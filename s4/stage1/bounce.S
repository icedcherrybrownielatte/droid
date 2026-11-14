@ S4 GT-I9500 stage-1 test A: reboot straight into recovery (TWRP).
@ Samsung sec-reboot.c: INFORM2=0x12345678 (no LPM), INFORM3=0x12345670|4 (recovery), then PMU SWRESET=1.
@ PMU base 0x10040000 (EXYNOS5_PA_PMU). Position independent, no RAM use.
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
	ldr r0, =0x1004080C		@ INFORM3
	ldr r1, =0x12345674		@ REBOOT_MODE_PREFIX | REBOOT_MODE_RECOVERY
	str r1, [r0]
	dsb
	ldr r0, =0x10040400		@ SWRESET
	mov r1, #1
	str r1, [r0]
	dsb
2:	wfi
	b 2b
	.ltorg
