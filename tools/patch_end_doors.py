# index.html (2026-09-08): the end walls' doors re-read. The west "lit doorway" 12.9-14.6 is a double door
# with a round window in each leaf: the day frames (w2_000252 zoom crop, lines-west-w2_000252-zoom.jpg) show
# two bright discs about 0.4 m across at d 13.25 and 13.95, h 1.5, on dark leaves (brightness up the door
# 22-27 against the stone's 27-29, the discs 140-180), and endwalls.json's night "bright box with two light
# sources inside it" (d 12.6-14.4, h 1.3-2.5) is the same pair of windows lit from the lobby. The 11.5-12.7
# porthole door was a misplacement of those windows: nothing shows there by day. The east's "lit doorway with
# two lamps in it" (endwalls.json, d 4.4-8.2) is the same kind of door: the 2014 double doors 5.7-8.0 get a
# window per leaf (positions unmeasured, the leaf centres).
p = 'index.html'
s = open(p, encoding='utf-8').read()
old = " doors:{west:[[11.5,12.7,'port'],[12.9,14.6,'lit']], east:[[5.7,8.0,'dark'],[9.8,11.1,'port']]}};\n"
new = " doors:{west:[[12.9,14.6,'port2',[13.25,13.95]]], east:[[5.7,8.0,'port2',[6.28,7.42]],[9.8,11.1,'port']]}};   /* port2: a double door, a round window per leaf at the listed d (west measured, east the leaf centres) */\n"
assert old in s; s = s.replace(old, new)
old = ("  for(const [d0,d1,kind] of W.doors[side]){\n"
       "   if(kind==='lit')quad([[uD,d0,0],[uD,d1,0],[uD,d1,2.4],[uD,d0,2.4]],litMat,'gallery-door');\n"
       "   else { quad([[uD,d0,0],[uD,d1,0],[uD,d1,2.4],[uD,d0,2.4]],doorMat,'gallery-door-leaf');\n"
       "    if(kind==='port'){ const dm=(d0+d1)/2, r=0.18, uP=uD-s*0.005;\n"
       "     quad([[uP,dm-r,1.5-r],[uP,dm+r,1.5-r],[uP,dm+r,1.5+r],[uP,dm-r,1.5+r]],portMat,'gallery-porthole'); } } }\n")
new = ("  for(const [d0,d1,kind,ports] of W.doors[side]){\n"
       "   if(kind==='lit')quad([[uD,d0,0],[uD,d1,0],[uD,d1,2.4],[uD,d0,2.4]],litMat,'gallery-door');\n"
       "   else { quad([[uD,d0,0],[uD,d1,0],[uD,d1,2.4],[uD,d0,2.4]],doorMat,'gallery-door-leaf');\n"
       "    const pd=kind==='port2'?ports:kind==='port'?[(d0+d1)/2]:[]; const r=0.2, uP=uD-s*0.005;   /* the round windows, 0.4 across at h 1.5 */\n"
       "    for(const dm of pd)quad([[uP,dm-r,1.5-r],[uP,dm+r,1.5-r],[uP,dm+r,1.5+r],[uP,dm-r,1.5+r]],portMat,'gallery-porthole'); } }\n")
assert old in s; s = s.replace(old, new)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('patched')
