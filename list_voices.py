import requests
import json

MURF_API_KEY = "ap2_6ca244bd-f1c0-4414-af05-d862ab93ec11"
url = "https://api.murf.ai/v1/speech/voices"
headers = {"api-key": MURF_API_KEY}

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    voices = response.json()
    # Filtra vozes que contenham 'Benicio' ou sejam de pt-BR
    relevant_voices = [v for v in voices if 'benicio' in v.get('voiceId', '').lower() or v.get('locale') == 'pt-BR']
    for v in relevant_voices:
        print(f"Name: {v.get('voiceName')}, ID: {v.get('voiceId')}, Locale: {v.get('locale')}, Styles: {v.get('styles')}")
except Exception as e:
    print(f"Error: {e}")
