"""Render the reconstructed AirPods pair as a transparent six-second turntable.
Hidden surfaces are estimated from the supplied front reference.
Run: python tools/render_airpods.py OUTPUT_DIRECTORY
Requires numpy, Pillow, moderngl, scipy, scikit-image, EGL and ffmpeg.
"""
import sys, math, json, subprocess
from pathlib import Path
import numpy as np
import moderngl
from PIL import Image
from scipy.interpolate import CubicSpline
from skimage.measure import marching_cubes

output=Path(sys.argv[1]);output.mkdir(parents=True,exist_ok=True)
size=600
ctx=moderngl.create_standalone_context(backend="egl")
fbo=ctx.simple_framebuffer((size,size),components=4,samples=4)
target=ctx.simple_framebuffer((size,size),components=4)
program=ctx.program(vertex_shader="""#version 330
in vec3 in_pos;in vec3 in_norm;in vec2 in_uv;
uniform mat4 model;uniform mat4 vp;
out vec3 P;out vec3 N;out vec2 UV;
void main(){vec4 p=model*vec4(in_pos,1);P=p.xyz;N=mat3(model)*in_norm;UV=in_uv;gl_Position=vp*p;}
""",fragment_shader="""#version 330
in vec3 P;in vec3 N;in vec2 UV;out vec4 color;
uniform vec3 base;uniform float metal;uniform float gloss;uniform int texmode;uniform vec3 eye;
void main(){
vec3 n=normalize(N),v=normalize(eye-P);
vec3 l1=normalize(vec3(-3,6,5)),l2=normalize(vec3(4,2,2)),l3=normalize(vec3(0,3,-5));
float d1=max(dot(n,l1),0),d2=max(dot(n,l2),0),d3=max(dot(n,l3),0);
float f=pow(1-max(dot(n,v),0),5);vec3 r=reflect(-v,n);
float env=pow(max(dot(r,normalize(vec3(-1,2,3))),0),18)*1.25+pow(max(dot(r,normalize(vec3(3,1,1))),0),45)*.75;
float spec=pow(max(dot(n,normalize(l1+v)),0),gloss)*.8+pow(max(dot(n,normalize(l2+v)),0),gloss)*.45;
vec3 c=base*(.58+.32*d1+.14*d2+.15*d3);
c=mix(c,base*(.3+.35*d1+.2*d2)+vec3(env*.63),metal);
c+=vec3(spec*(.30+metal*.5)+f*.07);
if(texmode==1){vec2 q=fract(UV*vec2(28,42));float weave=smoothstep(.28,.38,length(q-.5));c=vec3(.018+.045*weave)*(.7+.3*d1)+vec3(env*.025);}
if(texmode==2)c=base*(.35+.5*d1)+vec3(env*.18+spec*.25+f*.13);
color=vec4(clamp(c,0,1),1);
}
""")
objects=[];geometry=[]
WHITE=((.92,.935,.96),0.,100,0)
SILICONE=((.87,.89,.92),0.,28,0)
BLACK=((.025,.027,.03),.45,150,2)
GRILLE=((.035,.039,.045),.15,80,1)

def mesh(vertices,faces,mat,uv=None):
    v=np.asarray(vertices,dtype="f4");f=np.asarray(faces,dtype="i4")
    geometry.append(v);n=np.zeros_like(v)
    fn=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
    for k in range(3):np.add.at(n,f[:,k],fn)
    n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-9)
    if uv is None:uv=np.zeros((len(v),2))
    data=np.concatenate([v,n,np.asarray(uv,dtype="f4")],axis=1).astype("f4")
    vao=ctx.vertex_array(program,[(ctx.buffer(data.tobytes()),"3f 3f 2f","in_pos","in_norm","in_uv")],ctx.buffer(f.tobytes()))
    objects.append((vao,mat))

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

eye=np.array([0,.65,9.0],dtype="f4");z=eye/np.linalg.norm(eye)
x=np.cross([0,1,0],z);x/=np.linalg.norm(x);y=np.cross(z,x)
view=np.eye(4,dtype="f4");view[:3,:3]=[x,y,z];view[:3,3]=-view[:3,:3]@eye
projection=np.diag([1/2.5,1/2.5,-2/30,1]).astype("f4");projection[2,3]=-1
program["vp"].write((projection@view).T.astype("f4").tobytes());program["eye"].value=tuple(eye)
ctx.enable(moderngl.DEPTH_TEST)
allpoints=np.concatenate(geometry);frames=[]
video=output/"card7-airpods-3d-v1.mp4"
encoder=subprocess.Popen(["ffmpeg","-y","-v","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{size}x{size}","-r","30","-i","-","-an","-c:v","libx264","-crf","20","-pix_fmt","yuv420p","-movflags","+faststart",str(video)],stdin=subprocess.PIPE)
for idx in range(180):
    fbo.use();fbo.clear(0,0,0,0)
    a=idx*2*math.pi/180
    rot=np.array([[math.cos(a),0,math.sin(a),0],[0,1,0,0],[-math.sin(a),0,math.cos(a),0],[0,0,0,1]],dtype="f4")
    xmax=np.max(allpoints@rot[0,:3])
    for side in [-1,1]:
        mirror=np.diag([-side,1,1,1]).astype("f4")
        trans=np.eye(4,dtype="f4");trans[0,3]=side*(.16+xmax)
        program["model"].write((trans@mirror@rot).T.tobytes())
        for vao,mat in objects:
            program["base"].value=mat[0];program["metal"]=mat[1];program["gloss"]=mat[2];program["texmode"]=mat[3];vao.render()
    ctx.copy_framebuffer(target,fbo)
    frame=Image.frombytes("RGBA",(size,size),target.read(components=4)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    frames.append(frame)
    composite=Image.new("RGBA",frame.size,(8,8,10,255));composite.alpha_composite(frame)
    encoder.stdin.write(composite.convert("RGB").tobytes())
    if idx%30==0:print("Rendered frame",idx,flush=True)
encoder.stdin.close()
if encoder.wait()!=0:raise RuntimeError("Video encoding failed")
animation=output/"card7-airpods-3d-v1.webp"
frames[0].save(animation,save_all=True,append_images=frames[1:],duration=[33,33,34]*60,loop=0,quality=82,method=4)
frames[0].save(output/"card7-airpods-3d-preview.png")
im=Image.open(animation);assert im.n_frames==180 and im.info["loop"]==0
duration=0;different=set()
for i in range(im.n_frames):
    im.seek(i);im.load();duration+=im.info["duration"]
    if i in [0,45,90,135]:different.add(im.tobytes())
assert duration==6000 and len(different)==4
assert frames[0].getpixel((0,0))[3]==0
print(json.dumps({"frames":180,"duration_ms":duration,"loop":0,"transparent":True,"quarter_turns":len(different),"webp_bytes":animation.stat().st_size,"mp4_bytes":video.stat().st_size}),flush=True)
