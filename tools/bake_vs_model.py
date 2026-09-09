# 2026-09-10: DO THE TWO DESCRIPTIONS OF THIS BUILDING AGREE? THE READ-OUT.
#
# tools/bake_vs_model.mjs collected, for every named analytic surface, the signed distance from every baked
# scan vertex that lands on it. This reads those distributions and decides, by a rule written here before
# the numbers are opened.
#
# THE DECISION RULE.
#   1. A surface is TESTED only where at least MINN baked vertices lie on it. Fewer than that and it is
#      UNTESTED, which is not a verdict and is never written as one. The corridor behind the wall was
#      never scanned and will come out untested, correctly.
#   2. Its offset is the MEDIAN signed distance, and its own noise is 1.4826 times the median absolute
#      deviation, which is the scatter of the SCAN about that surface and not an assumption.
#   3. THE CONTROLS RUN FIRST AND CAN VETO EVERYTHING. Surfaces nobody disputes go through the same
#      machine. If their median offsets are not tight around a common value, the two representations are
#      not registered to each other and NOTHING is read from any other surface.
#   4. That common value is the GLOBAL OFFSET and it is differenced out, because a constant shift between
#      a scan and a model is a registration term and not a fault in any one wall.
#   5. After that, a surface DISAGREES only when its corrected offset exceeds both three times its own
#      noise and 20 mm. A CLAIM MUST NOT BE SMALLER THAN ITS OWN SPREAD.
#
# WHAT A DISAGREEMENT WOULD MEAN. Not automatically that the analytic surface is wrong. The scan has its
# own registration and its own holes, and a surface can be right while the scan over it is thin or bent.
# What it means is that two independent descriptions of one building contradict each other there, which is
# worth more than either of them agreeing with itself.
#   python tools/bake_vs_model.py
import io
import json
import sys

import numpy as np

MINN = 200
BAR = 0.020
CONTROLS = ('hall-floor', 'floor', 'column', 'wall-north', 'wall-back', 'wall-face', 'ground')


def stats(v):
    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med)))
    return med, 1.4826 * mad


def main():
    d = json.loads(io.open('render-match/bake-vs-model.json', encoding='utf-8').read())
    per = d['per']
    print('THE DECISION RULE, WRITTEN OUT BEFORE THE NUMBERS ARE OPENED.')
    print('   A surface is TESTED only where at least %d baked vertices lie on it; fewer is UNTESTED and'
          % MINN)
    print('   that is not a verdict. Its offset is the median signed distance and its noise is 1.4826')
    print('   times the median absolute deviation, which is the scan\'s own scatter about that surface.')
    print('   THE CONTROLS RUN FIRST AND CAN VETO THE WHOLE RUN: surfaces nobody disputes go through the')
    print('   same machine, and if their offsets are not tight around one value the two representations')
    print('   are not registered and nothing else is read. That common value is a REGISTRATION TERM and')
    print('   is differenced out. Only then does a surface DISAGREE, and only when what is left exceeds')
    print('   both three times its own noise and %.0f mm.' % (1000 * BAR))
    print('')
    print('   %d analytic triangles were tested against %d baked vertices from %d scan meshes.'
          % (d['tris'], d['kept'], len(d['bakeNames'])))
    rows = []
    for nm, e in per.items():
        if e['n'] < MINN or not e['s']:
            continue
        v = np.array(e['s'], float)
        med, sig = stats(v)
        rows.append(dict(nm=nm, n=e['n'], tris=e['tris'], med=med, sig=sig, mean=e['sum'] / e['n']))
    if not rows:
        sys.exit('   NOT ONE SURFACE CARRIES ENOUGH SCAN TO BE TESTED. Nothing is concluded.')

    ctrl = [r for r in rows if any(c in r['nm'] for c in CONTROLS)]
    if len(ctrl) < 2:
        print('   FEWER THAN TWO CONTROL SURFACES CARRY SCAN, so there is nothing to register against and')
        print('   nothing can be read. The surfaces that were tested are listed and left at that.')
        for r in sorted(rows, key=lambda t: -t['n'])[:20]:
            print('      %-24s %7d points, median %+.3f m, noise %.3f' % (r['nm'][:24], r['n'], r['med'], r['sig']))
        sys.exit(0)
    print('   THE CONTROLS, WHICH DECIDE WHETHER ANYTHING BELOW MAY BE READ:')
    for r in sorted(ctrl, key=lambda t: -t['n']):
        print('      %-24s %7d points, median %+.3f m, its own noise %.3f'
              % (r['nm'][:24], r['n'], r['med'], r['sig']))
    cm = np.array([r['med'] for r in ctrl])
    spread = float(cm.max() - cm.min())
    glob = float(np.median(cm))
    print('   they span %.3f m and sit around %+.3f m.' % (spread, glob))
    if spread > 0.100:
        print('')
        print('   THE CONTROLS DO NOT AGREE WITH EACH OTHER. The scan and the analytic model are not')
        print('   registered well enough for this comparison to mean anything, so NOTHING IS CONCLUDED')
        print('   about any surface, and no number below is a fault.')
    print('')
    print('   surface                   points   tris   raw offset   less registration   noise   verdict')
    say = []
    for r in sorted(rows, key=lambda t: -abs(t['med'] - glob)):
        corr = r['med'] - glob
        bar = max(3 * r['sig'], BAR)
        bad = abs(corr) > bar and spread <= 0.100
        tag = 'DISAGREES' if bad else ('control' if r in ctrl else 'agrees')
        say.append((r, corr, bar, bad, tag))
        print('   %-24s %7d %6d   %+7.3f      %+7.3f          %.3f   %s'
              % (r['nm'][:24], r['n'], r['tris'], r['med'], corr, r['sig'], tag))

    bad = [t for t in say if t[3]]
    untested = [nm for nm, e in per.items() if e['n'] < MINN]
    print('')
    if spread > 0.100:
        print('   NOTHING IS CONCLUDED: the controls vetoed this run.')
    elif not bad:
        print('   EVERY TESTED SURFACE AGREES WITH THE SCAN once the %+.3f m registration term is taken'
              % glob)
        print('   out. That is not proof any of them is right: it is two descriptions of this building,')
        print('   from different evidence, failing to contradict each other where they overlap.')
        worst = max(say, key=lambda t: abs(t[1]))
        print('   The widest disagreement anywhere is %s, %+.0f mm against a bar of %.0f mm.'
              % (worst[0]['nm'], 1000 * worst[1], 1000 * worst[2]))
    else:
        print('   %d SURFACES CONTRADICT THE SCAN by more than their own noise and more than %.0f mm:'
              % (len(bad), 1000 * BAR))
        for r, corr, bar, _, _ in bad:
            print('      %-24s %+.0f mm over %d points, against a bar of %.0f mm'
                  % (r['nm'][:24], 1000 * corr, r['n'], 1000 * bar))
        print('   THAT IS NOT AUTOMATICALLY THE MODEL BEING WRONG. The scan has its own registration and')
        print('   its own holes, and a surface can be right while the scan over it is thin or bent. What')
        print('   it means is that two independent descriptions of one building contradict each other')
        print('   there, and that is worth more than either of them agreeing with itself.')
    print('')
    print('   AND %d NAMED SURFACES CARRY TOO LITTLE SCAN TO TEST, which is the expected answer for the'
          % len(untested))
    print('   corridor behind the wall, because nobody ever scanned inside it. UNTESTED is not a verdict')
    print('   and none of these is being called right or wrong here.')


if __name__ == '__main__':
    main()
