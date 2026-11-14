.global _s
_s: @ r2=atags: print cmdline tag via pl011 @0x09000000
 ldr r4,=0x09000000
 ldr r3,[r2,#4]
1: cmp r3,#0
 beq done
 ldr r5,=0x54410009
 cmp r3,r5
 bne next
 add r6,r2,#8
2: ldrb r7,[r6],#1
 cmp r7,#0
 beq done
 str r7,[r4]
 b 2b
next: ldr r5,[r2]
 add r2,r2,r5,lsl #2
 ldr r3,[r2,#4]
 b 1b
done: mov r7,#10
 str r7,[r4]
 b .
