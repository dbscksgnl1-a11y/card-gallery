"""Shared material, studio reflection and soft-shadow renderer for product loops."""
import math, json, subprocess
from pathlib import Path
import numpy as np
import moderngl
from PIL import Image

VERTEX='''#version 330
in vec3 in_pos; in vec3 in_norm; in vec2 in_uv;
uniform mat4 model; uniform mat4 vp; uniform mat4 lightVP;
out vec3 P; out vec3 N; out vec3 Local; out vec2 UV; out vec4 Shadow;
void main(){vec4 p=model*vec4(in_pos,1);P=p.xyz;Local=in_pos;N=mat3(model)*in_norm;UV=in_uv;Shadow=lightVP*p;gl_Position=vp*p;}
'''
FRAGMENT='''#version 330
in vec3 P;in vec3 N;in vec3 Local;in vec2 UV;in vec4 Shadow;out vec4 color;
uniform vec3 base;uniform float metal;uniform float gloss;uniform int texmode;uniform int product;uniform vec3 eye;
uniform sampler2D studio;uniform sampler2D face;uniform sampler2DShadow depthMap;
const float PI=3.14159265359;
float noise(vec3 p){return fract(sin(dot(p,vec3(12.9898,78.233,45.164)))*43758.5453);}
vec3 env(vec3 r,float rough){vec2 uv=vec2(atan(r.z,r.x)/(2*PI)+.5,asin(clamp(r.y,-1,1))/PI+.5);return pow(textureLod(studio,uv,rough*5.5).rgb,vec3(2.2));}
float shadowing(vec3 n,vec3 l){vec3 p=Shadow.xyz/Shadow.w*.5+.5;float bias=max(.0008*(1-dot(n,l)),.00023);float s=0;for(int x=-2;x<=2;x++)for(int y=-2;y<=2;y++)s+=texture(depthMap,vec3(p.xy+vec2(x,y)/1024.,p.z-bias));return s/25.;}
vec3 fresnel(float nv,vec3 f0){return f0+(1-f0)*pow(1-nv,5);}
vec3 light(vec3 n,vec3 v,vec3 l,vec3 albedo,vec3 f0,float rough,float m,vec3 intensity){
 vec3 h=normalize(l+v);float nl=max(dot(n,l),0),nv=max(dot(n,v),.001),nh=max(dot(n,h),0);
 float a=rough*rough,a2=a*a;float den=nh*nh*(a2-1)+1;float D=a2/(PI*den*den+.0001);
 float k=(rough+1)*(rough+1)/8;float G=nv/(nv*(1-k)+k)*nl/(nl*(1-k)+k);
 vec3 F=fresnel(max(dot(h,v),0),f0);vec3 spec=D*G*F/(4*nv*nl+.0001);
 return ((1-F)*(1-m)*albedo/PI+spec)*nl*intensity;
}
vec3 aces(vec3 x){return clamp((x*(2.51*x+.03))/(x*(2.43*x+.59)+.14),0,1);}
void main(){
 vec3 n=normalize(N),v=normalize(eye-P);float nv=max(dot(n,v),0);
 bool isScreen=product==0&&texmode==1;bool isGrille=product==1&&texmode==1;bool soft=gloss<50;
 float m=metal>.7?.94:0.;float rough=soft?.63:(m>.5?.31:.16);
 if(texmode==2)rough=.095;if(isScreen)rough=.075;if(isGrille)rough=.78;
 float grain=noise(floor(Local*420.));rough+= (grain-.5)*(m>.5?.009:soft?.012:.003);
 vec3 albedo=pow(base,vec3(2.2));
 if(soft)albedo*=.995+.01*grain;
 if(m>.5)albedo*=.985+.03*noise(vec3(floor(Local.y*850.),0,0));
 vec3 f0=mix(vec3(soft?.018:.04),albedo,m);
 if(isScreen){albedo=vec3(.002);f0=vec3(.035);}
 vec3 l=normalize(vec3(-3.8,6,5.5));float shade=shadowing(n,l);
 vec3 reflected=reflect(-v,n);vec3 F=fresnel(nv,f0);
 vec3 environment=(env(reflected,rough)*2.8+vec3(.075,.085,.10))*F*(1-rough*.42);
 if(soft)environment*=.22;if(isScreen)environment*=.28;
 vec3 c=albedo*(.26+.10*n.y)*(1-m)*(0.65+.35*shade);
 c+=light(n,v,l,albedo,f0,rough,m,vec3(3.5,3.45,3.35))*shade;
 c+=light(n,v,normalize(vec3(4,1.5,3)),albedo,f0,rough,m,vec3(.85,.95,1.15));
 c+=light(n,v,normalize(vec3(1,4,-5)),albedo,f0,rough,m,vec3(2.0));
 c+=environment;
 if(soft){float sss=pow(max(dot(-n,l),0),3)*.06;c+=albedo*sss;}
 if(isScreen)c+=pow(texture(face,UV).rgb,vec3(2.2))*.9;
 if(isGrille){vec2 q=fract(UV*vec2(38,56));float wire=smoothstep(.29,.43,length(q-.5));c=vec3(.003+.012*wire)*(.75+.5*max(dot(n,l),0))*shade+environment*.01;}
 color=vec4(pow(aces(c),vec3(1/2.2)),1);
}
'''

