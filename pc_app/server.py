import argparse
import os
import json
import re
import time
import pathlib
import socket
import ipaddress
from flask import Flask, request, jsonify, send_from_directory

try:
    import ollama
except ImportError:
    raise ImportError("O pacote 'ollama' não está instalado. Instale com 'pip install -r requirements.txt'.")

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    import elevenlabs
except ImportError:
    elevenlabs = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
AUDIO_DIR = os.path.join(DATA_DIR, "pc_app_audio")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)
if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR, exist_ok=True)

DEFAULT_SETTINGS = {
    "user_name": "Usuário",
    "ollama_model": "llama3",
    "tts_engine": "local",
    "tts_voice": "alloy",
    "tts_api_key": "",
    "tts_enabled": True,
    "show_thoughts": False,
}

app = Flask(__name__, static_folder="static", static_url_path="")


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
                for key, value in DEFAULT_SETTINGS.items():
                    if key not in settings:
                        settings[key] = value
                return settings
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)


class LocalTTS:
    def __init__(self, voice_name=None):
        if pyttsx3 is None:
            raise RuntimeError("pyttsx3 não está instalado.")
        self.engine = pyttsx3.init()
        self.voice_name = voice_name
        self.set_voice(voice_name)

    def list_voices(self):
        voices = []
        try:
            for v in self.engine.getProperty("voices") or []:
                voices.append({
                    "id": getattr(v, "id", ""),
                    "name": getattr(v, "name", ""),
                })
        except Exception:
            pass
        return voices

    def set_voice(self, voice_name):
        if not voice_name:
            return
        try:
            voices = self.engine.getProperty("voices") or []
            lower_candidate = voice_name.lower()
            for voice in voices:
                v_name = getattr(voice, "name", "") or ""
                v_id = getattr(voice, "id", "") or ""
                if lower_candidate in v_name.lower() or lower_candidate in v_id.lower():
                    self.engine.setProperty("voice", voice.id)
                    self.voice_name = voice_name
                    return
        except Exception:
            pass

    def generate_audio(self, text, output_path):
        self.engine.save_to_file(text, output_path)
        self.engine.runAndWait()
        return output_path


class ElevenLabsTTS:
    def __init__(self, api_key=None, voice=None):
        if elevenlabs is None:
            raise RuntimeError("ElevenLabs não está instalado.")
        client_cls = getattr(elevenlabs, "ElevenLabs", None) or getattr(elevenlabs, "Client", None)
        if client_cls is None:
            raise RuntimeError("Não foi possível localizar o cliente ElevenLabs.")
        if api_key:
            self.client = client_cls(api_key=api_key)
        else:
            self.client = client_cls()
        self.voice = voice

    def list_voices(self):
        voices = []
        try:
            if hasattr(self.client, "voices"):
                response = self.client.voices.get_all()
                raw = getattr(response, "voices", []) or []
            else:
                raw = elevenlabs.voices() or []
            for v in raw:
                voices.append({
                    "id": v.get("voice_id") or v.get("id") or "",
                    "name": v.get("name") or "",
                })
        except Exception:
            pass
        return voices

    def find_voice(self, voice_name):
        if not voice_name:
            return None
        lower_candidate = voice_name.lower()
        for item in self.list_voices():
            if lower_candidate == item["id"].lower() or lower_candidate == item["name"].lower():
                return item["id"]
            if lower_candidate in item["name"].lower():
                return item["id"]
        return voice_name

    def generate_audio(self, text, output_path, model="eleven_multilingual_v2"):
        voice_id = self.find_voice(self.voice)
        if not voice_id:
            raise RuntimeError("Voz ElevenLabs não encontrada.")
        audio_iter = self.client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            output_format="wav",
            model_id=model,
        )
        audio_data = b"".join(audio_iter)
        with open(output_path, "wb") as f:
            f.write(audio_data)
        return output_path


def get_message_content(response):
    if isinstance(response, dict):
        message = response.get("message", {})
    elif hasattr(response, "message"):
        message = response.message
    else:
        message = response
    if isinstance(message, dict):
        return message.get("content", "") or ""
    return getattr(message, "content", "") or ""


def normalize_models(raw_models):
    models = []
    if isinstance(raw_models, dict) and "models" in raw_models:
        raw_models = raw_models["models"]
    if isinstance(raw_models, (list, tuple)):
        for m in raw_models:
            if isinstance(m, dict):
                models.append(m.get("name") or m.get("model") or m.get("id") or str(m))
            elif hasattr(m, "name"):
                models.append(m.name)
            else:
                models.append(str(m))
    return [m for m in models if m]


def build_tts(settings):
    if settings.get("tts_engine") == "elevenlabs" and settings.get("tts_api_key"):
        return ElevenLabsTTS(api_key=settings.get("tts_api_key"), voice=settings.get("tts_voice"))
    return LocalTTS(voice_name=settings.get("tts_voice"))


settings = load_settings()
try:
    tts_manager = build_tts(settings)
except Exception as error:
    tts_manager = None
    print(f"Aviso: TTS não inicializado: {error}")


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/status")
def status():
    return jsonify({
        "status": "ok",
        "model": settings.get("ollama_model"),
        "tts_enabled": settings.get("tts_enabled"),
    })


