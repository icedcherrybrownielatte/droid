X="/home/user/xnu-j1/xnu/"
p=X+"osfmk/arm/locore.s"; s=open(p).read()
assert "add     r5, r4, #0x3000" in s
s=s.replace("add     r5, r4, #0x3000","add     r5, r4, #0xC00",1)
s=s.replace("MSM_MARKB 4, 0xC0000000","MSM_MARKB 4, 0x30000000")
s=s.replace("VA 0xC0000000/0xC0100000","VA 0x30000000/0x30100000")
open(p,"w").write(s)
p=X+"osfmk/arm/arm_vm_init.c"; s=open(p).read()
assert "l1[0xC00] = 0x88100000u | 0xC02;" in s
s=s.replace("l1[0xC00] = 0x88100000u | 0xC02;","l1[0x300] = 0x88100000u | 0xC02;",1).replace("l1[0xC01] = 0x88200000u | 0xC02;","l1[0x301] = 0x88200000u | 0xC02;",1)
open(p,"w").write(s)
p=X+"pexpert/arm/pe_msm8930_serrano.c"; s=open(p).read()
n=s.count("0xC0000000u")
s=s.replace("0xC0000000u","0x30000000u")
open(p,"w").write(s); print("ok",n)
