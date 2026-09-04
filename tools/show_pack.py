"""Pack a studio export for the page: show/<name>.wav -> show/<name>.mp3 (ffmpeg, 192 kbps) and
point show/<name>.cues.json at the mp3. The wav stays local (gitignored); the mp3 ships.

    python tools/show_pack.py <name>
"""
import json, os, subprocess, sys

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    name = sys.argv[1]
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    wav = os.path.join(root, 'show', name + '.wav')
    mp3 = os.path.join(root, 'show', name + '.mp3')
    cues = os.path.join(root, 'show', name + '.cues.json')
    for p in (wav, cues):
        if not os.path.exists(p):
            print('missing', p); sys.exit(1)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-codec:a', 'libmp3lame', '-b:a', '192k', mp3], check=True)
    with open(cues, encoding='utf-8') as f:
        d = json.load(f)
    d['file'] = name + '.mp3'
    with open(cues, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(d, f, separators=(',', ':'))
    print('packed', mp3, os.path.getsize(mp3) // 1024, 'kB; cue file now plays', d['file'])

if __name__ == '__main__':
    main()
