@ S4 GT-I9500 stage-1 test B: prove the hardware watchdog brings a hung build back to TWRP.
@ INFORM2/INFORM3 = recovery (as test A), unmask PMU WDT reset, arm WDT (max timeout), then spin.
@ Fallback: if the WDT never fires, a long busy loop (~45-170 s) ends in SWRESET, so the phone never stays hung.
@ WDT 0x101D0000: WTCON 0x0, WTDAT 0x4, WTCNT 0x8. WTCON = prescale 0xFF | enable | div128 | reset enable.
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
	ldr r1, =0x12345674		@ recovery
	str r1, [r0]
	ldr r0, =0x10040408		@ AUTOMATIC_WDT_RESET_DISABLE: clear SYS_WDTRESET
	ldr r1, [r0]
	bic r1, r1, #1
	str r1, [r0]
	ldr r0, =0x1004040C		@ MASK_WDT_RESET_REQUEST: clear SYS_WDTRESET
	ldr r1, [r0]
	bic r1, r1, #1
	str r1, [r0]
	ldr r0, =0x101D0000		@ WDT
	mov r1, #0
	str r1, [r0]			@ WTCON off while loading
	ldr r1, =0xFFFF
	str r1, [r0, #4]		@ WTDAT
	str r1, [r0, #8]		@ WTCNT
	ldr r1, =0xFF39
	str r1, [r0]			@ WTCON: prescale 255, enable, div128, reset
	dsb
	mov r2, #16			@ fallback: 16 x 2^32 iterations
2:	mvn r3, #0
3:	subs r3, r3, #1
	bne 3b
	subs r2, r2, #1
	bne 2b
	ldr r0, =0x10040400		@ SWRESET fallback
	mov r1, #1
	str r1, [r0]
	dsb
4:	wfi
	b 4b
	.ltorg
