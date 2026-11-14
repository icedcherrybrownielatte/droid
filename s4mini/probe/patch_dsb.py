p="/home/user/xnu-j1/xnu/osfmk/arm/locore.s"; s=open(p).read()
old="    MSM_MARK 1\n    /* Start MMU. */\n    mrc     p15, 0, r3, c1, c0, 0\n    orr     r3, r3, #1\n    mcr     p15, 0, r3, c1, c0, 0\n"
assert old in s
new="    MSM_MARK 1\n    /* Page-table stores must be visible to the walker before the MMU turns on (Krait buffers writes). */\n    dsb     sy\n    isb     sy\n    /* Start MMU. */\n    mrc     p15, 0, r3, c1, c0, 0\n    orr     r3, r3, #1\n    mcr     p15, 0, r3, c1, c0, 0\n    isb     sy\n"
s=s.replace(old,new,1)
open(p,"w").write(s); print("ok")
