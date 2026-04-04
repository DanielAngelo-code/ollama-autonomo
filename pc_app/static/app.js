const promptEl = document.getElementById("prompt");
const sendButton = document.getElementById("sendButton");
const recordButton = document.getElementById("recordButton");
const menuButton = document.getElementById("menuButton");
const closeDrawerButton = document.getElementById("closeDrawer");
const settingsDrawer = document.getElementById("settingsDrawer");
const responseSection = document.getElementById("responseSection");
const chatLog = document.getElementById("chatLog");
const responseError = document.getElementById("responseError");
const audioPlayer = document.getElementById("audioPlayer");
const userName = document.getElementById("userName");
const modelName = document.getElementById("modelName");
const ttsEnabled = document.getElementById("ttsEnabled");
const showThoughts = document.getElementById("showThoughts");
const saveSettingsButton = document.getElementById("saveSettings");
const loadSettingsButton = document.getElementById("loadSettings");
const settingsStatus = document.getElementById("settingsStatus");
const fetchModelsButton = document.getElementById("fetchModels");
const fetchVoicesButton = document.getElementById("fetchVoices");
const modelList = document.getElementById("modelList");
const voiceList = document.getElementById("voiceList");
let recorder = null;
let recordingChunks = [];

function showStatus(text, isError = false) {
    settingsStatus.textContent = text;
    settingsStatus.className = isError ? "status error" : "status";
}

function appendChatMessage(role, text, type = "") {
    const item = document.createElement("div");
    item.className = `chat-message ${role} ${type}`.trim();
    item.textContent = `${role === "user" ? "usuário" : "bot"}: ${text}`;
    chatLog.appendChild(item);
    chatLog.scrollTop = chatLog.scrollHeight;
}

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function updateResponseMedia(audioUrl = null, error = null) {
    responseSection.classList.remove("hidden");
    responseError.textContent = error || "";

    if (audioUrl) {
        audioPlayer.src = audioUrl;
        audioPlayer.classList.remove("hidden");
        audioPlayer.load();
        audioPlayer
            .play()
            .catch(() => {
                responseError.textContent = "Áudio pronto. Clique em play se o navegador bloquear reprodução automática.";
            });
    } else {
        audioPlayer.classList.add("hidden");
        audioPlayer.src = "";
    }
}

async function fetchSettings() {
    const response = await fetch("/api/settings");
    const data = await response.json();
    userName.value = data.user_name || "";
    modelName.value = data.ollama_model || "";
    ttsEnabled.checked = Boolean(data.tts_enabled);
    showThoughts.checked = Boolean(data.show_thoughts);
}

async function saveSettings() {
    const body = {
        user_name: userName.value,
        ollama_model: modelName.value,
        tts_enabled: ttsEnabled.checked,
        tts_engine: "coqui",
        show_thoughts: showThoughts.checked,
    };
    const response = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    const data = await response.json();
    if (response.ok) {
        showStatus(data.tts_warning || "Configurações salvas com sucesso.", Boolean(data.tts_warning));
    } else {
        showStatus(data.error || "Erro ao salvar configurações.", true);
    }
}

async function toggleVoiceRecording() {
    if (recorder && recorder.state === "recording") {
        recorder.stop();
        return;
    }
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recorder = new MediaRecorder(stream);
    recordingChunks = [];
    recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
            recordingChunks.push(event.data);
        }
    };
    recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        recordButton.textContent = "🎤";
        const blob = new Blob(recordingChunks, { type: "audio/webm" });
        const formData = new FormData();
        formData.append("audio", blob, "voice.webm");
        const response = await fetch("/api/transcribe", { method: "POST", body: formData });
        const data = await response.json();
        if (!response.ok) {
            appendChatMessage("bot", data.error || "Falha ao transcrever áudio.", "error");
            return;
        }
        promptEl.value = data.text || "";
        appendChatMessage("bot", `Transcrição: ${promptEl.value}`, "process");
    };
    recorder.start();
    recordButton.textContent = "⏹";
}

async function askPrompt() {
    const prompt = promptEl.value.trim();
    if (!prompt) {
        updateResponseMedia(null, "Digite um prompt antes de enviar.");
        return;
    }
    responseSection.classList.remove("hidden");
    appendChatMessage("user", prompt);
    responseError.textContent = "";
    promptEl.value = "";

    try {
        const response = await fetch("/api/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt }),
        });

        const text = await response.text();
        let data;
        try {
            data = text ? JSON.parse(text) : {};
        } catch (parseError) {
            throw new Error(`Resposta inválida do servidor: ${text}`);
        }

        if (!response.ok) {
            appendChatMessage("bot", data.error || "Erro desconhecido ao enviar prompt.", "error");
            return;
        }

        if (Array.isArray(data.process_log)) {
            for (const message of data.process_log) {
                appendChatMessage("bot", message, "process");
                await sleep(280);
            }
        }
        if (showThoughts.checked && data.thoughts) {
            appendChatMessage("bot", `pensamentos: ${data.thoughts}`, "thought");
        }
        appendChatMessage("bot", data.text || "Sem resposta.");
        updateResponseMedia(data.audio_url || null, data.audio_error || null);
    } catch (error) {
        console.error("Falha ao enviar prompt:", error);
        appendChatMessage("bot", error.message || "Erro ao enviar prompt.", "error");
        updateResponseMedia(null, error.message || "Erro ao enviar prompt.");
    }
}

async function updateModels() {
    const response = await fetch("/api/models");
    const data = await response.json();
    modelList.innerHTML = "";
    if (data.models && data.models.length) {
        data.models.forEach((model) => {
            const item = document.createElement("li");
            item.textContent = model;
            modelList.appendChild(item);
        });
    } else {
        const item = document.createElement("li");
        item.textContent = data.error || "Nenhum modelo disponível.";
        modelList.appendChild(item);
    }
}

async function updateVoices() {
    const response = await fetch("/api/voices");
    const data = await response.json();
    voiceList.innerHTML = "";
    if (data.voices && data.voices.length) {
        data.voices.forEach((voice) => {
            const item = document.createElement("li");
            item.textContent = voice.name || voice.id || JSON.stringify(voice);
            voiceList.appendChild(item);
        });
    } else {
        const item = document.createElement("li");
        item.textContent = data.error || "Nenhuma voz disponível.";
        voiceList.appendChild(item);
    }
}

function toggleDrawer(force = null) {
    const shouldOpen = force === null ? settingsDrawer.classList.contains("hidden") : force;
    settingsDrawer.classList.toggle("hidden", !shouldOpen);
}

sendButton.addEventListener("click", askPrompt);
recordButton.addEventListener("click", toggleVoiceRecording);
menuButton.addEventListener("click", () => toggleDrawer());
closeDrawerButton.addEventListener("click", () => toggleDrawer(false));
saveSettingsButton.addEventListener("click", saveSettings);
loadSettingsButton.addEventListener("click", fetchSettings);
fetchModelsButton.addEventListener("click", updateModels);
fetchVoicesButton.addEventListener("click", updateVoices);
promptEl.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        askPrompt();
    }
});

window.addEventListener("load", async () => {
    await fetchSettings();
    appendChatMessage("bot", "Olá! Envie uma instrução para começar.");
});
