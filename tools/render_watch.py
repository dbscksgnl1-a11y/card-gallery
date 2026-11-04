import sys, math
from pathlib import Path
import numpy as np
from studio_renderer import Renderer, encode
output=Path(sys.argv[1]);output.mkdir(parents=True,exist_ok=True)
renderer=Renderer(800,0)
renderer.set_face(Path(__file__).parent/'textures/watch-face.png')
def mesh(vertices,faces,mat,uv=None):
    renderer.add_mesh(vertices,faces,mat,uv)
def rrpoints(w,h,r,num=18):
    p=[]
    for cx,cy,a in [(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180),(w/2-r,-h/2+r,270)]:
        for t in np.linspace(a,a+90,num,endpoint=False):
            q=np.deg2rad(t);p.append((cx+r*np.cos(q),cy+r*np.sin(q)))
    return p
SILVER=((.70,.69,.66),.85,85,0)
BAND=((.86,.83,.75),0.,30,0)
BLACK=((.025,.027,.03),.45,150,2)
def rounded(w,h,r,z0,z1,bevel,mat,origin=(0,0,0),rotation=None):
    verts=[];uv=[];levels=10
    # Lathe rounded perimeter across the softened thickness.
    ringdata=[]
    for a in np.linspace(-math.pi/2,0,levels):ringdata.append((bevel*(1-math.cos(a)),z0+bevel+bevel*math.sin(a)))
    for a in np.linspace(0,math.pi/2,levels):ringdata.append((bevel*(1-math.cos(a)),z1-bevel+bevel*math.sin(a)))
    for inset,z in ringdata:
        for x,y in rrpoints(w-2*inset,h-2*inset,max(.02,r-inset)):
            verts.append((x,y,z));uv.append((x/w+.5,y/h+.5))
    count=len(verts)//len(ringdata);faces=[]
    for k in range(len(ringdata)-1):
        for j in range(count):
            a=k*count+j;b=k*count+(j+1)%count;c=b+count;d=a+count
            faces.extend([(a,b,c),(a,c,d)])
    for k,reverse in [(0,True),(len(ringdata)-1,False)]:
        center=len(verts);verts.append((0,0,ringdata[k][1]));uv.append((.5,.5))
        for j in range(count):
            tri=(center,k*count+j,k*count+(j+1)%count)
            faces.append(tri[::-1] if reverse else tri)
    v=np.array(verts)
    if rotation is not None:v=v@rotation.T
    v+=np.array(origin)
    mesh(v,faces,mat,uv)
def cylinder(center,r,length,axis,mat,N=96,ridge=False):
    axis=np.array(axis,dtype=float);axis/=np.linalg.norm(axis)
    u=np.cross(axis,[0,1,0])
    if np.linalg.norm(u)<.01:u=np.cross(axis,[1,0,0])
    u/=np.linalg.norm(u);v=np.cross(axis,u)
    rings=[(-length/2,r*.88),(-length/2+.02,r),(length/2-.02,r),(length/2,r*.88)]
    verts=[];faces=[]
    for d,rad in rings:
        for i in range(N):
            a=2*math.pi*i/N;rr=rad*(1+(.022 if i%2 else -.022)) if ridge else rad
            verts.append(np.array(center)+axis*d+rr*(u*math.cos(a)+v*math.sin(a)))
    for j in range(3):
        for i in range(N):
            a=j*N+i;b=j*N+(i+1)%N;faces.extend([(a,b,b+N),(a,b+N,a+N)])
    for j in [0,3]:
        ci=len(verts);verts.append(np.array(center)+axis*rings[j][0])
        for i in range(N):
            tri=(ci,j*N+i,j*N+(i+1)%N);faces.append(tri[::-1] if j==0 else tri)
    mesh(verts,faces,mat)

