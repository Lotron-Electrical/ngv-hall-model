# 2026-09-09 (Lloyd): "I also want to pixel map the ceiling. So we can display patterns and animations in
# the stained glass as if they are being back lit by RGBW lights behind each stained glass tile."
# Idempotent: every replacement checks for its own result first.
p = 'index.html'; s = open(p, encoding='utf-8').read(); n = 0
def rep(a, b):
    global s, n
    if b in s: return
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b); n += 1

# ---- 1. the pixel map itself, its patterns, and the per-frame fill
rep("let glassMesh=null;", """// ============ THE CEILING AS A PIXEL MAP (Lloyd, 2026-09-09) ============
// "pixel map the ceiling. So we can display patterns and animations in the stained glass as if they are
// being back lit by RGBW lights behind each stained glass tile."
// Every pane is ALREADY its own polygon with its own traced colour (tools/pieces.bin: 6,926 panes, median
// 146 mm across, 149.6 m2 of glass, 97% of them with real chroma), so each pane IS a pixel and nothing has
// to be invented to address one. A pane's id indexes a 128 x 128 RGBA texture: rgb is the fixture's colour
// and ALPHA IS ITS WHITE CHANNEL, because what would sit in the void behind the glass is RGBW, not RGB.
// The shader adds that light to the same "back" term the sky and the void lamps already use, so it arrives
// THROUGH the pane's own dye exactly as a real backlight would: a deep red slab stays red whatever colour
// is put behind it. PIX.through bleeds a share past the dye, because a show that has to read as one image
// across 6,926 differently coloured pieces cannot be filtered by every one of them.
// The patch: 6,926 panes x RGBW = 27,704 channels = 55 universes of 128 pixels.
const PIX={side:128, on:0, gain:1.35, through:0.15, speed:1, pattern:'off', hue:0.58,
           panes:[], n:0, u0:0, u1:1, v0:0, v1:1, tex:null, data:null, uni:null, t:0, wasOn:0,
           uStart:0, ppu:128};
function pixInit(){
 const S=PIX.side; PIX.data=new Uint8Array(S*S*4);
 PIX.tex=new THREE.DataTexture(PIX.data,S,S,THREE.RGBAFormat,THREE.UnsignedByteType);
 PIX.tex.magFilter=THREE.NearestFilter; PIX.tex.minFilter=THREE.NearestFilter;
 PIX.tex.generateMipmaps=false; PIX.tex.needsUpdate=true;
}
pixInit();
function pixHsv(h,sa,v){ h=((h%1)+1)%1*6; const i=Math.floor(h), f=h-i, q=v*(1-sa), w=v*(1-sa*f), e=v*(1-sa*(1-f));
 switch(i%6){case 0:return[v,e,q];case 1:return[w,v,q];case 2:return[q,v,e];case 3:return[q,w,v];case 4:return[e,q,v];default:return[v,q,w];} }
// x runs 0..1 along the hall, y 0..1 across it, q is the pane's own fixed random number (so a twinkle does
// not march in the order the panes were traced), t is seconds. Each returns [r,g,b,w] in 0..1.
const PIXPAT={
 off:()=>[0,0,0,0],
 white:()=>[0,0,0,1],
 wash:(x,y,q,t,P)=>{const c=pixHsv(P.hue,0.92,1); return [c[0],c[1],c[2],0.10];},
 rainbow:(x,y,q,t,P)=>{const c=pixHsv(x*1.15+t*0.07,0.95,1); return [c[0],c[1],c[2],0];},
 sweep:(x,y,q,t,P)=>{const sPos=(t*0.16)%1.25-0.125; const d=Math.abs(x-sPos); const b=Math.exp(-(d/0.07)*(d/0.07));
  const c=pixHsv(P.hue,0.55,1); return [c[0]*b,c[1]*b,c[2]*b,b*0.55];},
 ripple:(x,y,q,t,P)=>{const r=Math.hypot((x-0.5)*3.4,(y-0.5)); const b=0.5+0.5*Math.sin(r*9.0-t*2.2);
  const c=pixHsv(P.hue+r*0.25,0.85,1); const k=b*b; return [c[0]*k,c[1]*k,c[2]*k,k*0.2];},
 twinkle:(x,y,q,t,P)=>{const ph=Math.sin(t*1.5+q*6.2832); const b=Math.pow(Math.max(0,ph),9);
  const c=pixHsv(P.hue+q*0.12,0.35,1); return [c[0]*b,c[1]*b,c[2]*b,b];},
 plasma:(x,y,q,t,P)=>{const v=Math.sin(x*7+t*0.9)+Math.sin(y*5-t*0.7)+Math.sin((x+y)*6+t*0.5);
  const c=pixHsv(P.hue+v*0.09,0.9,1); const b=0.55+0.45*Math.sin(v*1.7+t*0.3); return [c[0]*b,c[1]*b,c[2]*b,0];},
 coffer:(x,y,q,t,P)=>{const i=Math.floor((x*(PIX.u1-PIX.u0))/7.36)+Math.floor((y*(PIX.v1-PIX.v0))/7.50)*7;
  const b=Math.pow(Math.max(0,Math.sin(t*1.1-i*0.9)),3); const c=pixHsv(P.hue+i*0.07,0.8,1);
  return [c[0]*b,c[1]*b,c[2]*b,b*0.25];},
};
// The whole map is refilled each frame from the pattern and pushed as one texture upload: 6,926 texels is
// 27 KB, far cheaper than touching 6,926 materials, and it is the same shape a real controller sends.
function pixStep(dt){
 if(!PIX.tex||!PIX.n)return;
 if(PIX.uni){ PIX.uni.pixOn.value=PIX.on; PIX.uni.pixGain.value=PIX.gain; PIX.uni.pixThrough.value=PIX.through; }
 if(!PIX.on){ if(PIX.wasOn){ PIX.data.fill(0); PIX.tex.needsUpdate=true; PIX.wasOn=0; sceneDirty=true; } return; }
 PIX.wasOn=1; PIX.t+=(dt||0)*PIX.speed;
 const f=PIXPAT[PIX.pattern]||PIXPAT.off, D=PIX.data, t=PIX.t;
 for(let i=0;i<PIX.n;i++){ const q=PIX.panes[i], c=f(q.x,q.y,q.q,t,PIX), o=i*4;
  D[o]=Math.max(0,Math.min(255,c[0]*255))|0; D[o+1]=Math.max(0,Math.min(255,c[1]*255))|0;
  D[o+2]=Math.max(0,Math.min(255,c[2]*255))|0; D[o+3]=Math.max(0,Math.min(255,c[3]*255))|0; }
 PIX.tex.needsUpdate=true; sceneDirty=true;
}
let glassMesh=null;""")

