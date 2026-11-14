import os
p = os.path.expanduser("~/xnu-j1/xnu/pexpert/arm/msm8930_timer.c")
s = open(p).read()

old_arm = """	wr(m_tmr, DGT_MATCH_VAL, rd(m_tmr, DGT_COUNT_VAL) + ticks);
	wr(m_gic_dist, GIC_DIST_PENDING_CLEAR + (irq / 32) * 4, 1U << (irq % 32));
	wr(m_gic_dist, GIC_DIST_ENABLE_SET + (irq / 32) * 4, 1U << (irq % 32));
	drain();
	armed = 1;
"""
new_arm = """	/* The DGT match IRQ is an edge pulse. Clear any stale pending state BEFORE programming the
	 * match (clearing afterwards can wipe the new pulse when the deadline is only microseconds
	 * away, and the timer then stays silent until the 32-bit counter wraps ~10 min later).
	 * If the deadline has already passed once the match is written, force the PPI pending. */
	wr(m_gic_dist, GIC_DIST_PENDING_CLEAR + (irq / 32) * 4, 1U << (irq % 32));
	drain();
	{
		uint32_t start = rd(m_tmr, DGT_COUNT_VAL), target = start + ticks;
		wr(m_tmr, DGT_MATCH_VAL, target);
		wr(m_gic_dist, GIC_DIST_ENABLE_SET + (irq / 32) * 4, 1U << (irq % 32));
		drain();
		if ((uint32_t)(rd(m_tmr, DGT_COUNT_VAL) - start) >= ticks)
			wr(m_gic_dist, 0x200U + (irq / 32) * 4, 1U << (irq % 32));	/* GICD_ISPENDR */
	}
	drain();
	armed = 1;
	arm_gen++;
"""
assert old_arm in s
s = s.replace(old_arm, new_arm, 1)

old_decl = "static uint32_t controller_ready, timebase_ready, armed;"
assert old_decl in s
s = s.replace(old_decl, old_decl + "\nstatic uint32_t arm_gen;", 1)

old_h = """		rtclock_intr((arm_saved_state_t *)context);
		ios7m8930_fb_flush();
		ios7m8930_hex10(m_irqs);
		if (m_irqs < 20000U) *(volatile uint32_t *)0x0208A038u = 1;	/* pet uniLoader WDT for ~30 s of ticks, then let it bite -> TWRP */
#if !CONFIG_TICKLESS
		M8930_timer_enabled(TRUE);
#endif
"""
new_h = """		{
			uint32_t gen = arm_gen;
			rtclock_intr((arm_saved_state_t *)context);
			/* Heartbeat: if the clock layer armed nothing, tick again in 10 ms so a missed
			 * deadline can never leave the CPU parked in WFI forever. */
			if (arm_gen == gen) { clock_decrementer = M8930_DGT_HZ / 100U; M8930_timer_enabled(TRUE); }
		}
		ios7m8930_fb_flush();
		ios7m8930_hex10(m_irqs);
		/* DEBUG: pet uniLoader's watchdog for the first 100 s of uptime, then let it bite -> TWRP */
		if (dgt_get_count() < 100ULL * M8930_DGT_HZ) *(volatile uint32_t *)0x0208A038u = 1;
"""
assert old_h in s
s = s.replace(old_h, new_h, 1)
open(p, "w").write(s)
print("timer patched")
