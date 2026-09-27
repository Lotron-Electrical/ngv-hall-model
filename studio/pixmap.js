// THE PIXEL MAP (Lloyd, 2026-09-27: "an app like caustic 3 that also had pixel strip visuals as a
// layer"): the MADRIX preview window for the studio. Every strip in the hall laid flat, twelve
// columns of eight strips each, north row on the left and south on the right, painted every frame
// by the same compositor the hall runs. It sits under every view and over the bottom of the hall,
// so what the lights are doing is visible while a pattern is being edited, not only on the Hall tab.
//
// It paints its own small pixel array rather than reading the hall's: the hall's is ten thousand
// LEDs and lives in an iframe that a phone may not have drawn yet. The looks only read s (height up
// the strip), col, colx, gap and pid, so a 12 x 8 x ROWS grid carrying the same five facts paints
// the same picture the hall does, just at a lower resolution up each strip.
(function(){
'use strict';
const Studio=window.Studio=window.Studio||{};

const COLS=12, GAPS=8;
// display gamma for the canvas: the compositor writes linear light
const GAM=new Uint8ClampedArray(1025); for(let i=0;i<=1024;i++){ const x=i/1024; GAM[i]=Math.round(255*(x<=0.0031308?x*12.92:1.055*Math.pow(x,1/2.4)-0.055)); }
const toByte=(v)=>v<=0?0:v>=1?255:GAM[(v*1024)|0];

// the pixel facts for one grid: the same fields index.html's P carries
function makeP(rows){
 const n=COLS*GAPS*rows;
 const P={n, rows, s:new Float32Array(n), col:new Uint8Array(n), gap:new Uint8Array(n), colx:new Float32Array(n), pid:new Uint32Array(n)};
 let k=0;
 for(let c=0;c<COLS;c++)for(let g=0;g<GAPS;g++)for(let j=0;j<rows;j++){
  P.s[k]=(j+0.5)/rows; P.col[k]=c; P.gap[k]=g+1; P.colx[k]=(c%6)/5; P.pid[k]=k; k++; }
 return P;
}
// where pixel k lands on the flat map: a strip per gap, a one-cell gutter between columns and a
// wider one between the north and south rows
const W=COLS*(GAPS+1)-1+2;
function cellX(c,g){ return c*(GAPS+1)+g+(c>=6?2:0); }

Studio.createPixmap=function(opts){
 opts=opts||{};
 const rows=opts.rows||36;
 const P=makeP(rows);
 const a=new Float32Array(P.n*3);
 const off=document.createElement('canvas'); off.width=W; off.height=rows;
 const octx=off.getContext('2d'); const img=octx.createImageData(W,rows);
 // the empty cells are a dark ground and the unlit LEDs a shade above it, so the strips read as
 // strips even in a blackout
 // Over the hall (overlay) the ground is clear and an unlit LED is a faint ghost, so the hall shows
 // through everywhere the strips are dark and the map reads as a layer on top of it.
 function paintImage(overlay){
  const d=img.data;
  for(let i=0;i<d.length;i+=4){ d[i]=10; d[i+1]=11; d[i+2]=14; d[i+3]=overlay?0:255; }
  for(let i=0;i<P.n;i++){ const c=P.col[i], g=P.gap[i]-1, j=Math.round(P.s[i]*rows-0.5);
   const x=cellX(c,g), y=rows-1-j, o=(y*W+x)*4, q=i*3;
   const r=toByte(a[q]), gg=toByte(a[q+1]), bb=toByte(a[q+2]);
   d[o]=Math.max(24,r); d[o+1]=Math.max(24,gg); d[o+2]=Math.max(28,bb);
   d[o+3]=overlay?Math.min(215,60+Math.max(r,gg,bb)*2):255; }
  octx.putImageData(img,0,0);
 }
 // blit the small image up to the canvas's real size, crisp, with a soft glow on top the way a
 // diffused strip blooms. The glow is skipped where the browser has no canvas filter.
 function blit(cv,labels,overlay){
  const dpr=Math.min(2,window.devicePixelRatio||1), cw=cv.clientWidth, ch=cv.clientHeight;
  if(!cw||!ch)return;
  const w=Math.round(cw*dpr), h=Math.round(ch*dpr);
  if(cv.width!==w||cv.height!==h){ cv.width=w; cv.height=h; }
  const ctx=cv.getContext('2d'), lab=labels?Math.round(12*dpr):0, mh=h-lab;
  if(overlay)ctx.clearRect(0,0,w,h); else { ctx.fillStyle='#08090b'; ctx.fillRect(0,0,w,h); }
  ctx.imageSmoothingEnabled=false; ctx.globalCompositeOperation='source-over'; ctx.globalAlpha=1;
  ctx.drawImage(off,0,0,W,rows,0,0,w,mh);
  if('filter' in ctx){ ctx.save(); ctx.filter='blur('+Math.max(2,Math.round(w/W*0.9))+'px)'; ctx.globalCompositeOperation='lighter'; ctx.globalAlpha=0.55;
   ctx.imageSmoothingEnabled=true; ctx.drawImage(off,0,0,W,rows,0,0,w,mh); ctx.restore(); }
  if(labels){ ctx.fillStyle=overlay?'#e9e6df':'#9a978f'; ctx.font=(10*dpr)+'px "IBM Plex Sans",system-ui,sans-serif'; ctx.textAlign='center'; ctx.textBaseline='bottom';
   for(let c=0;c<COLS;c++){ const x=(cellX(c,0)+GAPS/2)/W*w; ctx.fillText((c<6?'N':'S')+(c%6+1),x,h-dpr); } }
 }
 // paint a show (frame + state already set by the caller) into this map and onto a canvas
 function draw(show,cv,layers,labels,overlay){
  if(!show)return;
  if(layers&&layers.length&&show.paintLayers)show.paintLayers(a,P,layers); else show.paint(a,P);
  paintImage(!!overlay); if(cv)blit(cv,labels,!!overlay);
 }
 // the lit share, for the tests: how many pixels carry any light at all
 function litShare(){ let n=0; for(let i=0;i<P.n;i++){ const q=i*3; if(a[q]+a[q+1]+a[q+2]>0.02)n++; } return n/P.n; }
 return { P, a, draw, litShare, rows };
};
})();
