import os
p = os.path.expanduser("~/xnu-j1/xnu/osfmk/arm/trap.c")
s = open(p).read()
NL = chr(92) + "n"
a = "    debug_mode = TRUE;\n"
assert s.count(a) >= 1
assert "fatal_once" not in s
b = """#if defined(BOARD_CONFIG_MSM8930_SERRANO)
    {   /* DEBUG: show the first fatal exception once, then hold (pet WDT ~60 s) instead of
         * recursing through Debugger(), which itself traps on this port and scribbles the screen. */
        extern void ios7m8930_hexN(unsigned int, unsigned int);
        extern void ios7m8930_fb_flush_all(void);
        static int fatal_once;
        volatile unsigned long long spin;
        if (fatal_once++ == 0 && arm_ctx) {
            ios7m8930_hexN(15, arm_ctx->pc); ios7m8930_hexN(16, arm_ctx->lr);
            ios7m8930_hexN(20, arm_ctx->far); ios7m8930_hexN(21, arm_ctx->fsr);
            ios7m8930_hexN(22, arm_ctx->cpsr); ios7m8930_hexN(23, ((unsigned int)__builtin_return_address(0)) & ~1U);
            printf("FATAL %s pc=%08x lr=%08x far=%08x fsr=%08x cpsr=%08x sp=%08x thr=%p@NL@", message,
                   arm_ctx->pc, arm_ctx->lr, arm_ctx->far, arm_ctx->fsr, arm_ctx->cpsr, arm_ctx->sp, current_thread());
            printf("  r0=%08x r1=%08x r2=%08x r3=%08x r4=%08x r5=%08x r6=%08x r7=%08x@NL@",
                   arm_ctx->r[0], arm_ctx->r[1], arm_ctx->r[2], arm_ctx->r[3], arm_ctx->r[4], arm_ctx->r[5], arm_ctx->r[6], arm_ctx->r[7]);
            ios7m8930_fb_flush_all();
        }
        for (spin = 0; spin < 8000000000ULL; spin++) *(volatile unsigned int *)0x0208A038u = 1;
        for (;;) ;
    }
#endif
""".replace("@NL@", NL)
i = s.index("void sleh_fatal_exception(")
j = s.index(a, i)
s = s[:j] + b + s[j:]
open(p, "w").write(s)
print("ok")