def look_at(eye):
    eye=np.array(eye,dtype='f4');z=eye/np.linalg.norm(eye);x=np.cross([0,1,0],z);x/=np.linalg.norm(x);y=np.cross(z,x)
    view=np.eye(4,dtype='f4');view[:3,:3]=[x,y,z];view[:3,3]=-view[:3,:3]@eye
    return view

class Renderer:
    def __init__(self,size,product):
        self.size=size;self.product=product;self.objects=[]
        self.ctx=moderngl.create_standalone_context(backend='egl');ctx=self.ctx
        self.fbo=ctx.simple_framebuffer((size,size),components=4,samples=4)
        self.target=ctx.simple_framebuffer((size,size),components=4)
        self.program=ctx.program(vertex_shader=VERTEX,fragment_shader=FRAGMENT)
        self.shadow_program=ctx.program(vertex_shader='''#version 330
in vec3 in_pos;uniform mat4 model;uniform mat4 lightVP;void main(){gl_Position=lightVP*model*vec4(in_pos,1);}
''',fragment_shader='''#version 330
void main(){}
''')
        self.depth=ctx.depth_texture((2048,2048));self.depth.compare_func='<=';self.depth.repeat_x=False;self.depth.repeat_y=False
        self.shadow_fbo=ctx.framebuffer(depth_attachment=self.depth)
        lp=np.diag([1/4.,1/4.,-2/30.,1]).astype('f4');lp[2,3]=-1
        lightvp=(lp@look_at([-3.8,6,5.5])).T.astype('f4').tobytes()
        self.program['lightVP'].write(lightvp);self.shadow_program['lightVP'].write(lightvp)
        self.program['product']=product
        self.env=self.load_texture(Path(__file__).parent/'textures/studio.jpg');self.env.use(0);self.program['studio']=0
        self.face=ctx.texture((1,1),3,bytes([0,0,0]));self.face.use(1);self.program['face']=1
        self.depth.use(2);self.program['depthMap']=2
        ctx.enable(moderngl.DEPTH_TEST)
    def load_texture(self,path):
        im=Image.open(path).convert('RGB').transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        t=self.ctx.texture(im.size,3,im.tobytes());t.build_mipmaps();return t
    def set_face(self,path):
        self.face=self.load_texture(path);self.face.use(1)
    def add_mesh(self,vertices,faces,mat,uv=None):
        v=np.asarray(vertices,dtype='f4');f=np.asarray(faces,dtype='i4');n=np.zeros_like(v)
        fn=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
        for k in range(3):np.add.at(n,f[:,k],fn)
        n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-9)
        if uv is None:uv=np.zeros((len(v),2))
        data=np.concatenate([v,n,np.asarray(uv,dtype='f4')],axis=1).astype('f4');ctx=self.ctx
        buf=ctx.buffer(data.tobytes());indices=ctx.buffer(f.tobytes())
        vao=ctx.vertex_array(self.program,[(buf,'3f 3f 2f','in_pos','in_norm','in_uv')],indices)
        shadow=ctx.vertex_array(self.shadow_program,[(buf,'3f 20x','in_pos')],indices)
        self.objects.append((vao,shadow,mat))
    def render(self,models,eye,extent):
        ctx=self.ctx;p=self.program
        vp=np.diag([1/extent,1/extent,-2/30.,1]).astype('f4');vp[2,3]=-1
        p['vp'].write((vp@look_at(eye)).T.astype('f4').tobytes());p['eye'].value=tuple(eye)
        self.shadow_fbo.use();self.shadow_fbo.clear(depth=1.);ctx.viewport=(0,0,2048,2048)
        for model in models:
            self.shadow_program['model'].write(model.T.astype('f4').tobytes())
            for _,vao,_ in self.objects:vao.render()
        self.fbo.use();ctx.viewport=(0,0,self.size,self.size);self.fbo.clear(0,0,0,0)
        self.env.use(0);self.face.use(1);self.depth.use(2)
        for model in models:
            p['model'].write(model.T.astype('f4').tobytes())
            for vao,_,mat in self.objects:
                p['base'].value=mat[0];p['metal']=mat[1];p['gloss']=mat[2];p['texmode']=mat[3];vao.render()
        ctx.copy_framebuffer(self.target,self.fbo)
        return Image.frombytes('RGBA',(self.size,self.size),self.target.read(components=4)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)

def encode(frames,output,name):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    n=len(frames);size=frames[0].width
    webp=output/(name+'.webp');frames[0].save(webp,save_all=True,append_images=frames[1:],duration=[33,33,34]*(n//3),loop=0,quality=90,method=4)
    encoder=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{size}x{size}','-r','30','-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(output/(name+'.mp4'))],stdin=subprocess.PIPE)
    for frame in frames:
        c=Image.new('RGBA',frame.size,(8,8,10,255));c.alpha_composite(frame);encoder.stdin.write(c.convert('RGB').tobytes())
    encoder.stdin.close();assert encoder.wait()==0
    frames[0].save(output/(name+'-preview.png'))
    im=Image.open(webp);assert im.n_frames==180 and im.info['loop']==0
    duration=0;different=set()
    for i in range(180):
        im.seek(i);im.load();duration+=im.info['duration']
        if i%45==0:different.add(im.tobytes())
    assert duration==6000 and len(different)==4 and frames[0].getpixel((0,0))[3]==0
    print(json.dumps({'asset':name,'frames':180,'duration_ms':duration,'transparent':True,'quarter_turns':4,'bytes':webp.stat().st_size}),flush=True)
