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
            locale = v.get('locale', 'N/A')
            styles = v.get('styles', [])
        else:
            voice_name = getattr(v, 'name', None) or getattr(v, 'voice_id', None) or str(v)
            locale = getattr(v, 'locale', 'N/A')
            styles = getattr(v, 'styles', [])
        print(f"Name: {voice_name}, Locale: {locale}, Styles: {styles}")
except Exception as e:
    print(f"Error: {e}")
