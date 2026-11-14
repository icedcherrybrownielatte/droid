/*
 * Galaxy S4 GT-I9500 (Exynos 5410, boot CPU Cortex-A15): GIC + MCT timer for XNU.
 * Same entry points (M8930_*) as the S4 mini's msm8930_timer.c so the shared iOS-port code links unchanged.
 *
 * MCT (0x101C0000, Linux mct.c / regs-mct.h): global free-running counter G_CNT_L/U (0x100/0x104) at
 * 24 MHz is the timebase. Local timer L0 (base +0x300) is the event: TCNTB (+0x00) = 1 (divides by 2,
 * 12 MHz), ICNTB (+0x08) = bit31 | count, TCON (+0x20) bit0 timer start, bit1 int start, bit2 interval,
 * INT_CSTAT (+0x30) write 1 to clear, INT_ENB (+0x34), WSTAT (+0x40) write-status bits, written back to clear.
 * L0 interrupt = SPI 120 = INTID 152 (Linux "mct_tick0"). GIC dist 0x10481000, cpu 0x10482000.
 *
 * Safety: uniLoader armed the SoC watchdog (0x101D0000) before XNU; every timer tick pets it, so a hang
 * with interrupts off ends in a watchdog reset -> uniLoader -> TWRP. After J5410_RUN_SECONDS the kernel
 * reboots to recovery itself (INFORM3 + SWRESET), like the S4 mini's 420 s timed reboot.
 */
#include <mach/mach_types.h>
#include <mach/arm/thread_status.h>
#include <pexpert/pexpert.h>
#include <pexpert/arm/protos.h>
#include <machine/machine_routines.h>
#include <kern/debug.h>
#include "msm8930_timer.h"

#if defined(BOARD_CONFIG_EXYNOS5410_JA3G)

#define J5410_MCT_PA		0x101C0000U
#define J5410_WDT_PA		0x101D0000U
#define J5410_PMU_PA		0x10040000U
#define J5410_GIC_DIST_PA	0x10481000U
#define J5410_GIC_CPU_PA	0x10482000U
#define J5410_MARKER_PA		0x5FF00000U	/* uniLoader's "watchdog armed" DRAM marker */
#define J5410_HZ		24000000U
#define J5410_TICK_HZ		(J5410_HZ / 2U)	/* L0 counts at G/(TCNTB+1) */
#define J5410_IRQ		152U
#define J5410_RUN_SECONDS	420ULL

#define MCT_G_CNT_L		0x100U
#define MCT_G_CNT_U		0x104U
#define MCT_G_CNT_WSTAT		0x110U
#define MCT_G_TCON		0x240U
#define MCT_G_WSTAT		0x24CU
#define MCT_L0			0x300U
#define L_TCNTB			0x00U
#define L_ICNTB			0x08U
#define L_TCON			0x20U
#define L_INT_CSTAT		0x30U
#define L_INT_ENB		0x34U
#define L_WSTAT			0x40U

#define GIC_DIST_CTRL		0x000U
#define GIC_DIST_ENABLE_SET	0x100U
#define GIC_DIST_ENABLE_CLEAR	0x180U
#define GIC_DIST_PENDING_CLEAR	0x280U
#define GIC_DIST_PRI		0x400U
#define GIC_DIST_TARGET		0x800U
#define GIC_DIST_CONFIG		0xc00U
#define GIC_CPU_CTRL		0x00U
#define GIC_CPU_PRIMASK		0x04U
#define GIC_CPU_INTACK		0x0cU
#define GIC_CPU_EOI		0x10U

extern void rtc_configure(uint64_t hz);
extern void rtclock_intr(arm_saved_state_t *regs);
extern void ios7m8930_fb_flush(void);
extern void ios7m8930_mark(unsigned int n);

