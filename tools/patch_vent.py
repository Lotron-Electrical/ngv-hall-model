# index.html (2026-09-09): the east deck's floor vent strip as a perforated plate in the deck's own tone (the
# straight-down frame d4_000232 reads the plate no darker than the deck, a grid of dark holes on a 24 mm pitch).
p = 'index.html'; s = open(p, encoding='utf-8').read()
old = "const [v0,v1,vd0,vd1]=W.eastVent, hv=fl[1]+0.003, ventMat=new THREE.MeshBasicMaterial({color:0x0b0b0c, side:THREE.DoubleSide, name:'gallery-vent'}); quad([[v0,vd0,hv],[v1,vd0,hv],[v1,vd1,hv],[v0,vd1,hv]],ventMat,'gallery-vent'); }"
new = ("const [v0,v1,vd0,vd1]=W.eastVent, hv=fl[1]+0.003;\n"
       "   // a plate the deck's own tone with a grid of dark holes, 24 mm pitch (the frame: 40 px, 0.6 mm per px)\n"
       "   const vc=document.createElement('canvas'); vc.width=128; vc.height=256; const vx=vc.getContext('2d'); vx.fillStyle='#fff'; vx.fillRect(0,0,128,256); vx.fillStyle='#3a3a3a';\n"
       "   const vp=128/((v1-v0)/0.024); for(let yy=vp/2; yy<256; yy+=vp)for(let xx=vp/2; xx<128; xx+=vp){ vx.beginPath(); vx.arc(xx,yy,vp*0.3,0,Math.PI*2); vx.fill(); }\n"
       "   const ventMat=dnm(0x1a1c1e,0x85898d,'gallery-vent'); ventMat.map=new THREE.CanvasTexture(vc); ventMat.map.colorSpace=THREE.SRGBColorSpace;\n"
       "   quad([[v0,vd0,hv],[v1,vd0,hv],[v1,vd1,hv],[v0,vd1,hv]],ventMat,'gallery-vent'); }")
assert old in s; s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s); print('patched')
