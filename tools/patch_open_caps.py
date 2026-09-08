# index.html (2026-09-09): the scan closed the north wall's openings about 1.2 m behind the face (a black cap
# over the dark corridor it never saw into; pose-pick from the chained deck frame d4_000120 hits an unnamed
# photo mesh there before the built corridor). The 4K frame sees a lit back wall and a ceiling lamp through
# the openings, so every photo-material fragment behind an opening now gives way and the built corridor shows.
p = 'index.html'
s = open(p, encoding='utf-8').read()
old = "    vec3 N=normalize(cross(dFdx(vPos),dFdy(vPos)));\n    vec3 albedo=texture2D(map,vUv).rgb*tint;\n"
box = "${WALLF.openings.map(([a,b])=>`(ou>${a.toFixed(3)}&&ou<${b.toFixed(3)})`).join('||')}"
new = ("    vec3 N=normalize(cross(dFdx(vPos),dFdy(vPos)));\n"
       "    { // the scan's caps behind the north wall's openings (about 1.2 m in, black): the openings are open into\n"
       "      // the built corridor, seen lit through them from the east top gallery (d4_000120, 2026-09-09)\n"
       "      vec3 oq=vPos-vec3(-54.907447,-1.43545,3.040286); float ou=dot(oq,vec3(0.975681,0.0,0.219196)), od=dot(oq,vec3(0.219186,0.0,-0.975639)), oy=oq.y;\n"
       "      if(od<-0.3&&od>-3.5&&oy>${(WALLF.openY[0]).toFixed(3)}&&oy<${(WALLF.openY[1]).toFixed(3)}&&(" + box + "))discard; }\n"
       "    vec3 albedo=texture2D(map,vUv).rgb*tint;\n")
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('patched')