uint64_t clock_decrementer;
static vm_offset_t m_mct, m_gic_dist, m_gic_cpu, m_wdt, m_pmu, m_marker;
static uint32_t controller_ready, timebase_ready, armed, arm_gen, m_irqs;
static uint64_t m_deadline, m_t0;
static uint32_t m_l0_hz = J5410_TICK_HZ;	/* measured at timebase init */	/* m_t0: counter at timebase init */	/* G counter value the current L0 shot ends at */

static inline uint32_t rd(vm_offset_t b, uint32_t o) { return *(volatile uint32_t *)(b + o); }
static inline void wr(vm_offset_t b, uint32_t o, uint32_t v) { *(volatile uint32_t *)(b + o) = v; }
static inline void drain(void) { __asm__ volatile("dsb sy" ::: "memory"); }

/* MCT register writes complete asynchronously: wait (bounded) for the write-status bit, then clear it. */
/* write-status wait statistics, reported at the timed reboot: [0] calls, [1] timeouts, [2] max loops */
unsigned int j5410_wstat[3];
/* timer stats: [0] arms, [1] arms < 1 ms, [2] min request, [3] handler G ticks total, [4] handler max */
unsigned int j5410_tstat[8] = { 0, 0, ~0U, 0, 0, 0, 0, 0 };	/* [5] late total, [6] late max, [7] early count */
static void mct_write(uint32_t off, uint32_t v, uint32_t stat_off, uint32_t mask)
{
	unsigned int n;
	wr(m_mct, off, v);
	j5410_wstat[0]++;
	for (n = 0; n < 2000U; n++)
		if (rd(m_mct, stat_off) & mask) {
			wr(m_mct, stat_off, mask);
			if (n > j5410_wstat[2]) j5410_wstat[2] = n;
			return;
		}
	j5410_wstat[1]++;
}

static uint64_t mct_count(void)
{
	uint32_t hi, lo, hi2;
	unsigned int n = 0;
	do {
		hi = rd(m_mct, MCT_G_CNT_U);
		lo = rd(m_mct, MCT_G_CNT_L);
		hi2 = rd(m_mct, MCT_G_CNT_U);
	} while (hi != hi2 && ++n < 8U);
	return ((uint64_t)hi2 << 32) | lo;
}

/* Pet only while the kernel is healthy: once a panic starts, the watchdog must be free to bite. */
void ios7m8930_pet_wdt(void)
{
	extern const char *panicstr;
	if (m_wdt && !panicstr) wr(m_wdt, 0x08U, 0xFFFFU);	/* WTCNT reload */
}

/* Reboot into TWRP: Samsung sec-reboot (INFORM2/INFORM3 = recovery), clear uniLoader's marker, SWRESET. */
static void j5410_reboot_now(void)
{
	if (m_marker) {
		*(volatile uint32_t *)m_marker = 0;
		/* the mapping may be cacheable: push the line to DRAM or the reset loses it (and uniLoader then
		 * sees its marker and bounces the next boot straight back to TWRP) */
		__asm__ volatile("dsb sy" ::: "memory");
		__asm__ volatile("mcr p15, 0, %0, c7, c14, 1" :: "r"(m_marker) : "memory");	/* DCCIMVAC */
		__asm__ volatile("dsb sy" ::: "memory");
	}
	if (m_pmu) {
		wr(m_pmu, 0x808U, 0x12345678U);
		wr(m_pmu, 0x80CU, 0x12345674U);
		drain();
		wr(m_pmu, 0x400U, 1U);
	}
	for (;;) __asm__ volatile("dsb sy\n\twfi" ::: "memory");
}

