import sys, math
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicSpline
from skimage.measure import marching_cubes
from studio_renderer import Renderer, encode
output=Path(sys.argv[1]);output.mkdir(parents=True,exist_ok=True)
renderer=Renderer(800,1);geometry=[]
WHITE=((.92,.935,.96),0.,100,0)
SILICONE=((.87,.89,.92),0.,28,0)
BLACK=((.025,.027,.03),.45,150,2)
GRILLE=((.035,.039,.045),.15,80,1)
def mesh(vertices,faces,mat,uv=None):
    geometry.append(np.asarray(vertices,dtype='f4'))
    renderer.add_mesh(vertices,faces,mat,uv)
def ellipse(center,radii,mat):
    verts=[];faces=[];u=64;v=40
    for i in range(v+1):
        p=-math.pi/2+math.pi*i/v
        for j in range(u):
            t=2*math.pi*j/u
            verts.append(np.array(center)+np.array(radii)*[math.cos(p)*math.cos(t),math.sin(p),math.cos(p)*math.sin(t)])
    for i in range(v):
        for j in range(u):
            a=i*u+j;b=i*u+(j+1)%u;faces.extend([(a,a+u,b+u),(a,b+u,b)])
    mesh(verts,faces,mat)

# Seamless union of an ellipsoidal housing and a short, rounded stem.
lo=np.array([-.95,-1.30,-.65]);hi=np.array([.65,1.25,.65]);dim=np.array([110,168,94])
step=(hi-lo)/(dim-1)
grid=np.stack(np.meshgrid(*[np.linspace(lo[i],hi[i],dim[i]) for i in range(3)],indexing="ij"),-1)
body=(np.linalg.norm((grid-[-.15,.50,0])/[.65,.68,.54],axis=-1)-1)*.54
p=grid-[.20,0,.06];p[...,1]-=np.clip(p[...,1],-1.,.23)
stem=np.linalg.norm(p*[1,1,1.10],axis=-1)-.225
h=np.clip(.5+.5*(stem-body)/.20,0,1)
field=stem*(1-h)+body*h-.20*h*(1-h)
vertices,faces,_,_=marching_cubes(field,0,spacing=step);vertices+=lo
signed=np.sum(np.einsum("ij,ij->i",vertices[faces[:,0]],np.cross(vertices[faces[:,1]],vertices[faces[:,2]])))
if signed<0:faces=faces[:,::-1]
mesh(vertices,faces,WHITE)
del grid,body,stem,field,p

# A hollow silicone tip, with a rolled lip and an internal acoustic opening.
axis=np.array([-.84,-.14,-.52]);axis/=np.linalg.norm(axis)
u=np.cross(axis,[0,1,0]);u/=np.linalg.norm(u);v=np.cross(axis,u);origin=np.array([-.51,.20,-.03])
profile=[(-.10,.19),(-.04,.24),(.03,.29),(.10,.36),(.18,.405),(.26,.425),(.33,.419),(.39,.392),(.43,.35),(.45,.30),(.452,.25),(.435,.215),(.40,.20),(.34,.205),(.26,.22),(.17,.215),(.08,.18),(-.02,.16)]
pr=CubicSpline(np.arange(len(profile)),np.array(profile))(np.linspace(0,len(profile)-1,100))
verts=[];faces=[];count=96
for distance,radius in pr:
    for j in range(count):
        t=2*math.pi*j/count
        verts.append(origin+axis*distance+radius*(u*math.cos(t)+v*math.sin(t)))
for i in range(len(pr)-1):
    for j in range(count):
        a=i*count+j;b=i*count+(j+1)%count;faces.extend([(a,b,b+count),(a,b+count,a+count)])
mesh(verts,faces,SILICONE)
# Dark acoustic membrane at the base of the hollow tip.
verts=[origin+axis*.075];uv=[(.5,.5)];faces=[]
for j in range(96):
    a=j*2*math.pi/96
    verts.append(origin+axis*.075+.168*(u*math.cos(a)+v*math.sin(a)));uv.append((.5+.5*math.cos(a),.5+.5*math.sin(a)))
for j in range(96):faces.append((0,1+j,1+(j+1)%96))
mesh(verts,faces,GRILLE,uv)

def shell_patch(phi,theta,w,h,mat,offset=.006):
    verts=[];uv=[];faces=[];u=64;v=14
    for i in range(v+1):
        rad=i/v
        for j in range(u):
            a=j*2*math.pi/u
            xx=rad*w*np.sign(math.cos(a))*abs(math.cos(a))**.65
            yy=rad*h*np.sign(math.sin(a))*abs(math.sin(a))**.65
            p=phi+yy;t=theta+xx
            n=np.array([math.cos(p)*math.cos(t),math.sin(p),math.cos(p)*math.sin(t)])
            verts.append(np.array([-.15,.5,0])+[.65,.68,.54]*n+offset*n)
            uv.append((xx/w*.5+.5,yy/h*.5+.5))
    for i in range(v):
        for j in range(u):
            a=i*u+j;b=i*u+(j+1)%u;faces.extend([(a,a+u,b+u),(a,b+u,b)])
    mesh(verts,faces,mat,uv)

shell_patch(.68,1.12,.21,.32,BLACK,.008)
shell_patch(.68,1.12,.19,.30,GRILLE,.010)
shell_patch(-.35,2.24,.22,.275,BLACK,.009)
shell_patch(.45,4.55,.15,.27,GRILLE,.010)
ellipse((.20,-.61,.267),(.070,.30,.018),((.90,.915,.94),.04,110,0))
ellipse((.20,-1.197,.06),(.158,.028,.129),((.64,.67,.70),.90,140,0))
ellipse((.20,-1.219,.06),(.085,.012,.042),BLACK)


allpoints=np.concatenate(geometry);frames=[]
indices=[int(x) for x in sys.argv[2:]] if len(sys.argv)>2 else range(180)
for idx in indices:
    a=idx*2*math.pi/180
    rot=np.array([[math.cos(a),0,math.sin(a),0],[0,1,0,0],[-math.sin(a),0,math.cos(a),0],[0,0,0,1]],dtype='f4')
    xmax=np.max(allpoints@rot[0,:3]);models=[]
    for side in [-1,1]:
        mirror=np.diag([-side,1,1,1]).astype('f4')
        trans=np.eye(4,dtype='f4');trans[0,3]=side*(.16+xmax)
        models.append(trans@mirror@rot)
    frame=renderer.render(models,[0,.65,9.0],2.5);frames.append(frame)
    if len(sys.argv)>2:frame.save(output/f'airpods-{idx:03d}.png')
    if idx%30==0:print('AirPods frame',idx,flush=True)
if len(sys.argv)==2:encode(frames,output,'card7-airpods-3d-v2')
