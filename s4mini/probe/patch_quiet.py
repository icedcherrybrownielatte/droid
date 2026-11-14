import os
root = os.path.expanduser("~/xnu-j1/xnu/")
p = root + "osfmk/arm/trap.c"
s = open(p).read()
for a, b in [("if (j1_uda_pg_once((unsigned)dfar >> 12))", "if (0 && j1_uda_pg_once((unsigned)dfar >> 12))"),
             ("if ((uda_total & 511U) == 0)", "if ((uda_total & 16383U) == 0)"),
             ("if (j1sr_abu < 30) { j1sr_abu++;", "if (j1sr_abu < 0U) { j1sr_abu++;")]:
    assert a in s, a
    s = s.replace(a, b, 1)
open(p, "w").write(s)
p = root + "pexpert/arm/msm8930_timer.c"
s = open(p).read()
a = "dgt_get_count() < 100ULL * M8930_DGT_HZ"
assert a in s
s = s.replace(a, "dgt_get_count() < 400ULL * M8930_DGT_HZ", 1)
open(p, "w").write(s)
print("ok")
