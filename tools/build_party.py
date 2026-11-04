"""Build a self-contained, looping SVG from the clean emoji face layer."""
from pathlib import Path
import base64
import math
import random

ROOT = Path(__file__).resolve().parents[1]
FACE = base64.b64encode((ROOT / 'tools/textures/party-face.webp').read_bytes()).decode()
DURATION = 4.2
TIMES = [0, .12, .22, .31, .42, .49, .60, .69, .78, 1]
EXTENSION = [0, 0, .16, .90, 1, .98, .12, 0, .035, 0]
KEYS = ';'.join(map(str, TIMES))

def blower(extension):
    # Fixed paper length: the straight section grows as its spiral tip unwinds.
    length, segments = 390, 100
    straight = 80 + 310 * extension
    x, y = 493., 585.
    theta = 0.
    points = [(x, y)]
    for i in range(segments):
        s = (i + .5) * length / segments
        if s > straight:
            theta -= length / segments / max(26, 52 - .085 * (s - straight))
        x += math.cos(theta) * length / segments
        y += math.sin(theta) * length / segments
        points.append((x, y))
    return 'M' + ' L'.join(f'{x:.2f},{y:.2f}' for x, y in points)

paths = [blower(e) for e in EXTENSION]
spline = ';'.join(['.42 0 .22 1'] * (len(TIMES) - 1))
common = f'keyTimes="{KEYS}" dur="{DURATION}s" repeatCount="indefinite" calcMode="spline" keySplines="{spline}"'

def confetti(count, seed):
    rng = random.Random(seed)
    output = []
    colors = ['#f75474', '#a848dc', '#78a1ff', '#ffdff9', '#fff8d8', '#007bff']
    for i in range(count):
        # Keep the face legible; most foreground pieces drift along its edges.
        x = rng.uniform(70, 900) if seed == 18 else rng.choice([rng.uniform(60, 240), rng.uniform(750, 900)])
        drift = rng.uniform(-65, 65)
        dur = rng.uniform(3.8, 6.5)
        begin = -rng.uniform(0, dur)
        size = rng.uniform(16, 29)
        angle = rng.uniform(-150, 150)
        fill = colors[i % len(colors)]
        shape = f'<rect x="{-size/2:.2f}" y="{-size/2:.2f}" width="{size:.2f}" height="{size*.8:.2f}" rx="4" fill="{fill}"/>'
        if i % 4 == 0:
            shape = f'<circle r="{size/2:.2f}" fill="{fill}"/>'
        output.append(f'''<g opacity="0"><animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.08;.86;1" dur="{dur:.2f}s" begin="{begin:.2f}s" repeatCount="indefinite"/>
<animateTransform attributeName="transform" type="translate" values="{x:.2f} -25;{x+drift:.2f} 440;{x-drift*.5:.2f} 960" keyTimes="0;.5;1" dur="{dur:.2f}s" begin="{begin:.2f}s" repeatCount="indefinite"/>
<g><animateTransform attributeName="transform" type="rotate" values="{angle:.2f};{angle+220:.2f};{angle+470:.2f}" dur="{dur:.2f}s" begin="{begin:.2f}s" repeatCount="indefinite"/>
<g><animateTransform attributeName="transform" type="scale" values="1 1;.25 1;1 1;.4 1;1 1" dur="{dur*.48:.2f}s" begin="{begin:.2f}s" repeatCount="indefinite"/>{shape}</g></g></g>''')
    return ''.join(output)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="960" height="960" viewBox="0 0 960 960" role="img" aria-labelledby="party-title">
<title id="party-title">파티 블로어를 불고 컨페티가 흩날리는 축하 이모지</title>
<desc>얼굴이 숨을 불면 블로어가 길게 펼쳐지고 다시 말립니다. 색종이는 회전하며 떨어집니다.</desc>
{confetti(15, 18)}
<g transform="translate(450 500)"><g>
<animateTransform attributeName="transform" type="rotate" values="0;0;-2;-3;-2;0;1;0;0;0" {common}/>
<g><animateTransform attributeName="transform" type="scale" values="1 1;1 1;1.025 .985;1.035 .975;1.025 .99;1.01 1;1 1;1 1;1 1;1 1" {common}/>
<g transform="translate(-450 -500)">
<image x="25" y="5" width="900" height="900" xlink:href="data:image/webp;base64,{FACE}"/>
<path d="{paths[0]}" fill="none" stroke="#087fff" stroke-width="26" stroke-linecap="round" stroke-linejoin="round">
<animate attributeName="d" values="{';'.join(paths)}" {common}/></path>
<path d="M489 585 H520" fill="none" stroke="#168bff" stroke-width="29" stroke-linecap="round"/>
</g></g></g></g>
{confetti(9, 27)}
</svg>'''
(ROOT / 'assets/card2-party-animated-v1.svg').write_text(svg)
print(f'Wrote animated emoji: {len(svg.encode()):,} bytes, {DURATION}s blower loop, 24 confetti pieces')