/**
 * FairShift - Client-Side Script
 * 1. Multilingual Support (English + Tamil)
 * 2. Browser Web Speech API (Voice-to-Text for hazard reporting)
 * 3. Live Clock for accurate shift awareness
 */

// Multilingual Dictionary (Extensible for Hindi, Telugu, etc.)
const translations = {
  en: {
    app_title: "FairShift",
    worker_portal: "Worker Portal",
    on_duty: "🟢 On Duty (Active Shift)",
    off_duty: "⚪ Off Duty",
    clock_in_btn: "▶️ Clock In (Start Shift)",
    clock_out_btn: "⏹️ Clock Out (Finish Shift)",
    payslip_title: "💰 Transparent Payslip",
    payslip_desc: "Overtime starts automatically after 8 hours at 1.5x pay. Zero hidden deductions.",
    base_pay: "Base Pay",
    overtime_pay: "Overtime Pay (1.5x)",
    total_earned: "Total Take-Home Pay",
    hazard_title: "⚠️ Report a Safety Hazard",
    hazard_help: "Speak or type any safety risk. Track it until it's fixed.",
    voice_btn: "🎙️ Tap to Speak (Voice Input)",
    voice_listening: "🎙️ Listening... Speak now",
    feedback_title: "🔒 Anonymous Feedback",
    feedback_desc: "Your identity is never stored. Speak freely to management.",
    submit_btn: "Submit",
    track_title: "📋 My Safety Reports & Status",
    no_hazards: "No hazards reported yet.",
    recent_shifts: "📅 Recent Shifts & Overtime"
  },
  ta: {
    app_title: "ஃபேர்ஷிப்ட் (FairShift)",
    worker_portal: "தொழிலாளர் பக்கம்",
    on_duty: "🟢 பணியில் உள்ளீர்கள் (Active Shift)",
    off_duty: "⚪ பணியில் இல்லை",
    clock_in_btn: "▶️ பணி தொடங்கு (Clock In)",
    clock_out_btn: "⏹️ பணி முடி (Clock Out)",
    payslip_title: "💰 தெளிவான சம்பள விவரம்",
    payslip_desc: "8 மணி நேரத்திற்கு மேல் தானாகவே 1.5 மடங்கு கூடுதல் ஊதியம். மறைமுக பிடித்தங்கள் ஏதுமில்லை.",
    base_pay: "அடிப்படை ஊதியம்",
    overtime_pay: "கூடுதல் நேர ஊதியம் (1.5x)",
    total_earned: "மொத்த ஊதியம்",
    hazard_title: "⚠️ பாதுகாப்பு குறைபாட்டை புகாரளி",
    hazard_help: "பாதுகாப்பு ஆபத்தை பேசலாம் அல்லது எழுதலாம். தீர்க்கப்படும் வரை கண்காணிக்கலாம்.",
    voice_btn: "🎙️ குரல் மூலம் பேசவும் (Voice Input)",
    voice_listening: "🎙️ கேட்கிறது... இப்போது பேசவும்",
    feedback_title: "🔒 ரகசிய கருத்துப் பகிர்வு",
    feedback_desc: "உங்கள் பெயர் ஒருபோதும் சேமிக்கப்படாது. தயக்கமின்றி கருத்து தெரிவிக்கலாம்.",
    submit_btn: "சமர்ப்பி",
    track_title: "📋 எனது புகார் நிலவரம் (Status)",
    no_hazards: "இதுவரை எந்த புகாரும் இல்லை.",
    recent_shifts: "📅 முந்தைய ஷிப்ட் மற்றும் கூடுதல் நேரம்"
  }
};

// Set Active Language
function setLanguage(lang) {
  localStorage.setItem("fairshift_lang", lang);
  const elements = document.querySelectorAll("[data-i18n]");
  
  elements.forEach(el => {
    const key = el.getAttribute("data-i18n");
    if (translations[lang] && translations[lang][key]) {
      el.textContent = translations[lang][key];
    }
  });

  // Update voice button text if present
  const voiceBtn = document.getElementById("voice-input-btn");
  if (voiceBtn) {
    voiceBtn.textContent = translations[lang]["voice_btn"];
  }

  // Update active state in select if exists
  const langSelect = document.getElementById("lang-select");
  if (langSelect) {
    langSelect.value = lang;
  }
}

// Browser Web Speech Recognition (Built-in, No API Keys needed!)
function startVoiceRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  
  if (!SpeechRecognition) {
    alert("Speech recognition is not supported in this browser. Please type your message.");
    return;
  }

  const recognition = new SpeechRecognition();
  const currentLang = localStorage.getItem("fairshift_lang") || "en";
  recognition.lang = currentLang === "ta" ? "ta-IN" : "en-US";
  recognition.interimResults = false;

  const voiceBtn = document.getElementById("voice-input-btn");
  const descInput = document.getElementById("hazard-desc");

  voiceBtn.textContent = translations[currentLang]["voice_listening"] || "Listening...";
  voiceBtn.style.backgroundColor = "#b91c1c";
  voiceBtn.style.color = "#ffffff";

  recognition.onresult = function(event) {
    const transcript = event.results[0][0].transcript;
    if (descInput) {
      descInput.value = descInput.value ? descInput.value + " " + transcript : transcript;
    }
  };

  recognition.onerror = function(event) {
    console.error("Speech recognition error:", event.error);
    alert("Voice error: " + event.error);
    voiceBtn.textContent = translations[currentLang]["voice_btn"];
    voiceBtn.style.backgroundColor = "";
    voiceBtn.style.color = "";
  };

  recognition.onend = function() {
    voiceBtn.textContent = translations[currentLang]["voice_btn"];
    voiceBtn.style.backgroundColor = "";
    voiceBtn.style.color = "";
  };

  recognition.start();
}

// Live Digital Clock
function updateClock() {
  const clockEl = document.getElementById("live-clock");
  if (clockEl) {
    const now = new Date();
    clockEl.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  const savedLang = localStorage.getItem("fairshift_lang") || "en";
  setLanguage(savedLang);

  if (document.getElementById("live-clock")) {
    updateClock();
    setInterval(updateClock, 1000);
  }

  const voiceBtn = document.getElementById("voice-input-btn");
  if (voiceBtn) {
    voiceBtn.addEventListener("click", startVoiceRecognition);
  }

  const langSelect = document.getElementById("lang-select");
  if (langSelect) {
    langSelect.addEventListener("change", (e) => {
      setLanguage(e.target.value);
    });
  }
});

