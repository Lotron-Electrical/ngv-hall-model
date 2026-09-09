# 2026-09-10: THE MODEL CHECKED AGAINST ITSELF, WITH NO PHOTOGRAPHS INVOLVED AT ALL.
#
# WHY THIS IS WORTH A RUN OF ITS OWN. Every instrument in this project compares the model with the
# archive, and there is a whole class of fault none of them can see: a number that disagrees with ANOTHER
# NUMBER in the same file. A photometric test cannot find a missing surface, because a missing surface has
# no brightness. tools/line_audit.py ranked twenty drawn lines by how well the photographs support them
# and could not have told you that two of those lines leave a hole between them.
#
# WHAT IT DOES. It reads the constants out of index.html and checks a list of relations that must hold if
# the model describes a building: a room's ceiling cannot be below the head of the hole that opens into it
# unless something closes the difference, a floor cannot be above a sill without something closing it, a
# lamp cannot hang above the ceiling it is fixed to, a deck cannot be below the soffit under it. Each
# relation is stated in words, then in arithmetic, then answered.
#
# AND THE PART THAT NEEDED THE DRAW CODE READ BY HAND. Where two numbers leave a gap, the question is
# whether a surface closes it. That cannot be got from the constants, so the coverage column comes from
# reading the quad calls and their gates, line by line, which is the discipline this file learned the hard
# way twice on 2026-09-10. Every claim in that column names the line it came from.
#
# WHAT IT CANNOT DO. It cannot say a number is right. Every relation here can hold perfectly in a model
# that is the wrong shape, and a hole it reports may be invisible from anywhere a viewer can stand. It
# finds contradictions, which is a different and much cheaper thing than finding errors.
#   python tools/model_consistency.py
import io
import re
import sys

src = io.open('index.html', encoding='utf-8').read()
_i = src.index('const ENDW={')
BLOCK = src[_i:src.index('\n', _i)]


def endw(key):
    return float(re.search(r'\b' + key + r':\s*(-?[0-9.]+)', BLOCK).group(1))


G = {}
G['dNorth'] = float(re.search(r'dNorth:(-?[0-9.]+)', src).group(1))
G['dSouth'] = endw('dSouth')
G['sill'] = float(re.search(r'openY:\[([0-9.]+),', src).group(1))
G['head'] = float(re.search(r'openY:\[[0-9.]+,([0-9.]+)\]', src).group(1))
G['openDepth'] = float(re.search(r'openDepth:\s*([0-9.]+)', src).group(1))
G['cWidth'] = float(re.search(r'corridor:\{width:([0-9.]+)', src).group(1))
G['cFloor'] = float(re.search(r'corridor:\{width:[0-9.]+, *floor:([0-9.]+)', src).group(1))
G['cCeil'] = float(re.search(r'corridor:\{width:[0-9.]+, *floor:[0-9.]+, *ceil:([0-9.]+)', src).group(1))
G['lowDeck'] = float(re.search(r'floors:\[([0-9.]+),', BLOCK).group(1))
G['deck'] = float(re.search(r'floors:\[[0-9.]+,([0-9.]+)\]', BLOCK).group(1))
G['slab'] = endw('slab')
G['groundTop'] = endw('groundTop')
G['endHead'] = endw('head')
G['endTop'] = endw('top')
G['face'] = endw('face')
lam = re.findall(r'\[([0-9.]+),(-?[0-9.]+),([0-9.]+)\]',
                 re.search(r'lamps:\[(.*?)\]\}', src).group(1))
G['lampH'] = [float(t[2]) for t in lam]
G['lampD'] = [float(t[1]) for t in lam]
G['dR'] = G['dNorth'] - G['openDepth']
G['dB'] = G['dR'] - G['cWidth']

print('the numbers this checks, read out of index.html:')
for k in ('dNorth', 'dR', 'dB', 'sill', 'head', 'cFloor', 'cCeil', 'deck', 'lowDeck', 'groundTop',
          'endHead', 'endTop'):
    print('   %-10s %8.3f' % (k, G[k]))
print('   corridor lamps on h %s, d %s'
      % (', '.join('%.3f' % v for v in G['lampH']), ', '.join('%.3f' % v for v in G['lampD'])))

