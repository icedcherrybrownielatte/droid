p="/home/user/xnu-j1/xnu/osfmk/arm/arm_init.c"; s=open(p).read()
reps=[("    ios7j1_kernel_continuing();\n#endif\n","    ios7j1_kernel_continuing();\n#endif\n    MARK(200);\n"),
("        kprintf(\"cache: initializing i+dcache ... \");\n        cache_initialize();","        MARK(201);\n        kprintf(\"cache: initializing i+dcache ... \");\n        cache_initialize();\n        MARK(202);"),
("    thread = current_thread();\n    thread->machine.preempt_count = 1;","    MARK(203);\n    thread = current_thread();\n    thread->machine.preempt_count = 1;"),
("    arm_processor_identify();","    MARK(204);\n    arm_processor_identify();\n    MARK(205);"),
("    init_vfp();\n","    init_vfp();\n    MARK(206);\n")]
for o,n in reps:
    assert o in s,o
    s=s.replace(o,n,1)
open(p,"w").write(s); print("ok")
