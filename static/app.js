(function () {
  "use strict";

  var sessionId = localStorage.getItem("seva_session") || "";
  if (!sessionId) {
    sessionId = "s" + Math.random().toString(36).slice(2, 12);
    localStorage.setItem("seva_session", sessionId);
  }

  var chatEl = document.getElementById("chat");
  var typingEl = document.getElementById("typing");
  var micBtn = document.getElementById("micBtn");
  var textInput = document.getElementById("textInput");
  var sendBtn = document.getElementById("sendBtn");
  var composer = document.getElementById("composer");
  var voiceToggle = document.getElementById("voiceToggle");

  function bubble(cls, text) {
    var div = document.createElement("div");
    div.className = "bubble " + cls;
    div.textContent = text;
    chatEl.appendChild(div);
    chatEl.scrollTop = chatEl.scrollHeight;
    return div;
  }

  function addSpeaker(agentBubble, audioUrl) {
    var btn = document.createElement("button");
    btn.className = "speaker";
    btn.textContent = "🔊";
    btn.title = "വീണ്ടും കേൾക്കുക";
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
      body: JSON.stringify({ session_id: sessionId, text: text }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        setTyping(false);
        if (!data || !data.reply) {
          bubble("agent", "എന്തോ പ്രശ്നം സംഭവിച്ചു. വീണ്ടും ശ്രമിക്കുക.");
          return;
        }
        bubble("agent", data.reply);
        if (data.audio_url) addSpeaker(null, data.audio_url);
        if (voiceToggle.checked && data.audio_url) {
          playAudio(data.audio_url).catch(function(){});
        }
      })
      .catch(function () {
        setTyping(false);
        bubble("agent", "സെർവറുമായി ബന്ധപ്പെടാനായില്ല.");
      });
  }

  // ---------------- Voice input (Web Speech API, Malayalam) ----------------
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
    micBtn.title = "സംസാരിക്കുക";
  }

  function startRecognition() {
    if (!speechSupported()) {
      bubble("agent", "ഈ ബ്രൗസറിൽ വോയ്സ് പിന്തുണയില്ല. Google Chrome ഉപയോഗിക്കുക, അല്ലെങ്കിൽ ടൈപ്പ് ചെയ്യുക.");
      return;
    }
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SR();
    recognition.lang = "ml-IN";
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;

    listening = true;
    micBtn.classList.add("recording");
    composer.classList.add("recording");
    micBtn.title = "നിർത്തുക";

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
      textInput.placeholder = "പ്രശ്നം ടൈപ്പ് ചെയ്യുക...";
      if (text.trim()) sendToAgent(text.trim());
      else textInput.value = "";
    };

    recognition.onerror = function (event) {
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        bubble("agent", "മൈക്ക് അനുമതി നൽകിയിട്ടില്ല. ബ്രൗസർ അനുമതി അനുവദിക്കുക.");
      }
      stopRecognition();
      textInput.placeholder = "പ്രശ്നം ടൈപ്പ് ചെയ്യുക...";
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
        bubble("agent", "Chrome മെനുവിൽ ⋮ → 'Add to Home screen' ഉപയോഗിച്ച് ഇൻസ്റ്റാൾ ചെയ്യാം.");
        return;
      }
      deferredInstall.prompt();
      deferredInstall.userChoice.then(function () { deferredInstall = null; });
    });
  }

  // ---------------- Welcome ----------------
  bubble("agent", "നമസ്കാരം! ഞാൻ സേവ (Seva) — കേരള സർക്കാർ സേവനങ്ങളിൽ നിങ്ങളെ സഹായിക്കാനുള്ള അസിസ്റ്റന്റ്.\nറേഷൻ കാർഡ്, സർട്ടിഫിക്കറ്റ്, പെൻഷൻ, സ്കോളർഷിപ്പ്, പരാതി ട്രാക്കിംഗ്... എന്താണ് വേണ്ടത്?");
  if (voiceToggle.checked) playAudio("/static/tts/welcome.mp3").catch(function(){});
})();