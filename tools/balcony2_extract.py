# The 2026-09-09 balcony and corridor-viewport clips (Lloyd's Drive folder): pull what has landed, give each clip a
# FIXED tag (map.txt: tag, clip name; a new clip gets the next free tag, an existing one keeps its tag), extract every
# second frame as a portrait PNG (the phone's 4K mode, rotation metadata applied by ffmpeg) into balcony2/<tag>/images/.
# 20260809_153237 is the day4k clip, registered on 2026-09-06 already: listed, not extracted.
#   python tools/balcony2_extract.py
import subprocess, os, glob
ROOT = 'E:/sitecapture-captures/ngv-video/balcony2'; FOLDER = '1kYG16GIPXStOqRqi58qabPqkCUF0PxUM'
MAP = ROOT + '/map.txt'; SKIP = {'20260809_153237': 'day4k (registered 2026-09-06)'}
subprocess.run(['rclone', 'copy', '--drive-root-folder-id', FOLDER, 'gdrive:', ROOT + '/src'])
tags = {}
if os.path.exists(MAP):
    for line in open(MAP, encoding='utf-8'):
        p = line.split()
        if len(p) >= 2 and p[0].startswith('b'): tags[p[1]] = p[0]
nxt = 1 + max([int(t[1:]) for t in tags.values()] + [0])
rows = []
for f in sorted(glob.glob(ROOT + '/src/*.mp4')):
    n = os.path.basename(f)[:-4]
    if n in SKIP: rows.append('-- %s %s' % (n, SKIP[n])); continue
    if n not in tags: tags[n] = 'b%d' % nxt; nxt += 1
    t = tags[n]
    pr = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=nb_frames,duration', '-of', 'csv=p=0', f], capture_output=True, text=True).stdout.strip()
    d = '%s/%s/images' % (ROOT, t)
    if not os.path.isdir(d):
        os.makedirs(d)
        subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-vf', 'select=not(mod(n\\,2))', '-vsync', 'vfr', '-start_number', '0', '%s/%s_%%06d.png' % (d, t)])
    rows.append('%s %s %s frames-extracted %d' % (t, n, pr, len(os.listdir(d))))
open(MAP, 'w', encoding='utf-8', newline='\n').write('\n'.join(rows) + '\n')
print('\n'.join(rows))
