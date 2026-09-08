# index.html (2026-09-09): the top galleries' soffit row of downlights removed (no floor frame shows a bright dot at
# any of the five built positions in either end, w2_000252 / w1_000028 / w1_000404 / w1_000356, max 156 of 255,
# while the back-wall fittings read 255), and the soffit's underside set to its measured tone: 53/44/39 in
# w2_000252 against 142/120/98 for the lit back wall, 0.37 of it.
p = 'index.html'; s = open(p, encoding='utf-8').read()
old = "const topSoffitMat=dnm(0x13100d,0x9c8a70,'gallery-soffit');"
new = "const topSoffitMat=dnm(0x13100d,0x332c26,'gallery-soffit');   /* underside 0.37x the lit back wall by day (w2_000252, 2026-09-09) */"
assert old in s; s = s.replace(old, new, 1)
i = s.index("  // the downlights in the top gallery's soffit (the day frames show a row of them, about 3 m apart)\n")
j = s.index("lampMat,'gallery-downlight'); }\n", i) + len("lampMat,'gallery-downlight'); }\n")
s = s[:i] + "  // (a row of soffit downlights was built here by estimate until 2026-09-09: no floor frame shows one, removed)\n" + s[j:]
open(p, 'w', encoding='utf-8', newline='\n').write(s); print('patched')
