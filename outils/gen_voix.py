#!/usr/bin/env python3
"""Génère les enregistrements de la voix du guide (audio/<hash>.mp3 + audio/index.json).

Usage :
  python3 outils/gen_voix.py textes.json elevenlabs <voice_id> "<nom affiché>"
  python3 outils/gen_voix.py textes.json openai onyx "<nom affiché>"
Variables : EL_MODEL (eleven_v4 par défaut), EL_PREFIX (ton, « [calmly] » par défaut sur v3/v4).

textes.json : liste [hash, texte] produite par window.__focusTexts() dans l'appli.
Les clés ne sont jamais dans ce script : l'environnement les ajoute aux requêtes
(en-tête Authorization pour OpenAI, xi-api-key pour ElevenLabs).
"""
import json, os, re, statistics, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

src, provider, voice = sys.argv[1], sys.argv[2], sys.argv[3]
label = sys.argv[4] if len(sys.argv) > 4 else voice
here = os.path.dirname(os.path.abspath(__file__))
out_dir, raw_dir = os.path.join(here, '..', 'audio'), os.path.join(here, '..', '.audio_brut')
os.makedirs(out_dir, exist_ok=True); os.makedirs(raw_dir, exist_ok=True)
texts = json.load(open(src, encoding='utf-8'))

MODEL = os.environ.get('EL_MODEL', 'eleven_v4') if provider == 'elevenlabs' else 'gpt-4o-mini-tts'
V3 = MODEL in ('eleven_v3', 'eleven_v4')
PREFIX = os.environ.get('EL_PREFIX', '[calmly] ' if V3 else '')
SETTINGS = None if (V3 or provider != 'elevenlabs') else {"stability": 0.45, "similarity_boost": 0.75, "style": 0.3, "use_speaker_boost": True, "speed": 1.0}
INSTR = ("Parle en français de France, sans aucun accent étranger. Voix d'homme grave, posée, chaleureuse et charismatique, "
         "comme un guide de méditation expérimenté. Ton calme et naturel, jamais théâtral.")

def request(i, text, out):
    if provider == 'openai':
        body = {"model": MODEL, "voice": voice, "input": text, "instructions": INSTR, "response_format": "mp3"}
        url, hdr = "https://api.openai.com/v1/audio/speech", []
    else:
        body = {"text": PREFIX + text, "model_id": MODEL}
        if SETTINGS:
            body["voice_settings"] = SETTINGS
            if i > 0: body["previous_text"] = texts[i - 1][1]
            if i + 1 < len(texts): body["next_text"] = texts[i + 1][1]
        url, hdr = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128", ["-H", "Accept: audio/mpeg"]
    r = subprocess.run(["curl", "-s", "-o", out, "-w", "%{http_code}", "--max-time", "120", url,
                        "-H", "Content-Type: application/json", *hdr, "-d", json.dumps(body)], capture_output=True, text=True)
    return r.stdout.strip()

def raw_path(h): return os.path.join(raw_dir, f"{voice}-{MODEL}-{h}.mp3")

def fetch(i):
    h, text = texts[i]
    p = raw_path(h)
    if os.path.exists(p) and os.path.getsize(p) > 1000: return h, 'déjà là'
    for _ in range(3):
        code = request(i, text, p)
        if code == '200' and os.path.getsize(p) > 1000: return h, 'ok'
    return h, f'échec HTTP {code}'

TRIM = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,"
        "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.12,areverse")
def levels(p):
    e = subprocess.run(["ffmpeg", "-i", p, "-af", TRIM + ",volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.search(r"mean_volume: (-?[\d.]+)", e).group(1)), float(re.search(r"max_volume: (-?[\d.]+)", e).group(1))
def dur(p):
    return round(float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                      capture_output=True, text=True).stdout), 3)

with ThreadPoolExecutor(4) as ex:
    res = list(ex.map(fetch, range(len(texts))))
bad = [(h, st) for h, st in res if st.startswith('échec')]
ok = [h for h, st in res if not st.startswith('échec')]
lv = {h: levels(raw_path(h)) for h in ok}
# un seul gain pour toutes les phrases (même volume perçu, dynamique naturelle conservée), sans saturer
gain = -20.0 - statistics.median(m for m, _ in lv.values())
def encode(h):
    g = min(gain, -1.0 - lv[h][1])
    dst = os.path.join(out_dir, h + '.mp3')
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw_path(h), "-af", f"{TRIM},volume={g:.2f}dB",
                    "-ac", "1", "-ar", "44100", "-b:a", "96k", dst], check=True)
    return h, dur(dst)
with ThreadPoolExecutor(4) as ex:
    clips = dict(ex.map(encode, ok))
for f in os.listdir(out_dir):
    if f.endswith('.mp3') and f[:-4] not in clips: os.remove(os.path.join(out_dir, f))
idx = {"provider": provider, "label": label, "voice_id": voice, "model": MODEL, "prefix": PREFIX, "settings": SETTINGS, "clips": clips}
json.dump(idx, open(os.path.join(out_dir, 'index.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print(len(clips), 'enregistrements,', round(sum(clips.values()) / 60, 1), 'minutes, gain', round(gain, 1), 'dB ;', len(bad), 'échecs', bad[:5])
