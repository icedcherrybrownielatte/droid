/*
 * MSM8930 qGIC + DGT timer for XNU. SCAFFOLD, see msm8930_timer.h.
 * Register layout (kernel timer.c): TMR+0x24 = DGT {MATCH 0x0, COUNT 0x4,
 * ENABLE 0x8 (bit0 EN, bit1 CLR_ON_MATCH), CLEAR 0xC}, DGT_CLK_CTL at TMR+0x34
 * (divider; value 3 = /4).
 */
#include <mach/mach_types.h>
#include <mach/arm/thread_status.h>
#include <pexpert/pexpert.h>
#include <pexpert/arm/protos.h>
#include <machine/machine_routines.h>
#include <kern/debug.h>
#include "msm8930_timer.h"

#if defined(BOARD_CONFIG_MSM8930_SERRANO)

#define DGT_BASE		0x24U
#define DGT_MATCH_VAL		(DGT_BASE + 0x00U)
#define DGT_COUNT_VAL		(DGT_BASE + 0x04U)
#define DGT_ENABLE		(DGT_BASE + 0x08U)
#define DGT_CLEAR		(DGT_BASE + 0x0CU)
#define DGT_CLK_CTL		0x34U
#define DGT_CLK_DIV_4		3U
#define DGT_EN			1U

#define GIC_DIST_CTRL		0x000U
#define GIC_DIST_ENABLE_SET	0x100U
#define GIC_DIST_ENABLE_CLEAR	0x180U
#define GIC_DIST_PENDING_CLEAR	0x280U
#define GIC_DIST_PRI		0x400U
#define GIC_DIST_CONFIG		0xc00U
#define GIC_CPU_CTRL		0x00U
#define GIC_CPU_PRIMASK		0x04U
#define GIC_CPU_INTACK		0x0cU
#define GIC_CPU_EOI		0x10U

extern void rtc_configure(uint64_t hz);
extern void rtclock_intr(arm_saved_state_t *regs);

uint64_t clock_decrementer;
static vm_offset_t m_tmr, m_gic_dist, m_gic_cpu;
static uint32_t controller_ready, timebase_ready, armed;
static uint32_t last_lo, hi_word;	/* software extension of the 32-bit counter */

static inline uint32_t rd(vm_offset_t b, uint32_t o) { return *(volatile uint32_t *)(b + o); }
static inline void wr(vm_offset_t b, uint32_t o, uint32_t v) { *(volatile uint32_t *)(b + o) = v; }
static inline void drain(void) { __asm__ volatile("dsb sy" ::: "memory"); }

/* Callers hold interrupts off. Counter is 32-bit: detect wrap on each read. */
static uint64_t dgt_get_count(void)
{
	uint32_t a, b, lo;
	do { a = rd(m_tmr, DGT_COUNT_VAL); b = rd(m_tmr, DGT_COUNT_VAL); } while (a != b);
	lo = b;
	if (lo < last_lo) hi_word++;
	last_lo = lo;
	return ((uint64_t)hi_word << 32) | lo;
}

void M8930_interrupt_init(void)
{
	boolean_t was = ml_set_interrupts_enabled(FALSE);
	uint32_t i, irq = M8930_DGT_IRQ;
	if (controller_ready) { ml_set_interrupts_enabled(was); return; }
	m_gic_dist = ml_io_map(M8930_GIC_DIST_PA, M8930_IO_BYTES);
	m_gic_cpu  = ml_io_map(M8930_GIC_CPU_PA, M8930_IO_BYTES);
	if (!m_gic_dist || !m_gic_cpu) panic("M8930 GIC IO mapping failed");
	/* Disable + clear all, then configure the DGT PPI: mid priority, level. */
	for (i = 0; i < 8; i++) {
		wr(m_gic_dist, GIC_DIST_ENABLE_CLEAR + i * 4, 0xffffffffU);
		wr(m_gic_dist, GIC_DIST_PENDING_CLEAR + i * 4, 0xffffffffU);
	}
	wr(m_gic_dist, GIC_DIST_PRI + (irq / 4) * 4,
	   (rd(m_gic_dist, GIC_DIST_PRI + (irq / 4) * 4) & ~(0xffU << ((irq % 4) * 8))) |
	   (0x80U << ((irq % 4) * 8)));
	wr(m_gic_dist, GIC_DIST_CONFIG + (irq / 16) * 4,
	   rd(m_gic_dist, GIC_DIST_CONFIG + (irq / 16) * 4) & ~(0x3U << ((irq % 16) * 2)));
	wr(m_gic_dist, GIC_DIST_CTRL, 1U);
	wr(m_gic_cpu, GIC_CPU_PRIMASK, 0xf0U);
	wr(m_gic_cpu, GIC_CPU_CTRL, 1U);
	drain();
	controller_ready = 1;
	ml_set_interrupts_enabled(was);
}

