/*
 * MSM8930 (Galaxy S4 mini, serrano3gxx) interrupt controller + DGT timer.
 * SCAFFOLD: written from the Samsung/LineageOS msm8930 kernel, NOT compiled
 * or run on hardware yet.
 */
#ifndef IOS7LAB_M8930_TIMER_H
#define IOS7LAB_M8930_TIMER_H
#include <mach/mach_types.h>

#define M8930_TMR_PA		0x0200A000U	/* GPT at +0x04, DGT at +0x24 */
#define M8930_GIC_DIST_PA	0x02000000U
#define M8930_GIC_CPU_PA	0x02002000U
#define M8930_IO_BYTES		0x1000U

#define M8930_DGT_HZ		6750000U	/* 27 MHz / 4, per Linux timer.c */
#define M8930_DGT_IRQ		17U		/* PPI 1 (INT_DEBUG_TIMER_EXP) */
#define M8930_MIN_MATCH_TICKS	16U

void M8930_interrupt_init(void);
void M8930_timebase_init(void);
void M8930_handle_interrupt(void *context);
uint64_t M8930_get_timebase(void);
uint64_t M8930_timer_value(void);
void M8930_timer_enabled(int enable);
extern uint64_t clock_decrementer;
#endif
