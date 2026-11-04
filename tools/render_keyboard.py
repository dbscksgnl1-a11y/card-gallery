"""Render the supplied keyboard artwork on raised keys and a rounded 3D case.

Usage: python tools/render_keyboard.py assets [frame indices for preview only]
The unseen underside is a simple illustrative reconstruction.
"""
import sys, math
from pathlib import Path
import numpy as np
from PIL import Image
import studio_renderer as studio

# A diffuse texture material retains the supplied legends without screen emission.
studio.FRAGMENT=studio.FRAGMENT.replace(
    'vec3 albedo=pow(base,vec3(2.2));',
    'vec3 albedo=pow(base,vec3(2.2)); if(product==2&&texmode==3)albedo=pow(texture(face,UV).rgb,vec3(2.2));')
output=Path(sys.argv[1]);output.mkdir(parents=True,exist_ok=True)
renderer=studio.Renderer(800,2)
texture=Path(__file__).parent/'textures/keyboard-source.webp'
renderer.set_face(texture)
TW,TH=Image.open(texture).size
SCALE=6/1146
SILVER=((.76,.77,.79),.92,85,0)
BOTTOM=((.74,.75,.77),.82,70,0)
KEY=((.91,.92,.94),0,32,0)
PRINT=((.91,.92,.94),0,32,3)
DARK=((.035,.038,.045),0,30,0)

def perimeter(w,h,r):
    result=[]
    for cx,cy,a in [(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180),(w/2-r,-h/2+r,270)]:
        for t in np.linspace(a,a+90,10,endpoint=False):
            q=math.radians(t);result.append((cx+r*math.cos(q),cy+r*math.sin(q)))
    return result

def rounded(w,h,r,z0,z1,bevel,material,center=(0,0),top_material=None):
    rings=[]
    for a in np.linspace(-math.pi/2,0,5):rings.append((bevel*(1-math.cos(a)),z0+bevel+bevel*math.sin(a)))
    for a in np.linspace(0,math.pi/2,5):rings.append((bevel*(1-math.cos(a)),z1-bevel+bevel*math.sin(a)))
    verts=[];uv=[];faces=[]
    for inset,z in rings:
        for x,y in perimeter(w-2*inset,h-2*inset,max(.005,r-inset)):
            x+=center[0];y+=center[1]
            verts.append((x,y,z));uv.append(((x/SCALE+627)/TW,1-(634-y/SCALE)/TH))
    n=len(verts)//len(rings)
    for k in range(len(rings)-1):
        for j in range(n):
            a=k*n+j;b=k*n+(j+1)%n
            faces.extend([(a,b,b+n),(a,b+n,a+n)])
    renderer.add_mesh(verts,faces,material,uv)
    # Separate cap vertices keep the broad faces flat, with curved bevel normals.
    for k,reverse in [(0,True),(len(rings)-1,False)]:
        cap=[(center[0],center[1],rings[k][1])]+verts[k*n:(k+1)*n]
        cuv=[((center[0]/SCALE+627)/TW,1-(634-center[1]/SCALE)/TH)]+uv[k*n:(k+1)*n]
        tris=[(0,j+1,(j+1)%n+1) for j in range(n)]
        if reverse:tris=[t[::-1] for t in tris]
        renderer.add_mesh(cap,tris,top_material if top_material and not reverse else material,cuv)

# Body proportions and key positions are measured directly from the reference.
rounded(6,464*SCALE,.19,-.085,.045,.028,SILVER)
rounded(5.91,455*SCALE,.17,-.099,-.079,.009,BOTTOM)
rows=[
 (414,482,[(64,171),(179,249),(257,327),(335,405),(414,483),(492,561),(570,640),(649,719),(727,797),(805,875),(883,953),(962,1032),(1040,1110),(1119,1189)]),
 (491,557,[(65,134),(143,212),(222,291),(300,369),(378,448),(457,526),(536,605),(614,683),(692,761),(771,840),(849,918),(927,997),(1005,1075),(1084,1189)]),
 (566,632,[(65,172),(182,251),(260,329),(339,408),(417,487),(496,565),(574,644),(653,722),(732,801),(810,879),(889,958),(967,1037),(1046,1115),(1124,1190)]),
 (640,705,[(65,193),(202,271),(280,350),(359,429),(438,507),(516,585),(595,664),(673,743),(752,821),(830,900),(909,978),(987,1057),(1066,1190)]),
 (714,779,[(65,232),(241,310),(320,389),(398,468),(477,546),(556,625),(634,704),(713,782),(791,861),(870,939),(949,1018),(1028,1190)]),
 (788,853,[(65,134),(143,212),(222,291),(300,389),(399,782),(792,879),(889,958),(968,1037),(1124,1190)]),
 (788,819,[(1046,1115)]),(821,853,[(1046,1115)])
]
for y0,y1,keys in rows:
    for x0,x1 in keys:
        center=((x0+x1-1254)*SCALE/2,(1268-y0-y1)*SCALE/2)
        w=(x1-x0)*SCALE;h=(y1-y0)*SCALE
        rounded(w+.014,h+.014,.045,.042,.054,.004,DARK,center)
        rounded(w-.010,h-.010,.045,.055,.105,.012,KEY,center,PRINT)

# Four discreet rubber pads give the reverse a credible product silhouette.
for x in [-2.64,2.64]:
    for y in [-.94,.94]:
        rounded(.24,.14,.06,-.118,-.097,.008,DARK,(x,y))

frames=[]
indices=[int(x) for x in sys.argv[2:]] if len(sys.argv)>2 else range(180)
for idx in indices:
    a=math.radians(-18)+idx*2*math.pi/180
    yaw=np.array([[math.cos(a),0,math.sin(a),0],[0,1,0,0],[-math.sin(a),0,math.cos(a),0],[0,0,0,1]],dtype='f4')
    r=math.radians(-8)
    lean=np.array([[math.cos(r),-math.sin(r),0,0],[math.sin(r),math.cos(r),0,0],[0,0,1,0],[0,0,0,1]],dtype='f4')
    frame=renderer.render([lean@yaw],[0,2.1,10.],3.45);frames.append(frame)
    if len(sys.argv)>2:frame.save(output/f'keyboard-{idx:03d}.png')
    if idx%30==0:print('Keyboard frame',idx,flush=True)
if len(sys.argv)==2:studio.encode(frames,output,'card6-keyboard-3d-v1')
