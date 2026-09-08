# index.html (2026-09-08, the ends read again across every source: the 2014 photograph of the east end
# (reference-photos/south-glazing/drawings/great-hall-ngv-2014.jpg, 4732 px, the far end profiled
# row by row), the posed floor frames of both ends with both face hypotheses drawn in
# (tools/end_overlay2.py: the end assemblies stand W.face in front of the plate line at BOTH ends,
# the frames' wall corners fall on that plane, not the plate line), the 4K west frames, endwalls.json
# and the 1968 plans). The stack, one plane at each end:
#   0..4.2   stone ground wall with doors (east: double doors d 5.7-8.0, a porthole door 9.8-11.1;
#            west: a porthole door 11.5-12.7, a lit doorway 12.9-14.6; the 2014 photograph, w1_000028)
#   4.4..6.33 a dark perforated apron under the lower floor (the 2014 band h 4.39-6.14, +-0.15)
#   6.33     the lower floor, a glass balustrade to 7.22 (endwalls.json: 6.33 and the 7.2 rail)
#   8.08..8.34 the top floor's fascia; 8.34..9.41 a SOLID dark parapet (the 2014 band 8.33-9.43,
#            the 4K frames show people from the chest up above it)
#   10.0     the lit soffit and the stone head above, on the face plane
# The 3.99 "floor" was the ground's soffit line (the face-plane edges 3.80/3.91 in endwalls.json,
# the 2014 dark strip to 4.17), not a balcony: it goes. Back walls on the plate end (3.85 deep, the
# 1968 first-floor plan's 0.46 column pitch).
p = 'index.html'
s = open(p, encoding='utf-8').read()
old = "const ENDW={west:0.344, east:51.906, top:13.5, face:3.85, floors:[3.99,6.33,8.34], slab:0.26, rails:[0.89,0.89,1.07], scanEast:49.06, scanWest:-4.65, dSouth:15.364, head:10.0, westTopDoor:[13.4,14.2,10.0]};"
new = ("const ENDW={west:0.344, east:51.906, top:13.5, face:3.85, floors:[6.33,8.34], slab:0.26, rails:[0.89,1.07], apron:4.4, groundTop:4.2, head:10.0, cut:4.0, scanEast:49.06, scanWest:-4.65, dSouth:15.364, westTopDoor:[13.4,14.2,10.0],\n"
       " doors:{west:[[11.5,12.7,'port'],[12.9,14.6,'lit']], east:[[5.7,8.0,'dark'],[9.8,11.1,'port']]}};")
