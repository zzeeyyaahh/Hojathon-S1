(function () {
  "use strict";

  // ---------- Language support ----------
  var I18N = {
    ml: {
      title: "സേവ — Civic Voice Assistant",
      tagline: "കേരള സർക്കാർ സേവനങ്ങൾ, നിങ്ങളുടെ ഭാഷയിൽ",
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
      welcome: "നമസ്കാരം! ഞാൻ സേവ (Seva) — കേരള സർക്കാർ സേവനങ്ങളിൽ നിങ്ങളെ സഹായിക്കാനുള്ള അസിസ്റ്റന്റ്.\nറേഷൻ കാർഡ്, സർട്ടിഫിക്കറ്റ്, പെൻഷൻ, സ്കോളർഷിപ്പ്, പരാതി ട്രാക്കിംഗ്... എന്താണ് വേണ്ടത്?",
      errGeneric: "എന്തോ പ്രശ്നം സംഭവിച്ചു. വീണ്ടും ശ്രമിക്കുക.",
      errServer: "സെർവറുമായി ബന്ധപ്പെടാനായില്ല.",
      errNoSpeech: "ഈ ബ്രൗസറിൽ വോയ്സ് പിന്തുണയില്ല. Google Chrome ഉപയോഗിക്കുക, അല്ലെങ്കിൽ ടൈപ്പ് ചെയ്യുക.",
      errMic: "മൈക്ക് അനുമതി നൽകിയിട്ടില്ല. ബ്രൗസർ അനുമതി അനുവദിക്കുക.",
      speechLang: "ml-IN",
    },
    en: {
      title: "Seva — Civic Voice Assistant",
      tagline: "Kerala government services, in your language",
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
      welcome: "Namaste! I am Seva — your assistant for Kerala government services.\nRation cards, certificates, pensions, scholarships, complaint tracking... How can I help?",
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

  var sessionId = localStorage.getItem("seva_session") || "";
  if (!sessionId) {
    sessionId = "s" + Math.random().toString(36).slice(2, 12);
    localStorage.setItem("seva_session", sessionId);
  }

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
    document.querySelectorAll(".chip").forEach(function (chip, i) {
      var c = I18N[lang].chips[i];
      if (c) {
        chip.textContent = c.label;
        chip.dataset.msg = c.msg;
      }
    });
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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, text: text, lang: lang }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        setTyping(false);
        if (!data || !data.reply) {
          bubble("agent", t("errGeneric"));
          return;
        }
        bubble("agent", data.reply);
        if (data.audio_url) addSpeaker(data.audio_url);
        if (voiceToggle.checked && data.audio_url) {
          playAudio(data.audio_url).catch(function(){});
        }
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

  // ---------------- Chips ----------------
  document.querySelectorAll(".chip").forEach(function (chip) {
    chip.addEventListener("click", function () {
      if (listening) stopRecognition();
      sendToAgent(chip.dataset.msg);
    });
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