# Silver rounded case; a closed, thick loop for the sport band.
rounded(1.91,2.32,.48,1.02,1.43,.105,SILVER)
rounded(1.79,2.20,.46,1.405,1.49,.045,BLACK)
rounded(1.66,2.05,.40,1.47,1.498,.008,((0,0,0),0,100,1))
rounded(1.70,2.11,.43,.975,1.045,.03,BLACK)
def band_segment(start,end,width=1.17,offset=0):
    verts=[];faces=[];U=220;V=32
    for i,t in enumerate(np.linspace(start,end,U)):
        # A continuous rounded rectangle ribbon swept around an ellipse.
        yy=2.00*math.sin(t);zz=1.24*math.cos(t)
        no=np.array([0,math.sin(t)/2.0,math.cos(t)/1.24]);no/=np.linalg.norm(no)
        for j in range(V):
            a=2*math.pi*j/V
            # squircle cross section produces flat strap faces with soft edges
            taper=math.sqrt(max(.002,1-max(0,(t-(end-.29))/.29)**2)) if offset else 1
            x=width*taper/2*np.sign(math.cos(a))*abs(math.cos(a))**.28
            thick=.070*np.sign(math.sin(a))*abs(math.sin(a))**.7
            verts.append(np.array([x,yy,zz])+no*(thick+offset))
    for i in range(U-1):
        for j in range(V):
            a=i*V+j;b=i*V+(j+1)%V;faces.extend([(a,b,b+V),(a,b+V,a+V)])
    mesh(verts,faces,BAND)
band_segment(.565,2*math.pi-.565)
# Overlapping band tail and polished pin on the far side.
band_segment(2.67,3.71,1.08,.105)
cylinder((0,-.35,-1.405),.145,.035,(0,0,-1),SILVER)
# Crown with fine fluting, button, microphone and opposite speaker slit.
cylinder((1.02,.47,1.24),.225,.19,(1,0,0),SILVER,192,True)
cylinder((1.125,.47,1.24),.184,.015,(1,0,0),((.76,.75,.72),.85,100,0))
rotY=np.array([[0,0,1],[0,1,0],[-1,0,0]])
rounded(.17,.56,.08,-.015,.035,.018,SILVER,origin=(.947,-.51,1.24),rotation=rotY)
cylinder((.959,-.10,1.22),.025,.01,(1,0,0),BLACK,32)
rounded(.048,.51,.023,-.01,.01,.005,BLACK,origin=(-.958,.05,1.22),rotation=rotY)
# Ceramic underside sensor disc, rings and optical windows.
cylinder((0,0,.96),.61,.10,(0,0,-1),((.12,.13,.14),.65,100,2))
cylinder((0,0,.90),.48,.025,(0,0,-1),BLACK)
cylinder((0,0,.88),.20,.015,(0,0,-1),((.05,.075,.08),.6,200,2))
for a in np.linspace(0,2*math.pi,4,endpoint=False):
    x=.325*math.cos(a);y=.325*math.sin(a)
    cylinder((x,y,.88),.092,.015,(0,0,-1),((.12,.14,.15),.8,180,2))
    cylinder((x,y,.868),.065,.01,(0,0,-1),((.015,.035,.03),.6,180,2))


frames=[]
indices=[int(x) for x in sys.argv[2:]] if len(sys.argv)>2 else range(180)
for idx in indices:
    a=math.radians(-32)+idx*2*math.pi/180
    model=np.array([[math.cos(a),0,math.sin(a),0],[0,1,0,0],[-math.sin(a),0,math.cos(a),0],[0,0,0,1]],dtype='f4')
    r=math.radians(-7);lean=np.array([[math.cos(r),-math.sin(r),0,0],[math.sin(r),math.cos(r),0,0],[0,0,1,0],[0,0,0,1]],dtype='f4')
    frame=renderer.render([lean@model],[0,1.,9.],2.75);frames.append(frame)
    if len(sys.argv)>2:frame.save(output/f'watch-{idx:03d}.png')
    if idx%30==0:print('Watch frame',idx,flush=True)
if len(sys.argv)==2:encode(frames,output,'card6-watch-3d-v3')
