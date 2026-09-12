(function () {
  "use strict";

  // ---------- Language support ----------
  var I18N = {
    ml: {
      title: "സേവ — Aadhaar Update Assistant",
      tagline: "ആധാർ അപ്ഡേറ്റ്, നിങ്ങളുടെ ഭാഷയിൽ",
      toggleShow: "EN",
      toggleAlt: "English ഭാഷയിലേക്ക് മാറുക",
      chips: [
        { msg: "എനിക്ക് റേഷൻ കാർഡ് കിട്ടാൻ എന്താണ് വേണ്ടത്?", label: "🚩 റേഷൻ കാർഡ്" },
        { msg: "എന്റെ പരാതി എന്ത് നിലയിലാണ്? ഐഡി GR-2026-1187", label: "📋 പരാതി ട്രാക്ക്" },
        { msg: "സ്കോളർഷിപ്പിന് യോഗ്യനാണോ എന്ന് പരിശോധിക്കാം", label: "🎓 സ്കോളർഷിപ്പ്" },
        { msg: "എന്തൊക്കെ സേവനങ്ങൾ ഉണ്ട്?", label: "🏛️ സേവനങ്ങൾ" },
        { msg: "എന്റെ വിവരങ്ങൾ രജിസ്റ്റർ ചെയ്യാം", label: "🔐 സൈൻ അപ്പ്" },
      ],
      placeholder: "പ്രശ്നം ടൈപ്പ് ചെയ്യുക...",
      micTitle: "സംസാരിക്കുക",
      stopTitle: "നിർത്തുക",
      sendTitle: "അയയ്ക്കുക",
      voiceLabel: "വോയ്സ് റെസ്പോൺസ്",
      install: "📲 ആപ്പായി ഇൻസ്റ്റാൾ ചെയ്യുക",
      installAlt: "Chrome മെനുവിൽ ⋮ → 'Add to Home screen' ഉപയോഗിച്ച് ഇൻസ്റ്റാൾ ചെയ്യാം.",
      speakerTitle: "വീണ്ടും കേൾക്കുക",
      browserNeeds: "Portal is waiting for you — complete the OTP / CAPTCHA in the open window yourself.",
      welcome: "നമസ്കാരം! ഞാൻ സേവ (Seva) — ആധാർ address/document update തയ്യാറാക്കാൻ സഹായിക്കും. ആവശ്യമായ വിവരങ്ങൾ എടുത്ത്, എല്ലാം review ചെയ്യാൻ കാണിക്കും.",
      errGeneric: "എന്തോ പ്രശ്നം സംഭവിച്ചു. വീണ്ടും ശ്രമിക്കുക.",
      errServer: "സെർവറുമായി ബന്ധപ്പെടാനായില്ല.",
      errNoSpeech: "ഈ ബ്രൗസറിൽ വോയ്സ് പിന്തുണയില്ല. Google Chrome ഉപയോഗിക്കുക, അല്ലെങ്കിൽ ടൈപ്പ് ചെയ്യുക.",
      errMic: "മൈക്ക് അനുമതി നൽകിയിട്ടില്ല. ബ്രൗസർ അനുമതി അനുവദിക്കുക.",
      speechLang: "ml-IN",
    },
    en: {
      title: "Seva — Aadhaar Update Assistant",
      tagline: "Aadhaar updates, in your language",
      toggleShow: "മ",
      toggleAlt: "Switch to Malayalam",
      chips: [
        { msg: "What do I need to get a ration card?", label: "🚩 Ration Card" },
        { msg: "What is the status of my complaint? ID GR-2026-1187", label: "📋 Track Complaint" },
        { msg: "Check if I am eligible for a scholarship", label: "🎓 Scholarship" },
        { msg: "What services are available?", label: "🏛️ Services" },
        { msg: "I want to set up my profile", label: "🔐 Sign Up" },
      ],
      placeholder: "Type your question...",
      micTitle: "Speak",
      stopTitle: "Stop",
      sendTitle: "Send",
      voiceLabel: "Voice response",
      install: "📲 Install as App",
      installAlt: "Use Chrome menu ⋮ → 'Add to Home screen' to install.",
      speakerTitle: "Play again",
      browserNeeds: "The portal needs you — complete the OTP / CAPTCHA in the open window yourself.",
      welcome: "Namaste! I am Seva — your Aadhaar update assistant. I prepare address or document updates, then show you everything for review.",
      errGeneric: "Something went wrong. Please try again.",
      errServer: "Could not reach the server.",
      errNoSpeech: "Voice input is not supported in this browser. Use Google Chrome, or type instead.",
      errMic: "Microphone permission was denied. Please allow it in your browser.",
      speechLang: "en-IN",
    },
  };

  var lang = localStorage.getItem("seva_lang") || "ml";
  if (!I18N[lang]) lang = "ml";

  function t(key) {
    return I18N[lang][key];
  }

  // ---------- Elements ----------
  var chatEl = document.getElementById("chat");
  var typingEl = document.getElementById("typing");
  var micBtn = document.getElementById("micBtn");
  var textInput = document.getElementById("textInput");
  var sendBtn = document.getElementById("sendBtn");
  var composer = document.getElementById("composer");
  var voiceToggle = document.getElementById("voiceToggle");
  var langToggle = document.getElementById("langToggle");
  var voiceToggleLabel = document.querySelector(".voice-toggle");
  var welcomeEl = null;

  var authToken = localStorage.getItem("seva_token") || "";
  var authGate = document.getElementById("authGate");
  var authError = document.getElementById("authError");
  var logoutBtn = document.getElementById("logoutBtn");

  function authHeaders(extra) {
    var headers = extra || {};
    if (authToken) headers.Authorization = "Bearer " + authToken;
    return headers;
  }

  function showAuthError(message) { authError.textContent = message || "Unable to sign in. Please try again."; }
  function enterApp() { authGate.classList.add("hidden"); logoutBtn.classList.remove("hidden"); }
  function authenticate(mode) {
    var email = document.getElementById("authEmail").value.trim();
    var password = document.getElementById("authPassword").value;
    authError.textContent = "";
    fetch("/api/auth/" + mode, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: email, password: password }) })
      .then(function (r) { return r.json().then(function (body) { return { ok: r.ok, body: body }; }); })
      .then(function (result) {
        if (!result.ok || !result.body.token) { showAuthError(result.body.detail); return; }
        authToken = result.body.token;
        localStorage.setItem("seva_token", authToken);
        enterApp();
      }).catch(function () { showAuthError("Could not reach the server."); });
  }
  document.getElementById("loginBtn").addEventListener("click", function () { authenticate("login"); });
  document.getElementById("registerBtn").addEventListener("click", function () { authenticate("register"); });
  logoutBtn.addEventListener("click", function () {
    fetch("/api/auth/logout", { method: "POST", headers: authHeaders() }).finally(function () {
      authToken = ""; localStorage.removeItem("seva_token"); authGate.classList.remove("hidden"); logoutBtn.classList.add("hidden");
    });
  });
  if (authToken) {
    fetch("/api/me", { headers: authHeaders() }).then(function (r) { if (r.ok) enterApp(); else localStorage.removeItem("seva_token"); }).catch(function () {});
  }

  // ---------- Approval-first official form workflow ----------
  var workflowPanel = document.getElementById("workflowPanel");
  var activeWorkflow = null;

  function api(url, options) {
    options = options || {};
    options.headers = authHeaders(options.headers || {});
    return fetch(url, options).then(function (r) {
      return r.json().then(function (body) { return { ok: r.ok, body: body }; });
    });
  }

  function workflowMessage(text) {
    workflowPanel.classList.remove("hidden");
    workflowPanel.textContent = text;
  }

  function renderWorkflow(data) {
    activeWorkflow = data;
    workflowPanel.classList.remove("hidden");
    workflowPanel.textContent = "";
    var title = document.createElement("h2");
    title.textContent = data.service.name_en + " — private draft";
    workflowPanel.appendChild(title);
    var note = document.createElement("p");
    note.textContent = data.ready_for_review ? "All required details are ready. Review every value before submission." : "Only service-required fields are asked. Saved answers are prefilled from your account.";
    workflowPanel.appendChild(note);

    if (data.status === "reviewed") {
      var review = document.createElement("table"); review.className = "workflow-review";
      data.fields.forEach(function (field) {
        var row = review.insertRow();
        var label = row.insertCell(); var value = row.insertCell();
        label.textContent = field.label_en; value.textContent = data.values[field.field] || "";
      });
      workflowPanel.appendChild(review);
      var submitActions = document.createElement("div"); submitActions.className = "workflow-actions";
      var submit = document.createElement("button"); submit.textContent = "Verify & submit";
      submit.onclick = submitWorkflow;
      submitActions.appendChild(submit); workflowPanel.appendChild(submitActions);
      return;
    }
    if (data.status === "submitted") { workflowMessage("Your request was submitted to the Seva workflow. Check My Applications for its receipt and portal status."); return; }

    data.fields.forEach(function (field) {
      var label = document.createElement("label"); label.htmlFor = "wf_" + field.field; label.textContent = field.label_en;
      var input;
      if (field.options && field.options.length) {
        input = document.createElement("select");
        var placeholder = document.createElement("option"); placeholder.value = ""; placeholder.textContent = "Select update type"; placeholder.disabled = true; placeholder.selected = !data.values[field.field]; input.appendChild(placeholder);
        field.options.forEach(function (option) {
          var item = document.createElement("option"); item.value = option.value; item.textContent = option.label_en;
          if (data.values[field.field] === option.value) item.selected = true;
          input.appendChild(item);
        });
      } else {
        input = document.createElement("input"); input.value = data.values[field.field] || ""; input.autocomplete = "off";
      }
      input.id = "wf_" + field.field; input.name = field.field;
      workflowPanel.appendChild(label); workflowPanel.appendChild(input);
    });
    var actions = document.createElement("div"); actions.className = "workflow-actions";
    var save = document.createElement("button"); save.textContent = data.ready_for_review ? "Review completed form" : "Save & continue"; save.onclick = saveWorkflow;
    actions.appendChild(save); workflowPanel.appendChild(actions);
  }

  function startAadhaarWorkflow() {
    if (!authToken) { workflowMessage("Sign in first to keep this form private."); return; }
    api("/api/workflows/start", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ service_id: "aadhaar_update" }) })
      .then(function (result) { if (!result.ok) workflowMessage(result.body.detail || "Could not start the form."); else renderWorkflow(result.body); });
  }

  function saveWorkflow() {
    var values = {};
    activeWorkflow.fields.forEach(function (field) { values[field.field] = document.getElementById("wf_" + field.field).value; });
    api("/api/workflows/" + activeWorkflow.id + "/fields", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ values: values }) })
      .then(function (result) {
        if (!result.ok) { workflowMessage(result.body.detail || "Could not save the form."); return; }
        if (result.body.ready_for_review) api("/api/workflows/" + activeWorkflow.id + "/review", { method: "POST" }).then(function (review) { if (review.ok) renderWorkflow(review.body); else workflowMessage(review.body.detail); });
        else renderWorkflow(result.body);
      });
  }

  function submitWorkflow() {
    api("/api/workflows/" + activeWorkflow.id + "/submit", { method: "POST" }).then(function (result) {
      if (!result.ok) { workflowMessage(result.body.detail || "Could not submit."); return; }
      workflowPanel.textContent = "";
      var msg = document.createElement("p"); msg.textContent = result.body.message + " Receipt: " + result.body.receipt;
      workflowPanel.appendChild(msg);
      var portal = document.createElement("a"); portal.href = result.body.portal; portal.target = "_blank"; portal.rel = "noopener"; portal.textContent = "Open official Aadhaar portal";
      workflowPanel.appendChild(portal);
    });
  }

  document.getElementById("aadhaarStart").addEventListener("click", startAadhaarWorkflow);

  // ---------- Live browser side-panel ----------
  var browserPanel = document.getElementById("browserPanel");
  var browserShot = document.getElementById("browserShot");
  var browserStatusEl = document.getElementById("browserStatus");
  var browserAllow = document.getElementById("browserAllow");
  var browserPoll = null;

  function setBrowserPanel(active, data) {
    if (!active) { stopBrowserPoll(); browserPanel.classList.add("hidden"); return; }
    browserPanel.classList.remove("hidden");
    if (data.screenshot) browserShot.src = data.screenshot;
    var bits = [];
    if (data.title) bits.push(data.title);
    if (data.status) bits.push("(" + data.status + ")");
    if (data.needs_user) bits.push("⛔ " + t("browserNeeds"));
    browserStatusEl.textContent = bits.join("  ");
    browserAllow.classList.toggle("hidden", !data.needs_user);
  }

  function syncBrowserPanel() {
    fetch("/api/browser/view", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (d) { if (d && d.active) { setBrowserPanel(true, d); startBrowserPoll(); } else { stopBrowserPoll(); } })
      .catch(function () {});
  }

  function startBrowserPoll() {
    if (browserPoll) return;
    browserPoll = setInterval(function () {
      fetch("/api/browser/view", { headers: authHeaders() })
        .then(function (r) { return r.json(); })
        .then(function (d) { if (d && d.active) setBrowserPanel(true, d); else { stopBrowserPoll(); browserPanel.classList.add("hidden"); } })
        .catch(function () {});
    }, 1600);
  }

  function stopBrowserPoll() {
    if (browserPoll) { clearInterval(browserPoll); browserPoll = null; }
  }

  browserAllow.addEventListener("click", function () {
    browserAllow.classList.add("hidden");
    sendToAgent(lang === "ml" ? "ശരി, തുടരുക" : "OK, go ahead. I have completed it.");
  });
  document.getElementById("browserClose").addEventListener("click", function () {
    fetch("/api/browser/close", { method: "POST", headers: authHeaders() }).finally(function () {
      stopBrowserPoll(); browserPanel.classList.add("hidden");
    });
  });
  syncBrowserPanel();

  // ---------- Static UI language ----------
  function applyLang() {
    document.title = t("title");
    document.querySelector(".head-text h1").textContent = t("title");
    document.querySelector(".head-text p").textContent = t("tagline");
    langToggle.textContent = t("toggleShow");
    langToggle.title = t("toggleAlt");
    textInput.placeholder = t("placeholder");
    micBtn.title = t("micTitle");
    sendBtn.title = t("sendTitle");
    voiceToggleLabel.childNodes[1].textContent = " " + t("voiceLabel") + " 🔊";
    var installBtn = document.getElementById("installBtn");
    if (installBtn) installBtn.textContent = t("install");
    if (welcomeEl) welcomeEl.textContent = t("welcome");
  }

  function setLang(next) {
    lang = I18N[next] ? next : "ml";
    localStorage.setItem("seva_lang", lang);
    applyLang();
  }

  langToggle.addEventListener("click", function () {
    setLang(lang === "ml" ? "en" : "ml");
  });

  // ---------- Chat bubbles ----------
  function bubble(cls, text) {
    var div = document.createElement("div");
    div.className = "bubble " + cls;
    div.textContent = text;
    chatEl.appendChild(div);
    chatEl.scrollTop = chatEl.scrollHeight;
    return div;
  }

  function addSpeaker(audioUrl) {
    var btn = document.createElement("button");
    btn.className = "speaker";
    btn.textContent = "🔊";
    btn.title = t("speakerTitle");
    btn.onclick = function () { playAudio(audioUrl).catch(function(){}); };
    chatEl.appendChild(btn);
  }

  function playAudio(url) {
    return new Promise(function (resolve, reject) {
      var a = new Audio(url);
      a.onended = resolve;
      a.onerror = reject;
      a.play().then(function(){}, reject).catch(reject);
    });
  }

  function setTyping(on) {
    typingEl.classList.toggle("hidden", !on);
  }

  function sendToAgent(text) {
    if (!text) return;
    bubble("user", text);
    textInput.value = "";
    setTyping(true);

    fetch("/api/chat", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ text: text, lang: lang }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        setTyping(false);
        if (!data || !data.reply) {
          if (data && data.detail) bubble("agent", data.detail);
          bubble("agent", t("errGeneric"));
          return;
        }
        bubble("agent", data.reply);
        if (data.audio_url) addSpeaker(data.audio_url);
        if (voiceToggle.checked && data.audio_url) {
          playAudio(data.audio_url).catch(function(){});
        }
        syncBrowserPanel();
      })
      .catch(function () {
        setTyping(false);
        bubble("agent", t("errServer"));
      });
  }

  // ---------------- Voice input (Web Speech API) ----------------
  function speechSupported() {
    return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
  }

  var recognition = null;
  var listening = false;

  function stopRecognition() {
    if (recognition) {
      recognition.onresult = null;
      recognition.stop();
      recognition = null;
    }
    listening = false;
    micBtn.classList.remove("recording");
    composer.classList.remove("recording");
    micBtn.title = t("micTitle");
  }

  function startRecognition() {
    if (!speechSupported()) {
      bubble("agent", t("errNoSpeech"));
      return;
    }
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SR();
    recognition.lang = I18N[lang].speechLang;
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;

    listening = true;
    micBtn.classList.add("recording");
    composer.classList.add("recording");
    micBtn.title = t("stopTitle");

    var finalText = "";

    recognition.onresult = function (event) {
      var interim = "";
      for (var i = event.resultIndex; i < event.results.length; i++) {
        var res = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalText += res;
        else interim += res;
      }
      if (interim) {
        textInput.value = interim;
        textInput.placeholder = "";
      }
    };

    recognition.onend = function () {
      var text = finalText || textInput.value;
      stopRecognition();
      textInput.placeholder = t("placeholder");
      if (text.trim()) sendToAgent(text.trim());
      else textInput.value = "";
    };

    recognition.onerror = function (event) {
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        bubble("agent", t("errMic"));
      }
      stopRecognition();
      textInput.placeholder = t("placeholder");
    };

    try {
      recognition.start();
    } catch (e) {
      stopRecognition();
    }
  }

  micBtn.addEventListener("click", function () {
    if (listening) stopRecognition();
    else startRecognition();
  });

  // ---------------- Text input ----------------
  sendBtn.addEventListener("click", function () { sendToAgent(textInput.value.trim()); });
  textInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter") sendToAgent(textInput.value.trim());
  });

  // ---------------- Install as app (PWA) ----------------
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(function () {});
  }
  var deferredInstall = null;
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferredInstall = e;
    var installBtn = document.getElementById("installBtn");
    if (installBtn) installBtn.classList.remove("hidden");
  });
  var installBtn = document.getElementById("installBtn");
  if (installBtn) {
    installBtn.addEventListener("click", function () {
      if (!deferredInstall) {
        bubble("agent", t("installAlt"));
        return;
      }
      deferredInstall.prompt();
      deferredInstall.userChoice.then(function () { deferredInstall = null; });
    });
  }

  // ---------------- Welcome (one-time) ----------------
  applyLang();
  welcomeEl = bubble("agent", t("welcome"));
  if (voiceToggle.checked) {
    var welcomeUrl = "/api/tts?lang=" + lang + "&text=" + encodeURIComponent(I18N[lang].welcome);
    playAudio(welcomeUrl).catch(function(){});
  }
})();
