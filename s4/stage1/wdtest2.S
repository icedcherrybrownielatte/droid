@ S4 GT-I9500 stage-1 test C (UNTESTED - run only with the user watching): watchdog safety net.
@ Test B showed: after a watchdog reset S-Boot ignores INFORM3=recovery and boots BOOT again -> endless logo loop.
@ Fix: on entry, if PMU RST_STAT (0x10040404) has SYS_WDTRESET (bit 20) set, or the DRAM marker written before
@ arming is still there, go straight to recovery with SWRESET (the path test A proved).
	.syntax unified
	.arm
	.text
	.globl _start
_start:
	mov r0, r0
	mov r0, r0
	mov r0, r0
	mov r0, r0
	mov r0, r0
	mov r0, r0
	mov r0, r0
	mov r0, r0
	b 1f
	.word 0x016f2818		@ zImage magic at 0x24
	.word 0
	.word 0
1:
	cpsid aif
	ldr r0, =0x10040808		@ INFORM2
	ldr r1, =0x12345678
	str r1, [r0]
	ldr r0, =0x1004080C		@ INFORM3 = recovery
	ldr r1, =0x12345674
	str r1, [r0]
	ldr r0, =0x10040404		@ RST_STAT
	ldr r1, [r0]
	tst r1, #(1 << 20)		@ SYS_WDTRESET
	bne recover
	ldr r4, =0x5FF00000		@ DRAM marker (outside S-Boot's usual load areas)
	ldr r5, =0x57D7E5A1
	ldr r1, [r4]
	cmp r1, r5
	beq recover
	str r5, [r4]			@ set marker, then arm the watchdog
	dsb
	ldr r0, =0x10040408
	ldr r1, [r0]
	bic r1, r1, #1
	str r1, [r0]
	ldr r0, =0x1004040C
	ldr r1, [r0]
	bic r1, r1, #1
	str r1, [r0]
	ldr r0, =0x101D0000
	mov r1, #0
	str r1, [r0]
	ldr r1, =0xFFFF
	str r1, [r0, #4]
	str r1, [r0, #8]
	ldr r1, =0xFF39
	str r1, [r0]
	dsb
2:	b 2b				@ hang: the watchdog must catch this
recover:
	ldr r4, =0x5FF00000
	mov r1, #0
	str r1, [r4]			@ clear marker
	dsb
	ldr r0, =0x10040400		@ SWRESET
	mov r1, #1
	str r1, [r0]
	dsb
3:	wfi
	b 3b
	.ltorg
