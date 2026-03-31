from elevenlabslocal import voices

try:
    voices_list = voices()
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
