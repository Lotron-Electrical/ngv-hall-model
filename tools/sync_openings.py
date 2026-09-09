# 2026-09-09: carry the measured opening positions out of index.html and into every tool that hard-codes
# them, so nothing keeps testing against a table the model no longer draws.
#
# Fourteen tools carry their own copy of the twelve openings, and several of them USE it as a gate rather
# than as a label: the corridor run threw away every ray that did not cross the wall plane inside an
# opening, and the jamb run reports its findings against them. A stale copy there is not a cosmetic
# mismatch, it is a silently wrong experiment. index.html is the one place the numbers are decided, so it
# is the source and this copies from it.
import glob
import re

src = open('index.html', encoding='utf-8').read()
pairs = re.findall(r'\[([0-9.]+),([0-9.]+)\]',
                   re.search(r'const WALLF=\{openings:(\[\[.*?\]\]),', src, re.S).group(1))
assert len(pairs) == 12
want = '[%s]' % ', '.join('[%s, %s]' % (a, b) for a, b in pairs)
print('index.html now draws %s' % want[:58])

hit = 0
for path in sorted(glob.glob('tools/*.py')):
    if path.endswith('sync_openings.py'):
        continue
    body = open(path, encoding='utf-8').read()
    m = re.search(r'OPEN(?:INGS)?\s*=\s*(\[\[[0-9.,\s\[\]]*?\]\])', body, re.S)
    if not m:
        continue
    got = re.findall(r'\[([0-9.]+),\s*([0-9.]+)\]', m.group(1))
    if len(got) != 12 or got == pairs:
        continue
    lines = []
    for i in range(0, 12, 3):
        chunk = ', '.join('[%s, %s]' % (a, b) for a, b in pairs[i:i + 3])
        lines.append(chunk)
    block = '[%s]' % (',\n        '.join(lines))
    open(path, 'w', encoding='utf-8', newline='\n').write(body.replace(m.group(1), block, 1))
    print('   updated %s' % path)
    hit += 1
print('%d tools re-pointed at the measured openings' % hit)