void M8930_interrupt_init(void)
{
	boolean_t was = ml_set_interrupts_enabled(FALSE);
	uint32_t i, irq = J5410_IRQ;
	if (controller_ready) { ml_set_interrupts_enabled(was); return; }
	m_gic_dist = ml_io_map(J5410_GIC_DIST_PA, 0x1000U);
	m_gic_cpu = ml_io_map(J5410_GIC_CPU_PA, 0x1000U);
	if (!m_gic_dist || !m_gic_cpu) panic("J5410 GIC IO mapping failed");
	for (i = 0; i < 8; i++) {
		wr(m_gic_dist, GIC_DIST_ENABLE_CLEAR + i * 4, 0xffffffffU);
		wr(m_gic_dist, GIC_DIST_PENDING_CLEAR + i * 4, 0xffffffffU);
	}
	/* L0 tick: mid priority, all CPU interfaces (only the boot CPU runs), level sensitive. */
	wr(m_gic_dist, GIC_DIST_PRI + (irq / 4) * 4,
	   (rd(m_gic_dist, GIC_DIST_PRI + (irq / 4) * 4) & ~(0xffU << ((irq % 4) * 8))) | (0x80U << ((irq % 4) * 8)));
	wr(m_gic_dist, GIC_DIST_TARGET + (irq / 4) * 4,
	   rd(m_gic_dist, GIC_DIST_TARGET + (irq / 4) * 4) | (0xffU << ((irq % 4) * 8)));
	wr(m_gic_dist, GIC_DIST_CONFIG + (irq / 16) * 4,
	   rd(m_gic_dist, GIC_DIST_CONFIG + (irq / 16) * 4) & ~(0x2U << ((irq % 16) * 2)));
	wr(m_gic_dist, GIC_DIST_CTRL, 1U);
	wr(m_gic_cpu, GIC_CPU_PRIMASK, 0xf0U);
	wr(m_gic_cpu, GIC_CPU_CTRL, 1U);
	drain();
	controller_ready = 1;
	printf("J5410 GIC up: ICDICTR=%08x ITARGETS0=%08x\n", rd(m_gic_dist, 0x004U), rd(m_gic_dist, GIC_DIST_TARGET));
	ml_set_interrupts_enabled(was);
}

void ios7j1_clk_dump(void);
void ios7j1_clk_dump(void) { }

void ios7j1_reboot_recovery(unsigned int secs);
void ios7j1_reboot_recovery(unsigned int secs)
{
	uint64_t end;
	__asm__ volatile("cpsid if");
	printf("\nJ1 halt: reboot to recovery in %u s\n", secs);
	if (timebase_ready) {
		end = mct_count() + (uint64_t)secs * J5410_HZ;
		while (mct_count() < end) if (m_wdt) wr(m_wdt, 0x08U, 0xFFFFU);	/* this wait ends in a reboot anyway */
	} else {
		volatile unsigned long long spin;
		for (spin = 0; spin < 2000000000ULL; spin++) ;
	}
	j5410_reboot_now();
}

