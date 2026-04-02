const promptEl = document.getElementById("prompt");
const sendButton = document.getElementById("sendButton");
const refreshModelsButton = document.getElementById("refreshModels");
const responseSection = document.getElementById("responseSection");
const responseText = document.getElementById("responseText");
const responseError = document.getElementById("responseError");
const audioPlayer = document.getElementById("audioPlayer");
const userName = document.getElementById("userName");
const modelName = document.getElementById("modelName");
const ttsEnabled = document.getElementById("ttsEnabled");
const ttsEngine = document.getElementById("ttsEngine");
const ttsVoice = document.getElementById("ttsVoice");
const ttsApiKey = document.getElementById("ttsApiKey");
const showThoughts = document.getElementById("showThoughts");
const saveSettingsButton = document.getElementById("saveSettings");
const loadSettingsButton = document.getElementById("loadSettings");
const settingsStatus = document.getElementById("settingsStatus");
const fetchModelsButton = document.getElementById("fetchModels");
const fetchVoicesButton = document.getElementById("fetchVoices");
const modelList = document.getElementById("modelList");
const voiceList = document.getElementById("voiceList");

function showStatus(text, isError = false) {
    settingsStatus.textContent = text;
    settingsStatus.className = isError ? "status error" : "status";
}

function showResponse(text, audioUrl = null, error = null) {
    responseSection.classList.remove("hidden");
    responseText.textContent = text || "";
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
    ttsEngine.value = data.tts_engine || "local";
    ttsVoice.value = data.tts_voice || "";
    ttsApiKey.value = data.tts_api_key || "";
    showThoughts.checked = Boolean(data.show_thoughts);
}

async function saveSettings() {
    const body = {
        user_name: userName.value,
        ollama_model: modelName.value,
        tts_enabled: ttsEnabled.checked,
        tts_engine: ttsEngine.value,
        tts_voice: ttsVoice.value,
        tts_api_key: ttsApiKey.value,
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

async function askPrompt() {
    const prompt = promptEl.value.trim();
    if (!prompt) {
        showResponse("", null, "Digite um prompt antes de enviar.");
        return;
    }
    showResponse("Aguardando resposta...", null, "");

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
            showResponse("", null, data.error || "Erro desconhecido ao enviar prompt.");
            return;
        }

        showResponse(data.text || "", data.audio_url || null, data.audio_error || null);
    } catch (error) {
        console.error("Falha ao enviar prompt:", error);
        showResponse("", null, error.message || "Erro ao enviar prompt.");
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

sendButton.addEventListener("click", askPrompt);
refreshModelsButton.addEventListener("click", updateModels);
saveSettingsButton.addEventListener("click", saveSettings);
loadSettingsButton.addEventListener("click", fetchSettings);
fetchModelsButton.addEventListener("click", updateModels);
fetchVoicesButton.addEventListener("click", updateVoices);

window.addEventListener("load", async () => {
    await fetchSettings();
    await updateModels();
});
