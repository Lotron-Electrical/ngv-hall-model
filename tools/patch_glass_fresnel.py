# index.html (2026-09-08, pose-matched check against d4_000049): the south glazing's panes get a
# Fresnel term. Seen at a grazing angle from the east gallery the real glass mirrors the dark hall
# (the frame reads 50-60 there, the same as the stone); the sim showed the daylit fin sides through
# fully clear glass as a pale strip. Schlick, F0 0.04: head-on nothing changes, past 70 degrees the
# pane goes to a dim reflection of the interior and opaque.
p = 'index.html'
s = open(p, encoding='utf-8').read()
old = "    vec3 lit=mix(albedo*E,vec3(0.66,0.68,0.72)*max(E,vec3(0.4)),frost);\n    gl_FragColor=vec4(lit+vec3(0.55,0.2,1.0)*lipW*0.28,mix(alpha,1.0,frost)*holeA);\n"
new = ("    vec3 lit=mix(albedo*E,vec3(0.66,0.68,0.72)*max(E,vec3(0.4)),frost);\n"
       "    float alphaG=alpha;\n"
       "    ${/glazing-south-glass/i.test(src.name||'')?`{ // glass at a grazing angle mirrors the hall (Fresnel, Schlick F0 0.04), so the court does not show through it edge-on\n"
       "     vec3 Vg=normalize(cameraPosition-vPos); float Fg=0.04+0.96*pow(1.0-abs(dot(N,Vg)),5.0);\n"
       "     lit=mix(lit,vec3(0.05,0.052,0.056)*max(E,vec3(0.25)),Fg); alphaG=mix(alpha,1.0,Fg); }`:''}\n"
       "    gl_FragColor=vec4(lit+vec3(0.55,0.2,1.0)*lipW*0.28,mix(alphaG,1.0,frost)*holeA);\n")
assert old in s
s = s.replace(old, new)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('patched')