void M8930_timebase_init(void)
{
	boolean_t was = ml_set_interrupts_enabled(FALSE);
	uint64_t a, b;
	uint32_t i, tcon;
	if (!controller_ready) panic("J5410 timebase before GIC");
	if (timebase_ready) { ml_set_interrupts_enabled(was); return; }
	m_mct = ml_io_map(J5410_MCT_PA, 0x1000U);
	m_wdt = ml_io_map(J5410_WDT_PA, 0x1000U);
	m_pmu = ml_io_map(J5410_PMU_PA, 0x1000U);
	m_marker = ml_io_map(J5410_MARKER_PA, 0x1000U);
	if (!m_mct || !m_wdt || !m_pmu) panic("J5410 timer IO mapping failed");
	ios7m8930_pet_wdt();
	tcon = rd(m_mct, MCT_G_TCON);
	printf("J5410 MCT G_TCON=%08x cnt=%08x:%08x WTCON=%08x WTCNT=%08x\n", tcon, rd(m_mct, MCT_G_CNT_U),
	    rd(m_mct, MCT_G_CNT_L), rd(m_wdt, 0), rd(m_wdt, 8));
	if (!(tcon & (1U << 8)))
		mct_write(MCT_G_TCON, tcon | (1U << 8), MCT_G_WSTAT, 1U << 16);
	a = mct_count(); b = a;
	for (i = 0; i < 1000000U; i++) { b = mct_count(); if (b != a) break; }
	if (a == b) panic("J5410 MCT global counter does not run");
	/* L0: stop, prescale 1 (12 MHz), interrupt enable, ack anything stale. */
	mct_write(MCT_L0 + L_TCON, 0, MCT_L0 + L_WSTAT, 1U << 3);
	mct_write(MCT_L0 + L_TCNTB, 1U, MCT_L0 + L_WSTAT, 1U << 0);
	wr(m_mct, MCT_L0 + L_INT_CSTAT, 1U);
	wr(m_mct, MCT_L0 + L_INT_ENB, 1U);
	/* Calibrate: the first boot showed ticks ~12x slower than G/2. Time a one-shot of CAL counts
	 * against the global counter (bounded to 3 s; the GIC line is still disabled). */
	{
		const uint32_t CAL = 120000U;
		uint64_t g0, g1, lim;
		mct_write(MCT_L0 + L_ICNTB, (1U << 31) | CAL, MCT_L0 + L_WSTAT, 1U << 1);
		g0 = mct_count(); lim = g0 + 3ULL * J5410_HZ;
		mct_write(MCT_L0 + L_TCON, (1U << 1) | (1U << 0), MCT_L0 + L_WSTAT, 1U << 3);
		do { g1 = mct_count(); } while (!(rd(m_mct, MCT_L0 + L_INT_CSTAT) & 1U) && g1 < lim);
		mct_write(MCT_L0 + L_TCON, 0, MCT_L0 + L_WSTAT, 1U << 3);
		wr(m_mct, MCT_L0 + L_INT_CSTAT, 1U);
		if (g1 < lim && g1 > g0)
			m_l0_hz = (uint32_t)(((uint64_t)CAL * J5410_HZ) / (g1 - g0));
		printf("J5410 L0 calibration: %u counts in %u G ticks -> %u Hz%s\n", CAL, (unsigned)(g1 - g0),
		    m_l0_hz, g1 >= lim ? " (TIMEOUT, using default)" : "");
	}
	/* Cache self-test: 4 MB (> 2 MB A15 L2) written and verified twice through the cached kernel map, so
	 * dirty lines are evicted to DRAM and refetched. Mismatches = lost/corrupted cache lines. */
	{
		static uint32_t mt[1U << 20];
		uint32_t i, pass, bad = 0, first = ~0U, firstv = 0;
		uint64_t g0 = mct_count();
		for (pass = 0; pass < 2U; pass++) {
			uint32_t x = pass ? 0xA5A5A5A5U : 0x12345678U;
			for (i = 0; i < (1U << 20); i++) mt[i] = (i * 2654435761U) ^ x;
			for (i = 0; i < (1U << 20); i++)
				if (mt[i] != ((i * 2654435761U) ^ x)) { if (!bad++) { first = i; firstv = mt[i]; } }
		}
		printf("J5410 cachetest: %u bad words (first idx %u val %08x) in %u us\n", bad, first, firstv,
		    (unsigned)((mct_count() - g0) / 24U));
	}
	/* CPU speed check: 1,000,000 iterations of a register loop, timed on the global counter. */
	{
		uint32_t sctlr, actlr, n = 1000000U;
		uint64_t g0 = mct_count(), g1;
		__asm__ volatile("1: subs %0, %0, #1\n\tbne 1b" : "+r"(n) :: "cc");
		g1 = mct_count();
		__asm__ volatile("mrc p15, 0, %0, c1, c0, 0" : "=r"(sctlr));
		__asm__ volatile("mrc p15, 0, %0, c1, c0, 1" : "=r"(actlr));
		printf("J5410 cpu: 1M loop = %u us, SCTLR=%08x ACTLR=%08x\n", (unsigned)((g1 - g0) / 24U), sctlr, actlr);
	}
	m_t0 = mct_count();
	timebase_ready = 1;
	clock_decrementer = J5410_HZ / 100U;	/* 10 ms */
	gPEClockFrequencyInfo.timebase_frequency_hz = J5410_HZ;
	gPEClockFrequencyInfo.dec_clock_rate_hz = J5410_HZ;
	rtc_configure(J5410_HZ);
	M8930_timer_enabled(TRUE);
	printf("J5410 timebase up %u Hz\n", J5410_HZ);
	ml_set_interrupts_enabled(was);
}

