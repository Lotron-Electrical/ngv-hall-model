# The end galleries rebuilt from the evidence of 2026-09-08 (string patches on index.html):
#   python tools/patch_endwalls.py
import sys
p = 'index.html'
s = open(p, encoding='utf-8').read()

def rep(old, new):
    global s
    if s.count(old) != 1: raise SystemExit('anchor count %d: %s' % (s.count(old), old[:100]))
    s = s.replace(old, new)

# 1. the scan's own end closures are the real ground-level end walls: keep them below the first gallery
rep("     if(!longWall&&((su>-5.3&&su<-4.0)||(su>48.5&&su<49.6)))discard;",
    "     if(!longWall&&sy>${ENDW.floors[0]-ENDW.slab}&&((su>-5.3&&su<-4.0)||(su>48.5&&su<49.6)))discard;")

# 2. ENDW and buildEndWalls
a = s.index("// MEASURED 2026-09-08 (agent-ref-walls/measure/endwalls.json, parallax of the posed frames rectified")
b = s.index("// ============ LED strips, built live from runs.json ============")
new = r'''// THE END GALLERIES, REBUILT 2026-09-08 (Lloyd: "you need to get the ends of the hall correct"). Evidence:
//  - the 4K balcony frames (day4k, 138 frames, all shot from the EAST gallery, u 48.0, d 13.4,
//    h 9.7): the person stood on the top gallery 3.9 m in front of the plate end, so the galleries
//    PROJECT into the hall from the end wall, they are not a recess behind it; the far (west) end in
//    those frames: an open top gallery with people behind a dark glass balustrade, a stone wall behind
//    them with double doors, a dark fascia under the floor, a middle level with a lit ceiling of
//    downlights, a lower level, and a bright lit lobby on the ground (the photograph 756d0ba6 and the
//    balcony still b0cefe7f show the same stack: three dark balustrade bands across the full width);
//  - the 1968 ground plan (BUIL005490, 27.1 mm/px from the 7.366 m column pitch): the reception
//    hall's end walls stand 3.7 m past the outer columns, i.e. the gallery face is u 4.05 / 48.2;
//    the west end opens to the adjoining gallery on the ground, the east end is a wall (the kitchen);
//  - the scan's own closures, u -4.65 (west) and 49.06 (east), are those ground-level walls (the
//    lobby's back wall and the kitchen wall), so below the first gallery they are kept, not cut;
//  - measure/endwalls.json: horizontal elements h 3.99, 6.33 and 8.34 (the three floors), a
//    face-plane edge h 3.80/3.91 both ends (the first fascia) and h 9.96/10.04 (the stone wall
//    over the top gallery); the east gallery itself never resolves (its frames all stand 13 m out),
//    so the east is built as the west, said so here.
// Unmeasured and taken as: the fascia depth 0.45 m under each floor, the glass balustrade 1.1 m
// (a balustrade's code height), the levels' ceilings 0.45 m under the floor above.
const ENDW={west:0.344, east:51.906, top:13.5, face:3.7, floors:[3.99,6.33,8.34], slab:0.45, rail:1.1, scanEast:49.06, scanWest:-4.65, dSouth:15.364};
function buildEndWalls(root){
 const W=ENDW, F=WALLF, O=EVENT.N.origin, HU=EVENT.N.u, HN=EVENT.N.inRoom;
 const hp=(u,d,y)=>new THREE.Vector3().copy(O).addScaledVector(HU,u).addScaledVector(HN,d).setY(O.y+y);
 // a 1 x 1 white map: the stone shader reads the bake only as a recess mask, and a built quad has no recesses
 const white=new THREE.DataTexture(new Uint8Array([255,255,255,255]),1,1); white.needsUpdate=true; white.colorSpace=THREE.SRGBColorSpace;
 const stone=photoMaterial({map:white, name:'walls'}); stone.side=THREE.DoubleSide; photoMats.push(stone);
 // the carpet beyond the scan's floor: the carpet's own measured albedo (FLOOR_ALB), lit like the floor
 const carpet=photoMaterial({color:0x854449, name:'floor-extension'}); carpet.side=THREE.DoubleSide; photoMats.push(carpet);
 const darkMat=new THREE.MeshLambertMaterial({color:0x2a2622, side:THREE.DoubleSide, name:'gallery-fascia'});
 const floorMat=new THREE.MeshLambertMaterial({color:0x4a4640, side:THREE.DoubleSide, name:'gallery-floor'});
 const ceilMat=new THREE.MeshLambertMaterial({color:0x9a948a, side:THREE.DoubleSide, name:'gallery-ceiling'});
 const backMat=new THREE.MeshLambertMaterial({color:0x7d776e, side:THREE.DoubleSide, name:'gallery-back'});
 const lobbyMat=new THREE.MeshBasicMaterial({color:0xd9d3c8, side:THREE.DoubleSide, name:'lobby-ceiling'});
 const railMat=new THREE.MeshBasicMaterial({color:0x0c1014, side:THREE.DoubleSide, transparent:true, opacity:0.62, name:'gallery-rail'});
 const quad=(pts,mat,name)=>{ const pos=new Float32Array(12); pts.forEach((p,i)=>{ const v=hp(...p); pos.set([v.x,v.y,v.z],3*i); });
  const geo=new THREE.BufferGeometry(); geo.setAttribute('position',new THREE.BufferAttribute(pos,3));
  geo.setAttribute('uv',new THREE.BufferAttribute(new Float32Array([0,0,1,0,1,1,0,1]),2)); geo.setIndex([0,1,2,0,2,3]); geo.computeVertexNormals();
  const m=new THREE.Mesh(geo,mat); m.name=name; root.add(m); solids.push(m); return m; };
 const D=W.dSouth;
 // the long walls and the carpet from the scan's east closure to the plate end
 { const u0=W.scanEast-0.02, u1=W.east;
  quad([[u0,F.dNorth,0],[u1,F.dNorth,0],[u1,F.dNorth,W.top],[u0,F.dNorth,W.top]],stone,'wall-north-extension');
  quad([[u0,D,0],[u1,D,0],[u1,D,W.top],[u0,D,W.top]],stone,'wall-south-extension');
  quad([[u0,0,0],[u1,0,0],[u1,D,0],[u0,D,0]],carpet,'floor-extension'); }
 // the two galleries: three open floors projecting W.face from the end wall, full width
 for(const [uB,s,ground] of [[W.west,-1,W.scanWest],[W.east,1,W.scanEast]]){   /* s: from the hall into the end */
  const uF=uB-s*W.face, fl=W.floors, top=W.top;
  // the stone wall over the top gallery, on the plate end, from the top floor up
  quad([[uB,0,fl[2]],[uB,D,fl[2]],[uB,D,top],[uB,0,top]],stone,'end-wall');
  // the ground: the scan's own wall stays (kept in the shader below the first fascia); its ceiling is the
  // first floor's underside, back to that wall: the west is the lit lobby, the east the kitchen wall
  quad([[uF,0,fl[0]-W.slab],[ground,0,fl[0]-W.slab],[ground,D,fl[0]-W.slab],[uF,D,fl[0]-W.slab]],s<0?lobbyMat:darkMat,'ground-soffit');
  for(let i=0;i<fl.length;i++){ const y=fl[i], yc=(i+1<fl.length?fl[i+1]:top+1)-W.slab;
   // the fascia under the floor edge, the glass balustrade on it, the floor back to the wall
   quad([[uF,0,y-W.slab],[uF,D,y-W.slab],[uF,D,y],[uF,0,y]],darkMat,'gallery-fascia');
   quad([[uF,0,y],[uF,D,y],[uF,D,y+W.rail],[uF,0,y+W.rail]],railMat,'gallery-rail');
   quad([[uF,0,y],[uB,0,y],[uB,D,y],[uF,D,y]],floorMat,'gallery-floor');
   if(i+1<fl.length){
    // a lit ceiling under the next floor and a back wall on the plate end
    quad([[uF,0,yc],[uB,0,yc],[uB,D,yc],[uF,D,yc]],ceilMat,'gallery-ceiling');
    quad([[uB,0,y],[uB,D,y],[uB,D,yc],[uB,0,yc]],backMat,'gallery-back'); } }
 }
}

'''
s = s[:a] + new + s[b:]

# 3. the stats row
rep("Both end galleries: floor 3.9 m, tiers 6.3 and 8.3 m, head 10.0 m, 6.2 m deep (the west measured, the east copied)",
    "Both end galleries: three open floors (h 3.99, 6.33 and 8.34 m) projecting 3.7 m from the end wall (the 4K balcony frames, the 1968 plan and the posed frames; the west measured, the east built the same), the scan's own ground-level end walls kept")
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('patched')