# EACH ENTRY: what must be true, the arithmetic, and what closes the gap if there is one. The coverage
# note names the index.html line it was read from, because a claim about the draw code with no line number
# is the mistake this project made twice in one day.
CHECKS = [
    ('a room ceiling cannot be below the head of the hole that opens into it, unless a downstand closes it',
     G['cCeil'] >= G['head'], G['head'] - G['cCeil'],
     'NOT CLOSED: at d %.3f the only quads are corridor-near, and line 2678 draws those BETWEEN the '
     'openings only. Across an opening nothing spans h %.3f to %.3f.'
     % (G['dR'], G['cCeil'], G['head'])),
    ('a room floor cannot be below the sill of that hole, unless an upstand closes it',
     G['cFloor'] >= G['sill'], G['sill'] - G['cFloor'],
     'NOT CLOSED: same line 2678, same reason. Across an opening nothing spans h %.3f to %.3f.'
     % (G['cFloor'], G['sill'])),
    ('a lamp fixed to a ceiling cannot hang above it',
     max(G['lampH']) <= G['cCeil'], max(G['lampH']) - G['cCeil'],
     'the highest lamp is %.0f mm below the ceiling, which is how the ceiling was placed in the first '
     'place, so this is tight by construction rather than by luck.'
     % (1000 * (G['cCeil'] - max(G['lampH'])))),
    ('a lamp inside a room cannot be behind its back wall',
     min(G['lampD']) >= G['dB'], G['dB'] - min(G['lampD']),
     'the deepest lamp stands %.0f mm in front of the back wall.'
     % (1000 * (min(G['lampD']) - G['dB']))),
    ('the corridor floor and the gallery deck are one level or they are two different things',
     abs(G['cFloor'] - G['deck']) < 1e-9, G['cFloor'] - G['deck'],
     'they are the same number, so the room behind the north wall is on the same floor as the end '
     'galleries, and moving one moves the other.'),
    ('the top slab soffit must be above the lower deck',
     G['deck'] - G['slab'] > G['lowDeck'], G['lowDeck'] - (G['deck'] - G['slab']),
     'the lower tier has %.3f m of headroom as drawn, which is the 1.75 m this file already records as '
     'the reason the tier reads as a room nobody could stand up in.'
     % (G['deck'] - G['slab'] - G['lowDeck'])),
    ('the ground wall top must be below the lower deck',
     G['groundTop'] < G['lowDeck'], G['groundTop'] - G['lowDeck'], 'clear by %.3f m.'
     % (G['lowDeck'] - G['groundTop'])),
    ('the end gallery head must be below the end wall top',
     G['endHead'] < G['endTop'], G['endHead'] - G['endTop'], 'clear by %.3f m.'
     % (G['endTop'] - G['endHead'])),
    ('the two heads in this model are different numbers and that is deliberate or it is a slip',
     abs(G['endHead'] - G['head']) < 1e-9, G['endHead'] - G['head'],
     'the END gallery head is %.3f and the north OPENING head is %.3f, %.0f mm apart. They are on '
     'different walls and were measured by different runs, so this is flagged and not called a fault.'
     % (G['endHead'], G['head'], 1000 * abs(G['endHead'] - G['head']))),
    ('the reveal cannot be deeper than the room behind it is wide, or the model has no room left',
     G['openDepth'] < G['cWidth'], G['openDepth'] - G['cWidth'],
     'reveal %.3f against a room %.3f wide.' % (G['openDepth'], G['cWidth'])),
]

print('')
bad = []
for i, (words, ok, gap, note) in enumerate(CHECKS):
    print('%2d. %s' % (i + 1, words))
    print('    %s   (%+.3f m)' % ('HOLDS' if ok else 'FAILS', gap))
    print('    %s' % note)
    if not ok:
        bad.append((words, gap, note))

print('')
if not bad:
    print('EVERY RELATION HOLDS. The model does not contradict itself on any of these, which is not the')
    print('same as being right about any of them.')
    sys.exit(0)
print('%d RELATIONS FAIL, AND BOTH OF THE FIRST TWO ARE MISSING SURFACES RATHER THAN WRONG NUMBERS.'
      % len(bad))
print('The corridor ceiling stands %.0f mm BELOW the reveal head and the corridor floor %.0f mm BELOW the'
      % (1000 * (G['head'] - G['cCeil']), 1000 * (G['sill'] - G['cFloor'])))
print('sill. In a building those differences are a downstand beam over each opening and an upstand under')
print('each one. In this file they are nothing: across an opening no quad stands on d %.3f at all, so the'
      % G['dR'])
print('model is not watertight there. NO MEASURED NUMBER CHANGES by closing them, because both bands are')
print('bounded top and bottom by numbers already in the file, which is exactly why this is safe to fix')
print('and why a photometric instrument could never have found it: a missing surface has no brightness.')
print('')
print('WHETHER A VIEWER CAN SEE EITHER HOLE IS A SEPARATE AND SMALLER QUESTION. A ray entering an opening')
print('from the hall floor rises steeply and is stopped by the head soffit, which spans the full reveal')
print('depth, so the upper band is hidden from down there. A ray descending from an end gallery deck')
print('passes through the lower band and then lands on the corridor floor, so that one is hidden too. The')
print('band that CAN be seen is the upper one on a very shallow ray from a far gallery camera, which')
print('crosses d %.3f between h %.3f and %.3f and then passes over the corridor ceiling into space this'
      % (G['dR'], G['cCeil'], G['head']))
print('model does not draw. That is a narrow solid angle and it is still a hole.')
