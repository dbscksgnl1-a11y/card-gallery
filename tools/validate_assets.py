"""Reject missing image paths and broken or static product loops before publishing."""
import hashlib
import sys
from html.parser import HTMLParser
from pathlib import Path
import xml.etree.ElementTree as ET
from PIL import Image

root = Path(sys.argv[1] if len(sys.argv) > 1 else '.')

class Artwork(HTMLParser):
    paths = set()
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('src', 'srcset', 'data-poster', 'data-video') and value:
                if value.startswith('assets/'):
                    self.paths.add(value.split('?')[0])

page = Artwork()
page.feed((root / 'index.html').read_text())
for path in sorted(page.paths):
    asset = root / path
    assert asset.is_file() and asset.stat().st_size > 0, f'Missing artwork: {path}'
    if asset.suffix == '.svg':
        ET.parse(asset)
    elif asset.suffix in ('.webp', '.png'):
        with Image.open(asset) as im:
            im.load()

for name in ('card6-watch-3d-v3', 'card7-airpods-3d-v3'):
    with Image.open(root / 'assets' / (name + '.webp')) as im:
        assert im.size == (800, 800) and im.n_frames == 180
        assert im.info.get('loop') == 0
        duration, turns = 0, set()
        for i in range(im.n_frames):
            im.seek(i)
            im.load()
            duration += im.info['duration']
            assert im.convert('RGBA').getpixel((0, 0))[3] == 0
            if i % 45 == 0:
                turns.add(hashlib.sha256(im.tobytes()).hexdigest())
        assert duration == 6000 and len(turns) == 4
    print(f'{name}: 180 frames, 6 seconds, transparent, 4 distinct quarter turns')

svg = ET.parse(root / 'assets/card2-party-animated-v1.svg')
ns = {'svg': 'http://www.w3.org/2000/svg'}
assert svg.findall('.//svg:animate[@attributeName="d"]', ns), 'Missing blower motion'
assert len(svg.findall('.//svg:animateTransform[@type="translate"]', ns)) >= 24
print(f'OK: {len(page.paths)} artwork paths, product loops and party animation')
