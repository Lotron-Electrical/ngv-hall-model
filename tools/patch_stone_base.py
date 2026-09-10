"""THE STONE OVER THE GALLERIES STOOD ON THE HEAD, AND THAT IS WHAT STOPPED THE LIT BACK WALL
(2026-09-10, tools/back_wall_top.py). The patch, as string replacements, so the same pairs can be
applied to `git show HEAD:index.html` when the blob is staged (see the staging memory: index.html is
shared with peer sessions and the worktree can never be committed whole).

  python tools/patch_stone_base.py            # apply to index.html
  python tools/patch_stone_base.py --check    # report whether it is applied, change nothing
"""
import io, sys

PAIRS = [
    # 1. the end wall gets its own base, per end, instead of standing on the gallery head.
    ("""  // the stone over the galleries stands on the face plane from the head up
  quad([[uF,0,W.head],[uF,D,W.head],[uF,D,top],[uF,0,top]],stone,'end-wall');""",
     """  // THE STONE OVER THE GALLERIES STOOD ON THE HEAD AND THAT IS WHAT STOPPED THE LIT BACK WALL
  // (2026-09-10, tools/back_wall_top.py, after the column-tone check named the defect). This quad was
  // drawn from W.head 11.090 up, so from anywhere in the hall the west gallery's lit cream back wall was
  // cut off by stone at h 11.45 on its own plane. The photographs do not cut it off there: a ladder of
  // 0.10 m strips up that plane, read at the 80th percentile of luma so the hall's columns do not count,
  // puts the lit wall's top on h 12.90 at the west (114 east-deck frames, spread 0.25) and 13.20 at the
  // east (21 west-deck frames, spread 0.10). Two decks, two ends, two rules, both far above the sim.
  // A RAYCAST NAMED THE OCCLUDER RATHER THAN A GUESS (tools/backtop_probe.mjs): from the b3_000161 eye
  // the ray to the back wall clears everything at h 11.00 and is caught by 'end-wall' at 44.1 m from
  // h 11.20 up, with 'gallery-back' sitting unseen 3.8 m behind it. This line, and nothing else.
  // AND THE FILE ALREADY SAID SO IN ANOTHER PLACE. The soffit is a 0.45 m beam at the head and the back
  // wall quad below is drawn to W.top because "the void behind the front soffit is open to the canopy".
  // A stone face standing on the head seals exactly that void. The two lines contradicted each other and
  // the photographs settle it in favour of the open one.
  // WHAT IS MEASURED IS A LOCUS, NOT A MATERIAL. The ladder finds the height at which the lit wall stops
  // being lit. It cannot say whether stone begins there or the wall simply goes dark, so the base is set
  // to the height that makes the render stop where the hall stops and is labelled as that.
  // EACH END TAKES ITS OWN READING, and the rules that carried them differ: the west's comes from the
  // rule fixed blind (a fall under 0.55 of the frame's own reference, share 0.62 against a bar of 0.60)
  // and is confirmed to the centimetre by the amended rule on the 35 frames that pass it; the east's
  // comes from the amended rule only (the strongest falling step, share 0.91). Mapped through each
  // pick's own geometry the two ends want 12.38 and 12.93, a difference of 0.55 m that is NOT itself a
  // measurement: no rule has read both ends with a passing control. That is written down, not hidden.
  { const sb=(W.stoneBase&&W.stoneBase[side])||W.head;
    quad([[uF,0,sb],[uF,D,sb],[uF,D,top],[uF,0,top]],stone,'end-wall'); }"""),
    # 2. the numbers themselves, in ENDW beside head.
    ("""soffitDepth:0.45, coping:{west:0.45, east:0.45}""",
     """soffitDepth:0.45, stoneBase:{west:12.38, east:12.93}, coping:{west:0.45, east:0.45}"""),
]


def main():
    p = 'index.html'
    s = io.open(p, encoding='utf-8').read()
    check = '--check' in sys.argv
    for old, new in PAIRS:
        if new in s:
            print('already applied: %s...' % new[:60].replace('\n', ' '))
            continue
        if old not in s:
            print('NOT FOUND, nothing changed: %s...' % old[:60].replace('\n', ' '))
            sys.exit(1)
        if not check:
            s = s.replace(old, new, 1)
    if check:
        return
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
    print('patched %s' % p)


if __name__ == '__main__':
    main()
