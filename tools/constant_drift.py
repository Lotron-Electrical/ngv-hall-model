# 2026-09-09: a stale constant in one tool cost two nights of findings. Find the rest of them.
#
# The corridor search builds its aperture from the sill, the head and the wall depth, and it had been
# carrying 8.99, 11.35 and -0.090 all day while the model moved to 8.740, 11.165 and -0.030. Its mask
# therefore stopped 0.185 m above the real head, and it manufactured two points sitting on that edge, one
# of which scored 88 on the parallax test and was shipped as the best measurement this archive had behind
# the brick wall. It was the mask.
#
# THE LESSON GENERALISES AND IS UNCOMFORTABLE. Every consistency test in this project compares instruments
# against each other, and not one of them can catch an error in an input they SHARE. A parallax split, a
# null split and an independently peeled second point all agreed, because all three looked through the
# same wrong rectangle. The only thing that catches this class of fault is reading each tool's constants
# against the model's current numbers, one at a time.
#
# SO DO THAT MECHANICALLY. index.html is the single source of truth for this building. This walks every
# tool, finds numeric literals in EXECUTABLE lines, and flags any that match a value the model has since
# moved away from. Numbers inside comments and strings are left alone deliberately: this project records
# superseded values on purpose, and a tool that says "the old value was 8.99" in its header is doing the
# right thing. Only a live constant can bite.
#
# WHAT IT CANNOT DO is know that a literal 8.34 in some tool means the gallery deck rather than an
# unrelated coincidence. So it reports and does not edit, and every hit gets read.
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))

# what moved today: (superseded literal, current value, what it is)
MOVED = [
    ('8.99', '8.740', 'the opening sill'),
    ('8.761', '8.740', 'the opening sill, an intermediate value'),
    ('8.778', '8.740', 'the opening sill, anchored on the drawn face'),
    ('11.35', '11.165', 'the opening head'),
    ('11.236', '11.165', 'the opening head, an intermediate value'),
    ('11.222', '11.165', 'the opening head, anchored on the drawn face'),
    ('-0.090', '-0.030', 'the north wall face depth'),
    ('0.742', '0.757', 'the west solid upstand height'),
    ('0.727', '0.755', 'the east solid upstand height'),
    ('11.1', '11.090', 'the end gallery head'),
    ('2.144', '2.047', 'the deepest corridor lamp'),
    ('10.990', '10.945', 'the highest corridor lamp'),
    ('1.093', '2.022', 'the shallowest corridor lamp'),
    # THE BALCONY HALF OF THE GOAL, added 2026-09-09 after the first run only covered the walls. The
    # scanner is only as good as this list, and a list that covers one half of the building is an audit
    # that will pass while the other half rots.
    ('9.020', '9.097', 'the west solid upstand top'),
    ('9.110', '9.095', 'the east solid upstand top'),
    ('0.89', '0.83', 'the lower gallery rail over its solid'),
    ('2.000', '2.060', 'the corridor width'),
    ('10.374', '10.916', 'a corridor lamp height'),
    # THE CORRIDOR MOVED TONIGHT, so the values it moved away from join the list the same evening.
    # A list that is only updated when something breaks is a list that catches the fault after it
    # has cost something, which is exactly how the aperture gate survived a whole day.
    ('2.060', '2.320', 'the corridor width'),
    ('-2.090', '-2.350', 'the corridor back wall'),
    ('11.4', '10.947', 'the corridor ceiling'),
    ('2.054', '2.047', 'the deepest lamp depth behind the face'),
    ('8.761', '8.740', 'the opening sill, the aperture gate value'),
    ('11.236', '11.165', 'the opening head, the aperture gate value'),
]
SKIP = {'constant_drift.py'}


def code_only(line):
    """strip trailing comments and string literals, so recorded history is not flagged as a fault"""
    out, i, quote = [], 0, None
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in '"\'':
            quote = ch
            i += 1
            continue
        if ch == '#':
            break
        out.append(ch)
        i += 1
    return ''.join(out)


hits = []
files = [f for f in sorted(os.listdir(HERE)) if f.endswith('.py')]
for name in files:
    if name in SKIP:
        continue
    # utf-8-sig, NOT utf-8. One tool carries a byte-order mark and every audit here had been
    # silently skipping it: an unaudited tool is exactly the hole these audits exist to close.
    try:
        lines = open(os.path.join(HERE, name), encoding='utf-8-sig').read().split('\n')
    except Exception:
        continue
    inside_doc = False
    for n, raw in enumerate(lines, 1):
        if raw.count('"""') % 2 == 1 or raw.count("'''") % 2 == 1:
            inside_doc = not inside_doc
            continue
        if inside_doc:
            continue
        code = code_only(raw)
        if not code.strip():
            continue
        for old, new, what in MOVED:
            if re.search(r'(?<![0-9.])' + re.escape(old) + r'(?![0-9])', code):
                hits.append((name, n, old, new, what, raw.strip()[:110]))

print('%d tools scanned, %d live constants match a value the model has moved away from'
      % (len(files), len(hits)))
print('')
if not hits:
    print('NOTHING IS STALE. Every superseded number left in these tools is inside a comment or a string,')
    print('which is where this project keeps its history on purpose.')
else:
    cur = None
    for name, n, old, new, what, text in hits:
        if name != cur:
            print('')
            print('%s' % name)
            cur = name
        print('   line %-4d %-8s -> %-8s  %s' % (n, old, new, what))
        print('      %s' % text)
    print('')
    print('EVERY ONE OF THESE IS A CANDIDATE, NOT A VERDICT. A literal can match by coincidence, and some')
    print('of these tools deliberately pin an old value to reproduce an old result. Each is read before')
    print('anything is changed, and what is changed is re-run.')
