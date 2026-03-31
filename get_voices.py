from elevenlabslocal import voices

try:
    voices_list = voices()
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
