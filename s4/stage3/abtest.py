"""A/B: user/pmap pages WT (A15: non-cacheable) vs WB. Usage: abtest.py wt|wb (edits ~/xnu-s4 pmap.c line 1204 only)."""
import os, sys
p = os.path.expanduser('~/xnu-s4/xnu/osfmk/arm/pmap.c')
s = open(p, newline='').read()
WB = '#define J5410_NORMAL_MEM ((ARM_CACHEBIT_WB_WA_BUFFERED << 2) | (ARM_L2_4KB_TEX(ARM_L2_TEX_100 | ARM_CACHEBIT_WB_WA_BUFFERED)))\n#else'
WT = '#define J5410_NORMAL_MEM ((ARM_CACHEBIT_WT_NWA_BUFFERED << 2) | (ARM_L2_4KB_TEX(ARM_L2_TEX_100 | ARM_CACHEBIT_WT_NWA_BUFFERED)))\n#else'
if sys.argv[1] == 'wt':
    assert s.count(WB) == 1; s = s.replace(WB, WT)
else:
    assert s.count(WT) == 1; s = s.replace(WT, WB, 1)
open(p, 'w', newline='').write(s); print('pmap normal mem ->', sys.argv[1])
