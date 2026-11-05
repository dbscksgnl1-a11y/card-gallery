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
  let seed=2319;
  const random=()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;};
  const balls=[];
  // Five staggered rows leave visible space above the resting balls.
  [4,5,6,5,3].forEach((count,row)=>{
    for(let col=0;col<count;col++)balls.push({
      x:625+(col-(count-1)/2)*103,y:430+row*88,r:51+random()*5,
      vx:0,vy:0,cooldown:0,color:balls.length%colors.length
    });
  });
  let initial;
  let ready=false,last=0,lastDraw=0,time=0,accumulator=0,jetClock=0;
  function contain(b){
    const rx=chamber.rx-b.r,ry=chamber.ry-b.r;
    const dx=b.x-chamber.x,dy=b.y-chamber.y;
    const q=Math.hypot(dx/rx,dy/ry);
    if(q<=1)return;
    b.x=chamber.x+dx/q;b.y=chamber.y+dy/q;
    let nx=(b.x-chamber.x)/(rx*rx),ny=(b.y-chamber.y)/(ry*ry);
    const length=Math.hypot(nx,ny);nx/=length;ny/=length;
    const vn=b.vx*nx+b.vy*ny;
    if(vn>0){b.vx-=1.5*vn*nx;b.vy-=1.5*vn*ny;}
  }
  function step(dt,air=true){
    time+=dt;
    // Brief bottom jets launch individual balls. Gravity acts everywhere,
    // so no force can hold a ball suspended halfway up the chamber.
    jetClock-=dt;
    if(air&&jetClock<=0){
      const phase=time%3.6;
      jetClock=.075+random()*.065;
      if(phase<2.85){
        const candidates=balls.filter(b=>b.y>650&&b.cooldown<=0).sort((a,b)=>b.y-a.y);
        for(let k=0;k<Math.min(2,candidates.length);k++){
          const b=candidates.splice(Math.floor(random()*Math.min(5,candidates.length)),1)[0];
          b.vy=-(1500+random()*650);
          b.vx=(625-b.x)*1.05+(random()-.5)*690;
          b.cooldown=.34;
        }
      }
    }
    balls.forEach(b=>{
      b.cooldown-=dt;
      b.vy+=2450*dt;
      const drag=Math.exp(-.085*dt);b.vx*=drag;b.vy*=drag;
      b.x+=b.vx*dt;b.y+=b.vy*dt;
      contain(b);
    });
    for(let pass=0;pass<2;pass++){
      for(let i=0;i<balls.length;i++)for(let j=i+1;j<balls.length;j++){
        const a=balls[i],b=balls[j],dx=b.x-a.x,dy=b.y-a.y;
        const distance=Math.hypot(dx,dy)||.001,min=a.r+b.r;
        if(distance>=min)continue;
        const nx=dx/distance,ny=dy/distance,overlap=(min-distance)/2;
        a.x-=nx*overlap;a.y-=ny*overlap;b.x+=nx*overlap;b.y+=ny*overlap;
        const relative=(b.vx-a.vx)*nx+(b.vy-a.vy)*ny;
        if(relative<0){const impulse=-relative*.86;a.vx-=impulse*nx;a.vy-=impulse*ny;b.vx+=impulse*nx;b.vy+=impulse*ny;}
      }
      balls.forEach(contain);
    }
  }
  // Settle the initial pose before showing it, including reduced-motion mode.
  for(let i=0;i<180;i++)step(1/120,false);
  initial=balls.map(b=>({...b}));time=0;jetClock=0;
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
    while(accumulator>=1/120){step(1/120);accumulator-=1/120;}
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
