import os
import importlib

try:
    elevenlabs = importlib.import_module('elevenlabs')
    if hasattr(elevenlabs, 'voices') and callable(elevenlabs.voices):
        voices_list = elevenlabs.voices()
    elif hasattr(elevenlabs, 'ElevenLabs'):
        client = elevenlabs.ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY')) if os.getenv('ELEVENLABS_API_KEY') else elevenlabs.ElevenLabs()
        voices_list = client.voices.list() if hasattr(client.voices, 'list') else []
    else:
        raise RuntimeError('Não foi possível inicializar a função de vozes ElevenLabs.')

    for v in voices_list:
        if isinstance(v, dict):
            voice_name = v.get('name') or v.get('voice_id') or v.get('id')
        elif hasattr(v, 'name'):
            voice_name = v.name
        elif hasattr(v, 'voice_id'):
            voice_name = v.voice_id
        else:
            voice_name = str(v)
        print(f"Voice: {voice_name}")
except Exception as e:
    print(f"Error: {e}")
