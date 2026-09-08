# index.html (2026-09-08, pose-matched check against d4_000049): the built stone quads take a bake
# value of 13/255 instead of white, so they carry the same recess-mask tone as the scan's walls (the
# scan wall read 90 and the extension 117 in the same shot, a 0.56 linear ratio; 13 sets the mask's
# smoothstep to 0.58 and the albedo to 0.63); the glass balustrades go from 0.62 opaque to 0.28 with
# a solid 60 mm handrail on top (the 4K frame shows people through the glass and a thin dark rail).
p = 'index.html'
s = open(p, encoding='utf-8').read()
old1 = " const white=new THREE.DataTexture(new Uint8Array([255,255,255,255]),1,1); white.needsUpdate=true; white.colorSpace=THREE.SRGBColorSpace;\n"
new1 = (" // a 1 x 1 map at the scan wall's own bake level (13/255: the recess mask reads 0.58, the albedo 0.63), so the\n"
        " // built stone matches the scan's tone; white left the extensions a third brighter (pose check, d4_000049)\n"
        " const white=new THREE.DataTexture(new Uint8Array([13,13,13,255]),1,1); white.needsUpdate=true; white.colorSpace=THREE.SRGBColorSpace;\n")
assert old1 in s; s = s.replace(old1, new1)
old2 = "transparent:true, opacity:0.62, name:'gallery-rail'});"
new2 = "transparent:true, opacity:0.28, name:'gallery-rail'});\n const handMat=new THREE.MeshLambertMaterial({color:0x1a1714, side:THREE.DoubleSide, name:'gallery-handrail'});"
assert old2 in s; s = s.replace(old2, new2)
old3 = "   quad([[uF,0,y],[uF,D,y],[uF,D,y+W.rails[i]],[uF,0,y+W.rails[i]]],railMat,'gallery-rail');\n"
new3 = ("   quad([[uF,0,y],[uF,D,y],[uF,D,y+W.rails[i]],[uF,0,y+W.rails[i]]],railMat,'gallery-rail');\n"
        "   quad([[uF,0,y+W.rails[i]-0.06],[uF,D,y+W.rails[i]-0.06],[uF,D,y+W.rails[i]],[uF,0,y+W.rails[i]]],handMat,'gallery-handrail');\n")
assert old3 in s; s = s.replace(old3, new3)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('patched')
