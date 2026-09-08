# 2026-09-09, part 2: the shader hook, the frame call, the controls and the patch export.
p = 'index.html'; s = open(p, encoding='utf-8').read(); n = 0
def rep(a, b):
    global s, n
    if b in s: return
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b); n += 1

# ---- the glass shader: a pane's id reads its own RGBW texel, and that light sits BEHIND the slab
rep("""   nLights:{value:0},lightPos:{value:lightPos},lightCol:{value:lightCol},blades:{value:bladeTex}},
  vertexShader:`attribute vec4 aux; varying vec3 vCol; varying vec3 vPos; varying vec4 vAux;
   void main(){vCol=color; vAux=aux; vec4 wp=modelMatrix*vec4(position,1.0); vPos=wp.xyz;
    gl_Position=projectionMatrix*viewMatrix*wp;}`,""",
"""   nLights:{value:0},lightPos:{value:lightPos},lightCol:{value:lightCol},blades:{value:bladeTex},
   pix:{value:PIX.tex},pixOn:{value:0},pixGain:{value:PIX.gain},pixThrough:{value:PIX.through},pixSide:{value:PIX.side}},
  vertexShader:`attribute vec4 aux; attribute float pid; varying float vPid;
   varying vec3 vCol; varying vec3 vPos; varying vec4 vAux;
   void main(){vCol=color; vAux=aux; vPid=pid; vec4 wp=modelMatrix*vec4(position,1.0); vPos=wp.xyz;
    gl_Position=projectionMatrix*viewMatrix*wp;}`,""")

rep("""   uniform vec4 lightPos[${MAX_LIGHTS}]; uniform vec4 lightCol[${MAX_LIGHTS}]; uniform sampler2D blades;
   varying vec3 vCol; varying vec3 vPos; varying vec4 vAux;
   float hash21(vec2 p){""",
"""   uniform vec4 lightPos[${MAX_LIGHTS}]; uniform vec4 lightCol[${MAX_LIGHTS}]; uniform sampler2D blades;
   uniform sampler2D pix; uniform float pixOn, pixGain, pixThrough, pixSide;
   varying vec3 vCol; varying vec3 vPos; varying vec4 vAux; varying float vPid;
   float hash21(vec2 p){""")

rep("    vec3 back=sky+lamps+vec3(0.030,0.033,0.040)+vec3(ambient);",
"""    // THE PANE'S OWN BACKLIGHT. Its id picks one texel of the pixel map: rgb is the fixture's colour,
    // alpha is its white channel, and an RGBW emitter puts out both together. Most of it is added to the
    // backlight the sky and the void lamps already provide, so it comes through this pane's dye the way a
    // real light behind the glass would; pixThrough carries the rest past the dye, which is the only way a
    // single image reads across pieces whose own colours span the whole wheel.
    vec2 pxy=vec2(mod(vPid,pixSide),floor(vPid/pixSide));
    vec4 pxc=texture2D(pix,(pxy+vec2(0.5))/pixSide);
    vec3 leds=(pxc.rgb+vec3(pxc.a))*pixGain*pixOn;
    vec3 back=sky+lamps+vec3(0.030,0.033,0.040)+vec3(ambient)+leds*(1.0-pixThrough);""")

rep("    vec3 L=T*back*bodyV*lip;",
    "    vec3 L=T*back*bodyV*lip;\n    L+=leds*pixThrough*bodyV*lip;      // the share that bypasses the slab's own colour")

rep(" m.name='ceiling-glass-pieces'; photoMats.push(m); return m;",
    " m.name='ceiling-glass-pieces'; photoMats.push(m); PIX.uni=m.uniforms; return m;")

# ---- the per-frame fill
rep("function frame(now){ portalStep(now/1000);",
    "function frame(now){ pixStep(Math.min(0.1,(now-last)/1000)); portalStep(now/1000);")

# ---- the controls, under the house lights row
rep("""  <input type="range" id="house" min="0" max="100" value="0"><span id="houseval" style="color:var(--dim);font-size:13px">0%</span></div>""",
"""  <input type="range" id="house" min="0" max="100" value="0"><span id="houseval" style="color:var(--dim);font-size:13px">0%</span></div>
 <!-- The ceiling as a pixel map (Lloyd, 2026-09-09). One pane, one RGBW pixel. -->
 <div class="row"><label for="pixpat">Ceiling pixels</label>
  <select id="pixpat" style="flex:1;min-width:140px">
   <option value="off">Off</option>
   <option value="wash">Colour wash</option>
   <option value="rainbow">Rainbow along the hall</option>
   <option value="sweep">Sweep</option>
   <option value="ripple">Ripple</option>
   <option value="twinkle">Twinkle</option>
   <option value="plasma">Plasma</option>
   <option value="coffer">Coffer chase</option>
   <option value="white">White channel only</option>
  </select><span id="pixval" style="color:var(--dim);font-size:13px">panes</span></div>
 <div class="row"><label for="pixlevel">Pixel level</label>
  <input type="range" id="pixlevel" min="0" max="250" value="100"><span id="pixlevelval" style="color:var(--dim);font-size:13px">100%</span></div>
 <div class="row"><label for="pixhue">Pixel hue</label>
  <input type="range" id="pixhue" min="0" max="100" value="58"><span id="pixhueval" style="color:var(--dim);font-size:13px">58</span></div>
 <div class="row"><label for="pixthru">Past the glass</label>
  <input type="range" id="pixthru" min="0" max="100" value="15"><span id="pixthruval" style="color:var(--dim);font-size:13px">15%</span></div>""")

# ---- wiring, beside the house slider's
rep("document.getElementById('house').oninput=e=>{lit.house=e.target.value/100; document.getElementById('houseval').textContent=e.target.value+'%'; rcSync();};",
"""document.getElementById('house').oninput=e=>{lit.house=e.target.value/100; document.getElementById('houseval').textContent=e.target.value+'%'; rcSync();};
// the ceiling pixel map's own controls. "Past the glass" is the one that needs a word: turned all the way
// down, the light is filtered by each pane's own colour, which is what a real backlight does; turned up, a
// share of it bypasses the dye so a pattern stays readable across pieces of every colour.
{const ps=document.getElementById('pixpat'), pl=document.getElementById('pixlevel'),
       ph=document.getElementById('pixhue'), pt=document.getElementById('pixthru');
 const sync=()=>{ PIX.pattern=ps.value; PIX.on=ps.value==='off'?0:1;
  PIX.gain=1.35*(+pl.value/100); PIX.hue=+ph.value/100; PIX.through=+pt.value/100;
  document.getElementById('pixlevelval').textContent=pl.value+'%';
  document.getElementById('pixhueval').textContent=ph.value;
  document.getElementById('pixthruval').textContent=pt.value+'%';
  if(PIX.n)document.getElementById('pixval').textContent=PIX.n.toLocaleString()+' panes';
  sceneDirty=true; };
 ps.onchange=sync; pl.oninput=sync; ph.oninput=sync; pt.oninput=sync; sync();}""")

open(p, 'w', encoding='utf-8', newline='\n').write(s); print('part 2 patched', n)
