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
  const colors=[['#fff47d','#ffe02c','#ffc20b'],['#ff91a4','#ff4e6c','#e52e50'],['#82e87e','#29ca3b','#02a627'],['#69c9ff','#058cff','#0063e0'],['#bd8aff','#843af1','#5925c3'],['#ffc76b','#ff9c20','#f27809'],['#ffb5ed','#ff7cda','#e750b7'],['#ffffff','#f2f2fa','#d0d2e5']];
  const sprites=colors.map(([light,base,shade])=>{
    const s=document.createElement('canvas');s.width=s.height=144;
    const c=s.getContext('2d');
    const g=c.createRadialGradient(45,35,5,72,74,70);
    g.addColorStop(0,light);g.addColorStop(.48,base);g.addColorStop(1,shade);
    c.fillStyle=g;c.beginPath();c.arc(72,72,69,0,Math.PI*2);c.fill();
    c.fillStyle='#ffffff80';c.beginPath();c.ellipse(49,39,21,11,-.72,0,Math.PI*2);c.fill();
    return s;
  });
  let seed=2319;
  const random=()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;};
  const balls=[];
  // Five staggered rows leave visible space above the resting balls.
  [4,5,6,5,3].forEach((count,row)=>{
    for(let col=0;col<count;col++)balls.push({
      x:625+(col-(count-1)/2)*103,y:430+row*88,r:51+random()*5,
      vx:(random()-.5)*140,vy:-random()*130,color:balls.length%colors.length
    });
  });
  const initial=balls.map(b=>({...b}));
  let ready=false,last=0,lastDraw=0,time=0,accumulator=0;
  function contain(b){
    const rx=chamber.rx-b.r,ry=chamber.ry-b.r;
    const dx=b.x-chamber.x,dy=b.y-chamber.y;
    const q=Math.hypot(dx/rx,dy/ry);
    if(q<=1)return;
    b.x=chamber.x+dx/q;b.y=chamber.y+dy/q;
    let nx=(b.x-chamber.x)/(rx*rx),ny=(b.y-chamber.y)/(ry*ry);
    const length=Math.hypot(nx,ny);nx/=length;ny/=length;
    const vn=b.vx*nx+b.vy*ny;
    if(vn>0){b.vx-=1.7*vn*nx;b.vy-=1.7*vn*ny;}
  }
  function step(dt){
    time+=dt;
    balls.forEach((b,i)=>{
      // A broad intermittent air jet lifts the pile, with gentle circulating flow.
      const jet=.62+.38*Math.sin(time*1.45);
      const bottom=Math.max(0,Math.min(1,(b.y-390)/350));
      const center=Math.max(.15,1-Math.abs(b.x-625)/370);
      b.vx+=(-.55*(b.y-520)+95*Math.sin(time*1.2+i*.8))*dt;
      b.vy+=(290-1250*bottom*center*jet+.45*(b.x-625))*dt;
      const drag=Math.exp(-.2*dt);b.vx*=drag;b.vy*=drag;
      const speed=Math.hypot(b.vx,b.vy);if(speed>470){b.vx*=470/speed;b.vy*=470/speed;}
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
        if(relative<0){const impulse=-relative*.88;a.vx-=impulse*nx;a.vy-=impulse*ny;b.vx+=impulse*nx;b.vy+=impulse*ny;}
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
    while(accumulator>=1/60){step(1/60);accumulator-=1/60;}
    if(now-lastDraw>=1000/30){draw();lastDraw=now;}
  };
  const reveal=()=>{if(!plate.complete||!plate.naturalWidth||!fallback.complete||!fallback.naturalWidth)return;ready=true;draw();canvas.hidden=false;fallback.hidden=true;};
  plate.onload=reveal;fallback.addEventListener('load',reveal,{once:true});
  plate.src='assets/lotto-machine-empty-v1.webp';
  motion.addEventListener('change',()=>{
    if(motion.matches)balls.forEach((b,i)=>Object.assign(b,initial[i]));
    last=0;accumulator=0;if(ready)draw();
  });
})();
