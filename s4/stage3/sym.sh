#!/bin/bash
# sym.sh <hexaddr>...: nearest preceding kernel symbol in the S4 XNU build
K=~/xnu-s4/xnu/BUILD/obj/RELEASE_ARM_EXYNOS5410_JA3G/mach_kernel
~/cctools/bin/arm-apple-darwin11-nm -n $K > /tmp/s4syms.txt
for a in "$@"; do
  awk -v A="$a" 'BEGIN{t=strtonum("0x" A)} {v=strtonum("0x" $1); if (v<=t) {best=$0} else {exit}} END{print A, best}' /tmp/s4syms.txt
done
