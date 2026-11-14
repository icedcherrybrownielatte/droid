#!/bin/bash
# Build XNU for the S4 (EXYNOS5410_JA3G) in ~/xnu-s4/xnu. Log: ~/xnu-s4-build.log
cd ~/xnu-s4/xnu && export B=$HOME/cctools/bin PATH=$HOME/cctools/bin:$PATH MIGCC=$HOME/cctools/bin/cc HOST_CC=$HOME/cctools/bin/hostcc && . SETUP/setup.sh >/dev/null 2>&1
make TARGET_CONFIGS="release arm EXYNOS5410_JA3G" MAKEJOBS=-j8 SDKROOT=$HOME/sdk/ios7 >~/xnu-s4-build.log 2>&1
if grep -qE ": error|Undefined symbols" ~/xnu-s4-build.log; then grep -E ": error|Undefined symbols" -A3 ~/xnu-s4-build.log | head -40; echo BUILD_FAILED; exit 3; fi
ls -la BUILD/obj/RELEASE_ARM_EXYNOS5410_JA3G/mach_kernel && echo BUILD_OK
