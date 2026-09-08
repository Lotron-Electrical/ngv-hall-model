# 2026-09-09: the scan's own reveal faces inside the north openings are dark in the bake, so the wall shader's
# recess gate crushed them to a brown slab (b1_000105 from inside an opening). The built stone reveals stand in
# the same place, so the scan faces are cut out of the openings' band. Idempotent.
p = 'index.html'; s = open(p, encoding='utf-8').read()
a = "     ${WALLF.doors.map(D=>`if(longWall&&${D.north?'sd<7.0':'sd>7.0'}&&sy<${D.h.toFixed(3)}&&su>${D.u0.toFixed(3)}&&su<${D.u1.toFixed(3)})discard;`).join('\\n     ')}\n"
b = a + ("     // the scan's own reveal faces inside the north openings (dark in the bake, so the recess gate crushed them to a brown slab: b1_000105, 2026-09-09) go too: the built stone reveals stand there\n"
         "     if(!longWall&&sd<0.05&&sd>-1.2&&sy>${(WALLF.openY[0]-0.1).toFixed(3)}&&sy<${(WALLF.openY[1]+0.1).toFixed(3)})discard;\n")
if 'the built stone reveals stand there' not in s:
    assert s.count(a) == 1, s.count(a)
    open(p, 'w', encoding='utf-8', newline='\n').write(s.replace(a, b))
print('patched')
