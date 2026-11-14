p="/home/user/xnu-j1/xnu/osfmk/arm/locore.s"; L=open(p).read().split("\n")
# find the macro block: from first '#if defined(BOARD_CONFIG_MSM8930_SERRANO)' (line 52) to its '#endif' (line 75)
start=next(i for i,l in enumerate(L) if l.startswith("#if defined(BOARD_CONFIG_MSM8930_SERRANO)"))
end=next(i for i in range(start,len(L)) if L[i]=="#endif" and any(".macro MSM_MARK n" in x for x in L[start:i]))
body='''#if defined(BOARD_CONFIG_MSM8930_SERRANO)
/* White bar idx (10x16 px) at y=500 in a scanout alias; clobbers r1-r3. base = VA/PA of the scanout. */
.macro MSM_MARKB idx, base
    LoadConstantToReg(((\base) + 500*1620 + (\idx)*48), r2)
    mvn     r3, #0
    mov     r1, #16
.Lmsmmarkb\@:
    str     r3, [r2]
    str     r3, [r2, #4]
    str     r3, [r2, #8]
    str     r3, [r2, #12]
    str     r3, [r2, #16]
    str     r3, [r2, #20]
    str     r3, [r2, #24]
    str     r3, [r2, #28]
    add     r2, r2, #0x600
    add     r2, r2, #0x54
    subs    r1, r1, #1
    bne     .Lmsmmarkb\@
.endm
.macro MSM_MARK idx
    MSM_MARKB \idx, 0x88100000
.endm
#else
.macro MSM_MARKB idx, base
.endm
.macro MSM_MARK idx
.endm
#endif'''.split("\n")
L[start:end+1]=body
open(p,"w").write("\n".join(L)); print("ok",start,end)