/* One-shot L0 shot of `clock_decrementer` timebase ticks (capped at 10 ms: the tick also pets the
 * watchdog, flushes the console and drives the timed reboot). */
void M8930_timer_enabled(int enable)
{
	boolean_t was = ml_set_interrupts_enabled(FALSE);
	uint64_t req = clock_decrementer;
	uint32_t lt;
	if (!timebase_ready) panic("J5410 timer before timebase");
	j5410_tstat[0]++;
	if (enable && req < 24000U) j5410_tstat[1]++;	/* < 1 ms requested */
	if (enable && req < j5410_tstat[2]) j5410_tstat[2] = (unsigned int)req;
	if (!enable || req == ~0ULL || req > J5410_HZ / 100U) req = J5410_HZ / 100U;
	if (req < 240U) req = 240U;	/* >= 10 us: a past deadline must not become an IRQ storm */
	lt = (uint32_t)((req * m_l0_hz) / J5410_HZ);
	if (lt < 2U) lt = 2U;
	mct_write(MCT_L0 + L_TCON, 0, MCT_L0 + L_WSTAT, 1U << 3);
	wr(m_mct, MCT_L0 + L_INT_CSTAT, 1U);
	wr(m_gic_dist, GIC_DIST_PENDING_CLEAR + (J5410_IRQ / 32) * 4, 1U << (J5410_IRQ % 32));
	mct_write(MCT_L0 + L_ICNTB, (1U << 31) | lt, MCT_L0 + L_WSTAT, 1U << 1);
	m_deadline = mct_count() + req;
	mct_write(MCT_L0 + L_TCON, (1U << 1) | (1U << 0), MCT_L0 + L_WSTAT, 1U << 3);
	wr(m_gic_dist, GIC_DIST_ENABLE_SET + (J5410_IRQ / 32) * 4, 1U << (J5410_IRQ % 32));
	drain();
	armed = 1;
	arm_gen++;
	ml_set_interrupts_enabled(was);
}

uint64_t M8930_get_timebase(void)
{
	uint64_t v;
	boolean_t w;
	if (!timebase_ready) return 0;
	w = ml_set_interrupts_enabled(FALSE);
	v = mct_count();
	ml_set_interrupts_enabled(w);
	return v;
}

uint64_t M8930_timer_value(void)
{
	boolean_t w = ml_set_interrupts_enabled(FALSE);
	uint64_t now, rem = 0;
	if (timebase_ready && armed) {
		now = mct_count();
		rem = m_deadline > now ? m_deadline - now : 0;
	}
	ml_set_interrupts_enabled(w);
	return rem;
}

unsigned int M8930_dbg(int w)
{
	(void)w;
	return timebase_ready ? (unsigned int)mct_count() : 0xdeadbeefU;
}

void M8930_diag(void) { }

