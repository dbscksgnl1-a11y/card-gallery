/* The glass housing stays fixed; only the contained balls are simulated. */
(()=>{
  const canvas=document.querySelector('.lotto-canvas');
  const fallback=document.querySelector('.lotto-poster');
  if(!canvas||!fallback)return;
  const ctx=canvas.getContext('2d');
  if(!ctx)return;
  const motion=matchMedia('(prefers-reduced-motion: reduce)');
  const plate=new Image();
  const W=1254,H=1254;
  canvas.width=W;canvas.height=H;
  const chamber={x:625,y:520,rx:360,ry:365};
  // Soft, rounded product-illustration colors with a broad studio highlight.
  const colors=[['#fff2a1','#ffd34d','#efb632'],['#ffb5bf','#ff7186','#e8526a'],['#a5edcd','#52d5a0','#2cb584'],['#9eceff','#4799fa','#2675db'],['#d5c2ff','#a083f1','#7e62d2'],['#ffdbad','#ffad65','#ed8b49'],['#f8c9ed','#ed98ce','#d676ba'],['#ffffff','#eef2fa','#ccd7e8']];
  const sprites=colors.map(([light,base,shade])=>{
    const s=document.createElement('canvas');s.width=s.height=144;
    const c=s.getContext('2d');
    const g=c.createRadialGradient(43,31,1,74,79,83);
    g.addColorStop(0,light);g.addColorStop(.46,base);g.addColorStop(1,shade);
    c.fillStyle=g;c.beginPath();c.arc(72,72,69,0,Math.PI*2);c.fill();
    const glint=c.createRadialGradient(48,38,1,48,38,39);
    glint.addColorStop(0,'#ffffff68');glint.addColorStop(1,'#ffffff00');
    c.fillStyle=glint;c.beginPath();c.arc(72,72,69,0,Math.PI*2);c.fill();
    return s;
  });
  // Random initial conditions; every later velocity change is an elastic collision.
  let seed=(Math.random()*4294967296)>>>0;
  const random=()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;};
  const balls=[];
  for(let i=0;i<12;i++){
    const r=53;
    let x,y;
    do{
      x=chamber.x+(random()*2-1)*(chamber.rx-r-2);
      y=chamber.y+(random()*2-1)*(chamber.ry-r-2);
    }while(Math.hypot((x-chamber.x)/(chamber.rx-r-2),(y-chamber.y)/(chamber.ry-r-2))>1||
      balls.some(b=>Math.hypot(x-b.x,y-b.y)<r+b.r+5));
    const angle=random()*Math.PI*2,speed=650+random()*250;
    balls.push({x,y,r,vx:Math.cos(angle)*speed,vy:Math.sin(angle)*speed,color:i%colors.length});
  }
  // Start without collective translation or rotation; individual directions remain random.
  const center=balls.reduce((c,b)=>({x:c.x+b.x/12,y:c.y+b.y/12,vx:c.vx+b.vx/12,vy:c.vy+b.vy/12}),{x:0,y:0,vx:0,vy:0});
  balls.forEach(b=>{b.vx-=center.vx;b.vy-=center.vy;});
  let angular=0,inertia=0;
  balls.forEach(b=>{const x=b.x-center.x,y=b.y-center.y;angular+=x*b.vy-y*b.vx;inertia+=x*x+y*y;});
  const omega=angular/inertia;
  balls.forEach(b=>{b.vx+=omega*(b.y-center.y);b.vy-=omega*(b.x-center.x);});
  const rms=Math.sqrt(balls.reduce((sum,b)=>sum+b.vx*b.vx+b.vy*b.vy,0)/balls.length);
  balls.forEach(b=>{b.vx*=760/rms;b.vy*=760/rms;});
  const initial=balls.map(b=>({...b}));
  let ready=false,last=0,lastDraw=0,accumulator=0;
  function contain(b){
    const rx=chamber.rx-b.r,ry=chamber.ry-b.r;
    const dx=b.x-chamber.x,dy=b.y-chamber.y;
    const q=Math.hypot(dx/rx,dy/ry);
    if(q<=1)return;
    b.x=chamber.x+dx/q;b.y=chamber.y+dy/q;
    let nx=(b.x-chamber.x)/(rx*rx),ny=(b.y-chamber.y)/(ry*ry);
    const length=Math.hypot(nx,ny);nx/=length;ny/=length;
    const vn=b.vx*nx+b.vy*ny;
    // Restitution = 1: reflect only the normal component, preserving speed.
    if(vn>0){b.vx-=2*vn*nx;b.vy-=2*vn*ny;}
  }
  function step(dt){
    // No gravity, air jets, drag, speed clamping, or preferred flow direction.
    balls.forEach(b=>{b.x+=b.vx*dt;b.y+=b.vy*dt;contain(b);});
    for(let pass=0;pass<3;pass++){
      for(let i=0;i<balls.length;i++)for(let j=i+1;j<balls.length;j++){
        const a=balls[i],b=balls[j],dx=b.x-a.x,dy=b.y-a.y;
        const distance=Math.hypot(dx,dy)||.001,min=a.r+b.r;
        if(distance>=min)continue;
        const nx=dx/distance,ny=dy/distance,overlap=(min-distance)/2;
        a.x-=nx*overlap;a.y-=ny*overlap;b.x+=nx*overlap;b.y+=ny*overlap;
        const relative=(b.vx-a.vx)*nx+(b.vy-a.vy)*ny;
        // Equal masses, restitution = 1: exchange normal velocity components.
        if(relative<0){const impulse=-relative;a.vx-=impulse*nx;a.vy-=impulse*ny;b.vx+=impulse*nx;b.vy+=impulse*ny;}
      }
      balls.forEach(contain);
    }
  }
  function draw(){
    ctx.fillStyle='#08080a';ctx.fillRect(0,0,W,H);ctx.globalCompositeOperation='lighten';ctx.drawImage(fallback,0,0,W,H);ctx.globalCompositeOperation='source-over';
    ctx.save();ctx.beginPath();ctx.ellipse(625,520,371,374,0,0,Math.PI*2);ctx.clip();
    ctx.drawImage(plate,0,0,W,H);ctx.restore();
    ctx.save();ctx.beginPath();ctx.ellipse(chamber.x,chamber.y,chamber.rx+4,chamber.ry+4,0,0,Math.PI*2);ctx.clip();
    balls.forEach(b=>ctx.drawImage(sprites[b.color],b.x-b.r,b.y-b.r,b.r*2,b.r*2));
    // Soft glass sheen keeps moving balls visually behind the chamber face.
    const sheen=ctx.createLinearGradient(300,250,930,820);
    sheen.addColorStop(0,'#eaf1ff13');sheen.addColorStop(.65,'#eaf1ff00');sheen.addColorStop(1,'#b5c9ff12');
    ctx.fillStyle=sheen;ctx.fillRect(250,150,760,750);ctx.restore();
  }
  window.drawLottoArtwork=(now,visible)=>{
    if(!ready||!visible||document.hidden){last=0;return;}
    if(motion.matches){last=0;return;}
    const dt=last?Math.min((now-last)/1000,.05):0;last=now;
    accumulator+=dt;
    while(accumulator>=1/240){step(1/240);accumulator-=1/240;}
    if(now-lastDraw>=1000/60){draw();lastDraw=now;}
  };
  const reveal=()=>{if(!plate.complete||!plate.naturalWidth||!fallback.complete||!fallback.naturalWidth)return;ready=true;draw();canvas.hidden=false;fallback.hidden=true;};
  plate.onload=reveal;fallback.addEventListener('load',reveal,{once:true});
  plate.src='assets/lotto-machine-empty-v1.webp';
  motion.addEventListener('change',()=>{
    if(motion.matches)balls.forEach((b,i)=>Object.assign(b,initial[i]));
    last=0;accumulator=0;if(ready)draw();
  });
})();
