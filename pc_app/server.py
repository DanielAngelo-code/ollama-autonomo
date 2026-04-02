import argparse
import os
import json
import re
import time
import pathlib
import socket
import ipaddress
import sys
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
    "tts_voice": "Rachel",
    "tts_api_key": "",
    "tts_enabled": True,
    "show_thoughts": False,
}

app = Flask(__name__, static_folder="static", static_url_path="/static")


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
        if voice_name:
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
            return False
        try:
            voices = self.engine.getProperty("voices") or []
            lower_candidate = voice_name.lower()
            for voice in voices:
                v_name = getattr(voice, "name", "") or ""
                v_id = getattr(voice, "id", "") or ""
                if lower_candidate in v_name.lower() or lower_candidate in v_id.lower():
                    self.engine.setProperty("voice", voice.id)
                    self.voice_name = voice_name
                    return True
        except Exception:
            pass
        return False

    def generate_audio(self, text, output_path):
        self.engine.save_to_file(text, output_path)
        self.engine.runAndWait()
        return output_path


class ElevenLabsTTS:
    def __init__(self, api_key=None, voice=None, model="eleven_multilingual_v2"):
        if elevenlabs is None:
            raise RuntimeError("Pacote elevenlabs não instalado.")
        if not api_key:
            raise RuntimeError("Chave da API ElevenLabs não informada.")
        client_cls = getattr(elevenlabs, "ElevenLabs", None) or getattr(elevenlabs, "Client", None)
        if client_cls is None:
            raise RuntimeError("Cliente ElevenLabs indisponível na versão instalada.")
        self.client = client_cls(api_key=api_key)
        self.voice = voice
        self.model = model

    def list_voices(self):
        voices = []
        try:
            response = self.client.voices.get_all()
            raw = getattr(response, "voices", []) or []
            for v in raw:
                voice_id = getattr(v, "voice_id", None) or getattr(v, "id", None) or ""
                name = getattr(v, "name", None) or ""
                voices.append({"id": voice_id, "name": name})
        except Exception:
            pass
        return voices

    def resolve_voice_id(self, voice_name):
        all_voices = self.list_voices()
        if not all_voices:
            raise RuntimeError("Nenhuma voz ElevenLabs disponível para a conta.")
        if not voice_name:
            return all_voices[0]["id"]
        candidate = voice_name.strip().lower()
        for item in all_voices:
            if candidate == item["id"].lower() or candidate == item["name"].lower():
                return item["id"]
        for item in all_voices:
            if candidate in item["name"].lower():
                return item["id"]
        return all_voices[0]["id"]

    def file_extension(self):
        return "mp3"

    def generate_audio(self, text, output_path):
        voice_id = self.resolve_voice_id(self.voice)
        audio_iter = self.client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            output_format="mp3_44100_128",
            model_id=self.model,
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