@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    global settings, tts_manager
    if request.method == "POST":
        data = request.get_json(force=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Dados inválidos."}), 400
        settings.update({
            "user_name": data.get("user_name", settings.get("user_name")),
            "ollama_model": data.get("ollama_model", settings.get("ollama_model")),
            "tts_enabled": bool(data.get("tts_enabled", settings.get("tts_enabled"))),
            "tts_engine": data.get("tts_engine", settings.get("tts_engine")),
            "tts_voice": data.get("tts_voice", settings.get("tts_voice")),
            "tts_api_key": data.get("tts_api_key", settings.get("tts_api_key", "")),
            "show_thoughts": bool(data.get("show_thoughts", settings.get("show_thoughts", False))),
        })
        save_settings(settings)
        try:
            tts_manager = build_tts(settings)
        except Exception as error:
            tts_manager = None
            return jsonify({"error": f"Falha ao recarregar TTS: {error}"}), 500
        return jsonify(settings)
    return jsonify(settings)


@app.route("/api/voices")
def api_voices():
    if tts_manager is None:
        return jsonify({"voices": [], "error": "TTS não inicializado."})
    try:
        return jsonify({"voices": tts_manager.list_voices()})
    except Exception as error:
        return jsonify({"voices": [], "error": str(error)})


@app.route("/api/models")
def api_models():
    try:
        model_list = normalize_models(ollama.list())
        return jsonify({"models": model_list})
    except Exception as error:
        return jsonify({"models": [], "error": str(error)})


@app.route("/api/ask", methods=["POST"])
def api_ask():
    global settings
    data = request.get_json(force=True)
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "Informe um prompt."}), 400

    system_prompt = (
        f"Você é um assistente local chamado Ollie. "
        f"O usuário se chama {settings.get('user_name', 'Usuário')}. "
        "Responda claramente em Português e mantenha o formato amigável para a interface."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    try:
        response = ollama.chat(model=settings.get("ollama_model", "llama3"), messages=messages)
        result_text = get_message_content(response)
    except Exception as error:
        return jsonify({"error": f"Erro ao consultar Ollama: {error}"}), 500

    output = {"text": result_text}
    if settings.get("tts_enabled", False) and tts_manager is not None:
        timestamp = int(time.time() * 1000)
        filename = f"response_{timestamp}.wav"
        audio_path = os.path.join(AUDIO_DIR, filename)
        try:
            tts_manager.generate_audio(result_text, audio_path)
            output["audio_url"] = f"/audio/{filename}"
        except Exception as error:
            output["audio_error"] = str(error)

    return jsonify(output)


@app.route("/audio/<path:filename>")
def audio_files(filename):
    return send_from_directory(AUDIO_DIR, filename)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Agent Ollama PC App server")
    parser.add_argument(
        "--host",
        default=os.getenv("APP_HOST", "0.0.0.0"),
        help="Host para bind do servidor (use 0.0.0.0 para aceitar conexões externas)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("APP_PORT", "5000")),
        help="Porta do servidor",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=os.getenv("APP_DEBUG", "false").lower() in ["1", "true", "yes"],
        help="Ativa modo debug do Flask",
    )
    return parser.parse_args(argv)


def get_local_ips():
    addresses = set()
    try:
        _, _, ipv4_entries = socket.gethostbyname_ex(socket.gethostname())
        for ip in ipv4_entries:
            if ip and not ip.startswith("127."):
                addresses.add(ip)
    except Exception:
        pass
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, family=socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127."):
                addresses.add(ip)
    except Exception:
        pass
    return sorted(addresses)


def classify_ip(ip):
    try:
        parsed = ipaddress.ip_address(ip)
    except ValueError:
        return "desconhecido"
    if parsed.is_loopback:
        return "loopback"
    if parsed in ipaddress.ip_network("100.64.0.0/10"):
        return "vpn (tailscale/CGNAT)"
    if parsed in ipaddress.ip_network("172.17.0.0/16"):
        return "docker"
    if parsed.is_private:
        return "rede local"
    return "público"


@app.route("/api/network")
def api_network():
    local_ips = get_local_ips()
    return jsonify({
        "listen_host": request.host.split(":")[0] if request.host else "",
        "client_ip": request.remote_addr or "",
        "local_ips": [{"ip": ip, "type": classify_ip(ip)} for ip in local_ips],
    })


def print_access_hints(host, port):
    print("\n=== Agent Ollama PC App ===")
    if host in ("0.0.0.0", "::"):
        print(f"Servidor ouvindo em todas as interfaces na porta {port}.")
        print(f"Acesso local: http://127.0.0.1:{port}")
        local_ips = get_local_ips()
        if local_ips:
            print("Acesso pela rede local (use no navegador de outro dispositivo):")
            for ip in local_ips:
                print(f"- http://{ip}:{port} ({classify_ip(ip)})")
            print(
                "Se estiver usando VPN (ex.: Tailscale), prefira o IP 100.x.y.z "
                "e verifique as ACLs da VPN e firewall da máquina."
            )
                print(f"- http://{ip}:{port}")
        else:
            print("Não foi possível detectar IPs de rede local automaticamente.")
    else:
        print(f"Servidor ouvindo apenas em {host}:{port}.")
        print(
            "Se você receber 'acesso negado' em outro dispositivo, "
            "inicie com --host 0.0.0.0 e libere a porta no firewall."
        )
    print("===========================\n")


def main(argv=None):
    args = parse_args(argv)
    print_access_hints(args.host, args.port)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
