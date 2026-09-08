# index.html (2026-09-09): the west top gallery's south doorway as the 4K frame d4_000049 has it: a pale lit panel
# 2.9 m wide (d 12.4-15.3) on the back wall round a darker door opening (d 13.35-14.15), and a green exit light
# over the door. The old build had one bright 0.8 m slot, the frame's tones the other way round.
p = 'index.html'; s = open(p, encoding='utf-8').read()
old = "westTopDoor:[13.4,14.2,10.0],"
new = "westTopDoor:[13.35,14.15,10.0], westTopPanel:[12.4,15.3], westTopExit:[13.3,13.85],"
assert old in s; s = s.replace(old, new, 1)
old = ("  if(s<0){ const [d0,d1,hd]=W.westTopDoor, du=uB-s*0.01;   /* the lit doorway behind the top floor, a hair in front of the back wall */\n"
       "   quad([[du,d0,fl[1]],[du,d1,fl[1]],[du,d1,hd],[du,d0,hd]],litMat,'gallery-door'); }\n")
new = ("  if(s<0){ const [d0,d1,hd]=W.westTopDoor, du=uB-s*0.01, [p0,p1]=W.westTopPanel, [e0,e1]=W.westTopExit;\n"
       "   /* the south doorway behind the top floor as d4_000049 (east deck, 45 m off) reads it: a pale panel 2.9 m wide\n"
       "      from the floor to the head, 1.25x the back wall's tone, round a door opening 0.95x the stone (people in it),\n"
       "      the green exit light over the door; a hair in front of the back wall */\n"
       "   quad([[du,p0,fl[1]],[du,p1,fl[1]],[du,p1,W.head],[du,p0,W.head]],panelMat,'gallery-panel');\n"
       "   quad([[du-s*0.005,d0,fl[1]],[du-s*0.005,d1,fl[1]],[du-s*0.005,d1,hd],[du-s*0.005,d0,hd]],topDoorMat,'gallery-door');\n"
       "   quad([[du-s*0.02,e0,W.head-0.32],[du-s*0.02,e1,W.head-0.32],[du-s*0.02,e1,W.head-0.12],[du-s*0.02,e0,W.head-0.12]],exitLitMat,'exit-sign'); }\n")
assert old in s; s = s.replace(old, new, 1)
old = "const litMat=new THREE.MeshBasicMaterial({color:0xe8e2d6, side:THREE.DoubleSide, name:'gallery-door'});"
new = (old + "\n const panelMat=dnm(0x2a2622,0xac9478,'gallery-panel');   /* 1.25x topBackMat by day (d4_000049) */\n"
       " const topDoorMat=dnm(0x3a342c,0x836f5b,'gallery-door');      /* 0.95x the stone by day, a hair darker than the panel */\n"
       " const exitLitMat=new THREE.MeshBasicMaterial({color:0x2ee88a, side:THREE.DoubleSide, name:'exit-sign'});")
assert old in s; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s); print('patched')