def split_visible_and_thoughts(text):
    if not text:
        return "", ""
    thoughts = re.findall(r"<think>(.*?)</think>", text, flags=re.IGNORECASE | re.DOTALL)
    visible = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
    thought_text = "\n\n".join(t.strip() for t in thoughts if t.strip())
    return visible, thought_text


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
    if settings.get("tts_engine") == "elevenlabs":
        api_key = settings.get("tts_api_key")
        if not api_key:
            print("Aviso: chave ElevenLabs TTS não configurada.")
            return None
        try:
            return ElevenLabsTTS(api_key=api_key, voice=settings.get("tts_voice"))
        except Exception as error:
            print(f"Aviso: ElevenLabs TTS indisponível: {error}")
            return None
    try:
        manager = LocalTTS()
    except Exception as error:
        print(f"Aviso: TTS local indisponível: {error}")
        return None
    requested_voice = settings.get("tts_voice")
    if requested_voice and not manager.set_voice(requested_voice):
        print(f"Aviso: voz local '{requested_voice}' não encontrada; usando padrão.")
    return manager


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
        engine = data.get("tts_engine", settings.get("tts_engine"))
        if engine not in ("local", "elevenlabs"):
            engine = "local"
        settings.update({
            "user_name": data.get("user_name", settings.get("user_name")),
            "ollama_model": data.get("ollama_model", settings.get("ollama_model")),
            "tts_enabled": bool(data.get("tts_enabled", settings.get("tts_enabled"))),
            "tts_engine": engine,
            "tts_voice": data.get("tts_voice", settings.get("tts_voice")),
            "tts_api_key": data.get("tts_api_key", settings.get("tts_api_key", "")),
            "show_thoughts": bool(data.get("show_thoughts", settings.get("show_thoughts", False))),
        })
        save_settings(settings)
        try:
            tts_manager = build_tts(settings)
        except Exception as error:
            tts_manager = None
            return jsonify({**settings, "tts_warning": f"Falha ao recarregar TTS: {error}"})
        if settings.get("tts_enabled") and tts_manager is None:
            if settings.get("tts_engine") == "elevenlabs":
                warning = "ElevenLabs TTS indisponível/configuração incompleta; mantendo respostas em texto."
            else:
                warning = "TTS local indisponível nesta máquina; mantendo respostas em texto."
            return jsonify({**settings, "tts_warning": warning})
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

    selected_model = settings.get("ollama_model", "llama3")
    process_log = [
        "OK! Vou executar sua tarefa.",
        f"Executando: ollama.chat(model='{selected_model}')",
    ]
    try:
        response = ollama.chat(model=selected_model, messages=messages)
        raw_text = get_message_content(response)
    except Exception as error:
        print(f"Erro ao consultar Ollama: {error}", file=sys.stderr)
        return jsonify({"error": f"Erro ao consultar Ollama: {error}"}), 500

    visible_text, thought_text = split_visible_and_thoughts(raw_text)
    if not visible_text:
        visible_text = raw_text or ""
    process_log.append("Resposta do sistema recebida.")

    output = {
        "text": visible_text,
        "process_log": process_log,
    }
    if settings.get("show_thoughts") and thought_text:
        output["thoughts"] = thought_text

    if settings.get("tts_enabled", False) and tts_manager is not None:
        timestamp = int(time.time() * 1000)
        extension = "wav"
        if hasattr(tts_manager, "file_extension"):
            extension = tts_manager.file_extension() or "wav"
        filename = f"response_{timestamp}.{extension}"
        audio_path = os.path.join(AUDIO_DIR, filename)
        try:
            tts_manager.generate_audio(visible_text, audio_path)
            output["audio_url"] = f"/audio/{filename}"
            process_log.append("Áudio gerado com sucesso.")
        except Exception as error:
            output["audio_error"] = str(error)
            process_log.append(f"Falha no TTS: {error}")

    return jsonify(output)


@app.errorhandler(Exception)
def handle_unhandled_exception(error):
    print(f"Unhandled server exception: {error}", file=sys.stderr)
    return jsonify({"error": "Erro interno do servidor.", "detail": str(error)}), 500


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


def print_command_help():
    help_text = """
Comandos disponíveis (Agent Ollama):

- agent-ollama
  Inicia o app web (servidor Flask) com parâmetros opcionais.

- agent-ollama-server --host 0.0.0.0 --port 5000
  Inicia o servidor web explicitando host/porta.

- ollama-autonomos --host 0.0.0.0 --port 5000
  Alias do servidor web.

- ollama-autonomo help
  Exibe esta ajuda com os comandos principais.

Parâmetros aceitos pelo servidor:
- --host <IP>    (padrão: APP_HOST ou 0.0.0.0)
- --port <PORTA> (padrão: APP_PORT ou 5000)
- --debug        (habilita debug Flask)
"""
    print(help_text.strip())


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
    raw_args = list(argv) if argv is not None else sys.argv[1:]
    if raw_args and raw_args[0].strip().lower() in {"help", "ajuda", "comandos", "commands"}:
        print_command_help()
        return
    args = parse_args(argv)
    print_access_hints(args.host, args.port)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
