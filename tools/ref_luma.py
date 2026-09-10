"""The reference band's rendered luma (p80 per rung, h 10 to 11) through each end's pick: the number wallGain is tuned to."""
import sys,json,math; sys.path.insert(0,'tools')
import numpy as np, cv2
from back_wall_hue import W,HU,HD,UP,SCRATCH
import ends_audit as EA
R=json.load(open(SCRATCH+'/back-wall-hue3.json'))
for e in EA.ENDS:
    for i,p in enumerate(R['picks']):
        if p['region']!=e['pick']: continue
        rd=cv2.imread('render-shots/render-match/r%02d.jpg'%i); S=rd.shape[0]; fr=S/2/math.tan(math.radians(p['sqvfov']/2)); C=W(p['u'],p['d'],p['h'])
        fh=p['fu']*HU+p['fd']*HD; fh/=np.linalg.norm(fh); pr=math.radians(p['pitch']); f=fh*math.cos(pr)+UP*math.sin(pr)
        right=np.cross(f,UP); right/=np.linalg.norm(right); up=np.cross(right,f)
        proj=lambda X:(S/2+fr*((X-C)@right)/((X-C)@f), S/2-fr*((X-C)@up)/((X-C)@f))
        ref=[]
        for h in EA.RUNGS:
            if not (10.0<=h<11.0): continue
            P=np.array([proj(W(*q)) for q in EA.band(h,e)])
            v=EA.read(rd,np.clip(P,0,S-1))
            if v is not None: ref.append(v)
        print('%s reference band p80 luma: median %.1f  (%s)'%(e['name'],np.median(ref),' '.join('%.0f'%v for v in ref)))