assert old in s; s = s.replace(old, new)
old = "     if(!longWall&&sy>${ENDW.floors[0]-ENDW.slab}&&((su>-5.3&&su<-4.0)||(su>48.5&&su<49.6)))discard;\n"
new = "     if(!longWall&&sy>${ENDW.cut}&&((su>-5.3&&su<-4.0)||(su>48.5&&su<49.6)))discard;\n"
assert old in s; s = s.replace(old, new)
a = s.index(" // the two galleries: three open floors projecting W.face from the end wall, full width\n")
b = s.index("    quad([[uB,0,y],[uB,D,y],[uB,D,yc],[uB,0,yc]],backMat,'gallery-back'); } }\n }\n") + len("    quad([[uB,0,y],[uB,D,y],[uB,D,yc],[uB,0,yc]],backMat,'gallery-back'); } }\n }\n")
new = r""" // the two ends: one plane, W.face in front of the plate end, carrying the whole stack (the 2014
 // photograph of the east end, the posed floor frames of both ends, endwalls.json): a stone ground
 // wall with doors to W.groundTop, a dark perforated apron from W.apron to the lower floor, a glass
 // balustrade on it, the void, the top floor's fascia, a solid dark parapet, the lit soffit on the
 // head and stone from the head up. The back walls stand on the plate end, W.face behind.
 const meshMat=new THREE.MeshLambertMaterial({color:0x3a3632, side:THREE.DoubleSide, name:'gallery-mesh'});
 const litMat=new THREE.MeshBasicMaterial({color:0xe8e2d6, side:THREE.DoubleSide, name:'gallery-door'});
 const doorMat=new THREE.MeshBasicMaterial({color:0x14120f, side:THREE.DoubleSide, name:'gallery-door-leaf'});
 const portMat=new THREE.MeshBasicMaterial({color:0xd8d2c6, side:THREE.DoubleSide, name:'gallery-porthole'});
 for(const [uB,s,side] of [[W.west,-1,'west'],[W.east,1,'east']]){   /* s: from the hall into the end */
  const uF=uB-s*W.face, fl=W.floors, top=W.top, uD=uF+s*0.01;   /* uD: a hair in front of the face, for the doors */
  // the ground wall and its doors
  quad([[uF,0,0],[uF,D,0],[uF,D,W.groundTop],[uF,0,W.groundTop]],stone,'end-ground-wall');
  for(const [d0,d1,kind] of W.doors[side]){
   if(kind==='lit')quad([[uD,d0,0],[uD,d1,0],[uD,d1,2.4],[uD,d0,2.4]],litMat,'gallery-door');
   else { quad([[uD,d0,0],[uD,d1,0],[uD,d1,2.4],[uD,d0,2.4]],doorMat,'gallery-door-leaf');
    if(kind==='port'){ const dm=(d0+d1)/2, r=0.18, uP=uD-s*0.005;
     quad([[uP,dm-r,1.5-r],[uP,dm+r,1.5-r],[uP,dm+r,1.5+r],[uP,dm-r,1.5+r]],portMat,'gallery-porthole'); } } }
  // the ground's soffit (the lobby ceiling) and back wall
  quad([[uF,0,W.groundTop],[uB,0,W.groundTop],[uB,D,W.groundTop],[uF,D,W.groundTop]],darkMat,'ground-soffit');
  quad([[uB,0,0],[uB,D,0],[uB,D,W.groundTop],[uB,0,W.groundTop]],backMat,'gallery-back');
  // the stone over the galleries stands on the face plane from the head up
  quad([[uF,0,W.head],[uF,D,W.head],[uF,D,top],[uF,0,top]],stone,'end-wall');
  if(s<0){ const [d0,d1,hd]=W.westTopDoor, du=uB-s*0.01;   /* the lit doorway behind the top floor, a hair in front of the back wall */
   quad([[du,d0,fl[1]],[du,d1,fl[1]],[du,d1,hd],[du,d0,hd]],litMat,'gallery-door'); }
  // the lower floor: the apron under it, the glass balustrade on it, the floor and its ceiling back to the plate end
  quad([[uF,0,W.apron],[uF,D,W.apron],[uF,D,fl[0]],[uF,0,fl[0]]],meshMat,'gallery-apron');
  quad([[uF,0,fl[0]],[uF,D,fl[0]],[uF,D,fl[0]+W.rails[0]],[uF,0,fl[0]+W.rails[0]]],railMat,'gallery-rail');
  quad([[uF,0,fl[0]+W.rails[0]-0.06],[uF,D,fl[0]+W.rails[0]-0.06],[uF,D,fl[0]+W.rails[0]],[uF,0,fl[0]+W.rails[0]]],handMat,'gallery-handrail');
  quad([[uF,0,fl[0]],[uB,0,fl[0]],[uB,D,fl[0]],[uF,D,fl[0]]],floorMat,'gallery-floor');
  quad([[uF,0,fl[1]-W.slab],[uB,0,fl[1]-W.slab],[uB,D,fl[1]-W.slab],[uF,D,fl[1]-W.slab]],ceilMat,'gallery-ceiling');
  quad([[uB,0,fl[0]],[uB,D,fl[0]],[uB,D,fl[1]-W.slab],[uB,0,fl[1]-W.slab]],backMat,'gallery-back');
  // the top floor: the fascia, a solid dark parapet, the floor, the lit soffit on the head, the back wall
  quad([[uF,0,fl[1]-W.slab],[uF,D,fl[1]-W.slab],[uF,D,fl[1]],[uF,0,fl[1]]],darkMat,'gallery-fascia');
  quad([[uF,0,fl[1]],[uF,D,fl[1]],[uF,D,fl[1]+W.rails[1]],[uF,0,fl[1]+W.rails[1]]],meshMat,'gallery-parapet');
  quad([[uF,0,fl[1]+W.rails[1]-0.06],[uF,D,fl[1]+W.rails[1]-0.06],[uF,D,fl[1]+W.rails[1]],[uF,0,fl[1]+W.rails[1]]],handMat,'gallery-handrail');
  quad([[uF,0,fl[1]],[uB,0,fl[1]],[uB,D,fl[1]],[uF,D,fl[1]]],floorMat,'gallery-floor');
  quad([[uF,0,W.head],[uB,0,W.head],[uB,D,W.head],[uF,D,W.head]],soffitMat,'gallery-soffit');
  quad([[uB,0,fl[1]],[uB,D,fl[1]],[uB,D,W.head],[uB,0,W.head]],backMat,'gallery-back');
 }
"""
s = s[:a] + new + s[b:]
# the stats row
old = "Both end galleries: three open floors (h 3.99, 6.33 and 8.34 m) projecting 3.7 m from the end wall (the 4K balcony frames, the 1968 plan and the posed frames; the west measured, the east built the same), the scan's own ground-level end walls kept"
new = "Both ends: one plane 3.85 m in front of the plate line (the posed floor frames of both ends) carrying a stone ground wall with doors to 4.2 m, a dark perforated apron under the lower balcony (floor 6.33 m, glass balustrade), a solid dark parapet on the upper balcony (floor 8.34 m) and stone from 10 m up (the 2014 photograph of the east end, the 4K west frames, endwalls.json); 3.85 m deep to the plate line (the 1968 first-floor plan)"
assert old in s; s = s.replace(old, new)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('patched')