# ---- 2. every pane gets a dense pixel id, a world position and a place in the patch
rep(" const pos=[], col=[], aux=[];", " const pos=[], col=[], aux=[], pid=[];\n PIX.panes.length=0;")
rep("""  kept++;
  const seed=hash(i);""", """  kept++;
  const pane=kept-1;                      // the pane's own pixel id: dense, and the order the patch uses
  {const Wc=lift(cu,cv); PIX.panes.push({u:hcu,v:hcv,X:Wc[0],Y:Wc[1],Z:Wc[2],r:r,g:g,b:b,
    area:Math.abs(A),x:0,y:0,q:hash(i*7919+13)});}
  const seed=hash(i);""")
rep("  const emit=(P,e)=>{ pos.push(P[0],P[1],P[2]); col.push(r*lin,g*lin,b*lin); aux.push(hcu,hcv,seed,e); };",
    "  const emit=(P,e)=>{ pos.push(P[0],P[1],P[2]); col.push(r*lin,g*lin,b*lin); aux.push(hcu,hcv,seed,e); pid.push(pane); };")
rep(" geo.setAttribute('aux',new THREE.BufferAttribute(new Float32Array(aux),4));",
    """ geo.setAttribute('aux',new THREE.BufferAttribute(new Float32Array(aux),4));
 geo.setAttribute('pid',new THREE.BufferAttribute(new Float32Array(pid),1));
 // the map's own frame: every pane's centroid normalised over what the glass actually covers, so a
 // pattern written in 0..1 lands on the canopy and not on the bounding box of the whole model
 PIX.n=PIX.panes.length;
 if(PIX.n){ let a=1e9,b2=-1e9,c2=1e9,d2=-1e9;
  for(const q of PIX.panes){ if(q.u<a)a=q.u; if(q.u>b2)b2=q.u; if(q.v<c2)c2=q.v; if(q.v>d2)d2=q.v; }
  PIX.u0=a; PIX.u1=b2; PIX.v0=c2; PIX.v1=d2;
  for(const q of PIX.panes){ q.x=(q.u-a)/Math.max(b2-a,1e-6); q.y=(q.v-c2)/Math.max(d2-c2,1e-6); }
  const pv=document.getElementById('pixval'); if(pv)pv.textContent=PIX.n.toLocaleString()+' panes';
  console.info(`canopy pixel map: ${PIX.n} panes, hall u ${a.toFixed(2)} to ${b2.toFixed(2)}, v ${c2.toFixed(2)} to ${d2.toFixed(2)}, ${4*PIX.n} RGBW channels`); }""")
open(p, 'w', encoding='utf-8', newline='\n').write(s); print('part 1 patched', n)
