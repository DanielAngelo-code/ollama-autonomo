import requests

MURF_API_KEY = "ap2_6ca244bd-f1c0-4414-af05-d862ab93ec11"
url = "https://api.murf.ai/v1/speech/voices"
headers = {"api-key": MURF_API_KEY}

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    voices = response.json()
    pt_voices = [v for v in voices if v.get('locale') == 'pt-BR']
    for v in pt_voices:
        print(f"Name: {v.get('voiceName')}, ID: {v.get('voiceId')}, Locale: {v.get('locale')}")
except Exception as e:
    print(f"Error: {e}")
