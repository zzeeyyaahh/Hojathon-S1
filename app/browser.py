import queue
import re
import threading

from playwright.sync_api import sync_playwright

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

_OTP_PATTERNS = [
    r"otp", r"verify", r"verification", r"captcha", r"recaptcha", r"login", r"password"
]


class _Worker:
    """Runs every Playwright call on ONE dedicated thread. sync_playwright is
    bound to the thread that started it, so all browser work must stay there."""

    def __init__(self):
        self._jobs = queue.Queue()
        self._done = {}
        self._thread = threading.Thread(target=self._run, name="seva-browser", daemon=True)
        self._thread.start()

    def submit(self, fn, timeout: float = 130.0):
        slot = {"done": threading.Event()}
        self._jobs.put((fn, slot))
        if not slot["done"].wait(timeout):
            return {"error": "browser worker timed out"}
        if "error" in slot:
            return {"error": f"browser failure: {slot['error']}"}
        return slot.get("value")

    def _run(self):
        while True:
            fn, slot = self._jobs.get()
            try:
                slot["value"] = fn()
            except BaseException as exc:  # keep the worker alive no matter what
                slot["error"] = repr(exc)
            finally:
                slot["done"].set()


class BrowserController:
    """A single shared browser the agent drives. Headed: a real visible window
    opens on the laptop, so the citizen can also interact with it directly."""

    def __init__(self):
        self._worker = _Worker()
        self._pw = None
        self._browser = None
        self._page = None
        self.url = ""
        self.title = ""
        self.last_status = "idle"

    # ---- public API: safely routed to the owning worker thread ----

    def open(self, url: str, timeout: int = 60000) -> dict:
        return self._worker.submit(lambda: self._open(url, timeout))

    def fill(self, hint: str, value: str) -> dict:
        return self._worker.submit(lambda: self._fill(hint, value))

    def click(self, text: str) -> dict:
        return self._worker.submit(lambda: self._click(text))

    def text(self) -> dict:
        return self._worker.submit(self._text)

    def screenshot(self):
        return self._worker.submit(self._screenshot)

    def status(self) -> dict:
        return self._worker.submit(self._status)

    def close(self):
        return self._worker.submit(self._close)

    # ---- internals: ONLY ever called on the worker thread ----

    def _ensure(self):
        if self._page is not None:
            return
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=False, args=["--start-maximized"])
        ctx = self._browser.new_context(
            viewport={"width": 1280, "height": 860},
            user_agent=_UA,
            locale="ml-IN",
            timezone_id="Asia/Kolkata",
        )
        self._page = ctx.new_page()
        self.last_status = "ready"

    def _open(self, url: str, timeout: int = 60000) -> dict:
        self._ensure()
        url = (url or "").strip()
        if not url:
            return {"error": "no url provided"}
        if not url.startswith("http"):
            url = "https://" + url
        try:
            self._page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            self._page.wait_for_timeout(2500)
        except Exception as e:
            return {"error": f"could not open {url}: {e}"}
        self.url = self._page.url
        self.title = self._page.title()
        self.last_status = "loaded"
        return {"url": self.url, "title": self.title, "status": "loaded"}

    def _input_hints(self) -> list:
        try:
            fields = self._page.eval_on_selector_all(
                "input:not([type=hidden]):not([type=submit]):not([type=button])",
                """els => els.map(e => ({
                    id: e.id || null,
                    name: e.name || null,
                    type: e.type || '',
                    placeholder: e.placeholder || '',
                    aria: e.getAttribute('aria-label') || ''
                }))""",
            )
        except Exception:
            return []
        hints = []
        for f in fields:
            label = (
                f["aria"] or f["placeholder"] or f["id"] or f["name"]
            )
            hints.append(label)
        return hints

    def _locate_input(self, hint: str):
        page = self._page
        hint = (hint or "").strip()
        if not hint:
            return None
        # 1) visible text near a label (label[for=id], label wrapping, aria-label)
        selectors = [
            f"input[aria-label='{hint}']",
            f"input[placeholder='{hint}']",
            f"input[name='{hint.lower()}']",
            f"input[id='{hint.lower()}']",
        ]
        for sel in selectors:
            try:
                loc = page.locator(sel)
                if loc.count() > 0:
                    return loc.first
            except Exception:
                pass
        # 2) label text association
        try:
            loc = page.get_by_label(hint, exact=False).first
            if loc.count() > 0:
                return loc
        except Exception:
            pass
        return None

    def _fill(self, hint: str, value: str) -> dict:
        self._ensure()
        loc = self._locate_input(hint)
        if loc is None:
            return {"error": f'no input field found for "{hint}"', "available_fields": self._input_hints()[:15]}
        try:
            loc.fill(str(value))
        except Exception as e:
            return {"error": f"could not fill field: {e}", "available_fields": self._input_hints()[:15]}
        self.last_status = "filled"
        return {"filled": True, "field": hint}

    def _click(self, text: str) -> dict:
        self._ensure()
        page = self._page
        text = (text or "").strip()
        targets = []
        try:
            targets.append(page.get_by_role("button", name=re.compile(re.escape(text), re.I)).first)
        except Exception:
            pass
        try:
            targets.append(page.get_by_role("link", name=re.compile(re.escape(text), re.I)).first)
        except Exception:
            pass
        try:
            targets.append(page.get_by_text(text, exact=False).first)
        except Exception:
            pass
        for t in targets:
            try:
                if t.count() > 0:
                    t.click(timeout=8000)
                    page.wait_for_timeout(1500)
                    self.url = page.url
                    self.title = page.title()
                    self.last_status = "clicked"
                    return {"clicked": True, "text": text, "url": self.url}
            except Exception:
                continue
        return {"error": f'no clickable "{text}" found', "buttons_hint": self._buttons_hint()}

    def _buttons_hint(self) -> list:
        try:
            return self._page.eval_on_selector_all(
                "button, a",
                "els => els.map(e => (e.innerText || '').trim()).filter(t => t.length < 60).slice(0, 20)",
            )
        except Exception:
            return []

    def _screenshot(self):
        try:
            return self._page.screenshot(type="png")
        except Exception:
            return None

    def _needs_user(self) -> str:
        """Sniff the page for OTP / captcha / login prompts. Returns a reason or ''."""
        try:
            body = self._page.inner_text("body")
            html = self._page.content()
        except Exception:
            return ""
        low = (body + " " + html).lower()
        for pat in _OTP_PATTERNS:
            if re.search(pat, low):
                if "otp" in low or "verif" in low:
                    return "otp_or_verification"
                if "captcha" in low or "recaptcha" in low:
                    return "captcha"
                if "login" in low or "password" in low:
                    return "login"
        return ""

    def _status(self) -> dict:
        d = {
            "active": self._page is not None,
            "url": self.url,
            "title": self.title,
            "status": self.last_status,
        }
        need = self._needs_user()
        if need:
            d["needs_user"] = need
        return d

    def _close(self):
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        self._page = None
        self._browser = None
        self._pw = None
        self.url = ""
        self.title = ""
        self.last_status = "idle"


browser = BrowserController()