void M8930_timebase_init(void)
{
	boolean_t was = ml_set_interrupts_enabled(FALSE);
	uint64_t a, b;
	uint32_t i;
	if (!controller_ready) panic("M8930 timebase before GIC");
	if (timebase_ready) { ml_set_interrupts_enabled(was); return; }
	m_tmr = ml_io_map(M8930_TMR_PA, M8930_IO_BYTES);
	if (!m_tmr) panic("M8930 timer IO mapping failed");
	wr(m_tmr, DGT_CLK_CTL, DGT_CLK_DIV_4);
	wr(m_tmr, DGT_ENABLE, 0);		/* stop, no clear-on-match: free-running */
	wr(m_tmr, DGT_CLEAR, 0);
	wr(m_tmr, DGT_ENABLE, DGT_EN);
	drain();
	last_lo = rd(m_tmr, DGT_COUNT_VAL);
	hi_word = 0;
	a = dgt_get_count(); b = a;
	for (i = 0; i < 65536U; i++) { b = dgt_get_count(); if (b != a) break; }
	if (a == b) panic("M8930 DGT did not advance");
	timebase_ready = 1;
	clock_decrementer = M8930_DGT_HZ / 100U;	/* 10 ms tick */
	gPEClockFrequencyInfo.timebase_frequency_hz = M8930_DGT_HZ;
	gPEClockFrequencyInfo.dec_clock_rate_hz = M8930_DGT_HZ;
	rtc_configure(M8930_DGT_HZ);
	M8930_timer_enabled(TRUE);
	ml_set_interrupts_enabled(was);
}

void M8930_timer_enabled(int enable)
{
	boolean_t was = ml_set_interrupts_enabled(FALSE);
	uint32_t irq = M8930_DGT_IRQ, ticks;
	uint64_t req = clock_decrementer;
	if (!timebase_ready) panic("M8930 timer before timebase");
	if (!enable || req == ~0ULL) {
		wr(m_gic_dist, GIC_DIST_ENABLE_CLEAR + (irq / 32) * 4, 1U << (irq % 32));
		armed = 0;
		ml_set_interrupts_enabled(was);
		return;
	}
	ticks = req > 0x7fffffffU ? 0x7fffffffU : (uint32_t)req;
	if (ticks < M8930_MIN_MATCH_TICKS) ticks = M8930_MIN_MATCH_TICKS;
	/* MATCH_VAL is compared against the low 32 bits of COUNT_VAL. */
	wr(m_tmr, DGT_MATCH_VAL, rd(m_tmr, DGT_COUNT_VAL) + ticks);
	wr(m_gic_dist, GIC_DIST_PENDING_CLEAR + (irq / 32) * 4, 1U << (irq % 32));
	wr(m_gic_dist, GIC_DIST_ENABLE_SET + (irq / 32) * 4, 1U << (irq % 32));
	drain();
	armed = 1;
	ml_set_interrupts_enabled(was);
}

uint64_t M8930_get_timebase(void)
{
	uint64_t v;
	boolean_t w;
	if (!timebase_ready) return 0;
	w = ml_set_interrupts_enabled(FALSE);
	v = dgt_get_count();
	ml_set_interrupts_enabled(w);
	return v;
}

uint64_t M8930_timer_value(void)
{
	boolean_t w = ml_set_interrupts_enabled(FALSE);
	int32_t rem = 0;
	if (timebase_ready && armed)
		rem = (int32_t)(rd(m_tmr, DGT_MATCH_VAL) - rd(m_tmr, DGT_COUNT_VAL));
	ml_set_interrupts_enabled(w);
	return rem > 0 ? (uint32_t)rem : 0;
}

void M8930_handle_interrupt(void *context)
{
	uint32_t ack, irq, budget;
	if (!controller_ready || !timebase_ready) panic("M8930 IRQ before init");
	for (budget = 0; budget < 64U; budget++) {
		ack = rd(m_gic_cpu, GIC_CPU_INTACK);
		irq = ack & 0x3ffU;
		if (irq >= 1020U) return;			/* spurious / none pending */
		if (irq != M8930_DGT_IRQ) {
			wr(m_gic_cpu, GIC_CPU_EOI, ack);
			panic("M8930 unexpected IRQ %u", irq);
		}
		wr(m_gic_cpu, GIC_CPU_EOI, ack);
		drain();
		(void)dgt_get_count();			/* keep the wrap tracker current */
		rtclock_intr((arm_saved_state_t *)context);
#if !CONFIG_TICKLESS
		M8930_timer_enabled(TRUE);
#endif
	}
	panic("M8930 IRQ drain budget exceeded");
}
#endif /* BOARD_CONFIG_MSM8930_SERRANO */
