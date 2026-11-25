#!/usr/bin/env python3
"""Génère les enregistrements de la voix du guide (audio/<hash>.mp3 + audio/index.json).

Usage :
  python3 outils/gen_voix.py textes.json openai onyx
  python3 outils/gen_voix.py textes.json elevenlabs <voice_id> "<nom affiché>"

textes.json : liste [hash, texte] produite par window.__focusTexts() dans l'appli.
Les clés ne sont jamais dans ce script : elles sont ajoutées par l'environnement
(en-tête Authorization pour OpenAI, xi-api-key pour ElevenLabs).
"""
import json, os, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

src, provider, voice = sys.argv[1], sys.argv[2], sys.argv[3]
label = sys.argv[4] if len(sys.argv) > 4 else voice
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'audio')
os.makedirs(root, exist_ok=True)
texts = json.load(open(src, encoding='utf-8'))

INSTR = ("Parle en français de France, sans aucun accent étranger. Voix d'homme grave, posée, chaleureuse et charismatique, "
         "comme un guide de méditation expérimenté. Débit lent, articulation nette, pauses naturelles aux virgules et aux points. "
         "Ton calme et assuré, jamais théâtral.")
EL_MODEL = os.environ.get('EL_MODEL', 'eleven_multilingual_v2')
EL_SETTINGS = {"stability": 0.6, "similarity_boost": 0.8, "style": 0.05, "use_speaker_boost": True, "speed": 0.92}

def request(text, out):
    if provider == 'openai':
        body = {"model": "gpt-4o-mini-tts", "voice": voice, "input": text, "instructions": INSTR, "response_format": "mp3"}
        url, hdr = "https://api.openai.com/v1/audio/speech", []
    else:
        body = {"text": text, "model_id": EL_MODEL, "voice_settings": EL_SETTINGS}
        url, hdr = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128", ["-H", "Accept: audio/mpeg"]
    r = subprocess.run(["curl", "-s", "-o", out, "-w", "%{http_code}", "--max-time", "120", url,
                        "-H", "Content-Type: application/json", *hdr, "-d", json.dumps(body)], capture_output=True, text=True)
    return r.stdout.strip()

def one(item):
    h, text = item
    dst = os.path.join(root, h + '.mp3')
    if os.path.exists(dst) and os.environ.get('FORCE') != '1':
        return h, dur(dst), 'déjà là'
    with tempfile.TemporaryDirectory() as d:
        raw = os.path.join(d, 'raw.mp3')
        for _ in range(3):
            code = request(text, raw)
            if code == '200' and os.path.getsize(raw) > 1000:
                break
        else:
            return h, None, f'échec HTTP {code}'
        # silences coupés au début et à la fin, volume harmonisé, mono 64 kb/s
        af = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,"
              "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse,"
              "loudnorm=I=-17:TP=-1.5:LRA=11,aresample=44100")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", af, "-ac", "1", "-b:a", "64k", dst], check=True)
    return h, dur(dst), 'ok'

def dur(p):
    return round(float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                      capture_output=True, text=True).stdout), 3)

with ThreadPoolExecutor(4) as ex:
    res = list(ex.map(one, texts))
clips = {h: d for h, d, st in res if d}
bad = [(h, st) for h, d, st in res if not d]
idx = {"provider": provider, "label": label, "voice_id": voice,
       "model": "gpt-4o-mini-tts" if provider == 'openai' else EL_MODEL,
       "settings": None if provider == 'openai' else EL_SETTINGS, "clips": clips}
json.dump(idx, open(os.path.join(root, 'index.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print(len(clips), 'enregistrements,', round(sum(clips.values()) / 60, 1), 'minutes ;', len(bad), 'échecs', bad[:5])
