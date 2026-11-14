"""Rebuild J1SHOT frame dumps from a last_kmsg capture into PNGs.
usage: python shot2png.py lastk.txt [outprefix]"""
import sys, re
from PIL import Image
src = open(sys.argv[1], 'rb').read().decode('latin1')
pre = sys.argv[2] if len(sys.argv) > 2 else 'shot'
for m in re.finditer(r'J1SHOT (\d+) 135x240\n(.*?)J1SHOT end', src, re.S):
    n = m.group(1)
    im = Image.new('RGB', (135, 240))
    for line in m.group(2).splitlines():
        mm = re.match(r'S(\d{3}) ([0-9a-f]+)', line)
        if not mm: continue
        y = int(mm.group(1)); h = mm.group(2)
        for x in range(min(135, len(h) // 3)):
            r, g, b = (int(h[x * 3 + k], 16) * 17 for k in range(3))
            im.putpixel((x, y), (r, g, b))
    out = '%s_frame%s.png' % (pre, n)
    im.resize((540, 960), Image.NEAREST).save(out)
    print('wrote', out)