unsigned int ios7m8930_pcring[16], ios7m8930_lrring[16], ios7m8930_pcidx;
void *ios7m8930_thring[16];
extern void *current_thread(void);
void M8930_handle_interrupt(void *context)
{
	uint32_t ack, irq, budget;
	{ arm_saved_state_t *ss = (arm_saved_state_t *)context;
	  unsigned int k = ios7m8930_pcidx++ & 15U; ios7m8930_pcring[k] = ss->pc; ios7m8930_lrring[k] = ss->lr; ios7m8930_thring[k] = current_thread(); }
	uint64_t h0 = timebase_ready ? mct_count() : 0;
	if (armed) { if (h0 >= m_deadline) { uint32_t l = (uint32_t)(h0 - m_deadline); j5410_tstat[5] += l; if (l > j5410_tstat[6]) j5410_tstat[6] = l; } else j5410_tstat[7]++; }
	++m_irqs;
	if (!controller_ready || !timebase_ready) panic("J5410 IRQ before init");
	for (budget = 0; budget < 1U; budget++) {	/* one interrupt per entry; IRQ re-enters if more pend */
		ack = rd(m_gic_cpu, GIC_CPU_INTACK);
		irq = ack & 0x3ffU;
		if (irq >= 1020U) return;
		if (irq != J5410_IRQ) {
			wr(m_gic_cpu, GIC_CPU_EOI, ack);
			panic("J5410 unexpected IRQ %u", irq);
		}
		wr(m_mct, MCT_L0 + L_INT_CSTAT, 1U);	/* level source: clear before EOI */
		armed = 0;
		wr(m_gic_cpu, GIC_CPU_EOI, ack);
		drain();
		ios7m8930_pet_wdt();
		{
			uint32_t gen = arm_gen;
			rtclock_intr((arm_saved_state_t *)context);
			if (arm_gen == gen) { clock_decrementer = J5410_HZ / 100U; M8930_timer_enabled(TRUE); }
		}
		if (!(m_irqs & 255U)) {
			extern void ios7j1_seclog_tick(unsigned int, unsigned int, unsigned int);
			arm_saved_state_t *ss2 = (arm_saved_state_t *)context;
			ios7j1_seclog_tick(m_irqs, ss2->pc, ss2->lr);	/* pc, lr of the interrupted code */
		}
		if (!(m_irqs & 3U))
			ios7m8930_fb_flush();
		if (mct_count() - m_t0 >= J5410_RUN_SECONDS * J5410_HZ) {
			printf("\nJ1 timed reboot to recovery: irqs=%u mct writes=%u timeouts=%u maxloops=%u\n", m_irqs,
			    j5410_wstat[0], j5410_wstat[1], j5410_wstat[2]);
			{ extern void ios7j5410_iokit_stats(void); ios7j5410_iokit_stats(); }
			{ extern void ios7j5410_dump_threads(void); ios7j5410_dump_threads(); }
			printf("J5410 timer late avg=%u us max=%u us early=%u\n", m_irqs ? j5410_tstat[5] / m_irqs / 24U : 0U, j5410_tstat[6] / 24U, j5410_tstat[7]);
			printf("J5410 timer arms=%u under1ms=%u minreq=%u handler avg=%u us max=%u us\n", j5410_tstat[0],
			    j5410_tstat[1], j5410_tstat[2], m_irqs ? j5410_tstat[3] / m_irqs / 24U : 0U, j5410_tstat[4] / 24U);
			{ unsigned int k;	/* last 16 interrupted contexts, oldest first */
			  for (k = 0; k < 16U; k++) {
				unsigned int i = (ios7m8930_pcidx + k) & 15U;
				printf("J5410 sample pc=%08x lr=%08x thread=%p\n", ios7m8930_pcring[i], ios7m8930_lrring[i], ios7m8930_thring[i]);
			  } }
			{ extern void ios7j1_seclog_tick(unsigned int, unsigned int, unsigned int);
			  ios7j1_seclog_tick(0xDEADB007U, m_irqs, (unsigned)((mct_count() - m_t0) / J5410_HZ)); }
			j5410_reboot_now();
		}
	}
	{ uint32_t d = (uint32_t)(mct_count() - h0); j5410_tstat[3] += d; if (d > j5410_tstat[4]) j5410_tstat[4] = d; }
}
#endif /* BOARD_CONFIG_EXYNOS5410_JA3G */
