p="/home/user/xnu-j1/xnu/osfmk/kern/processor.c"; s=open(p).read()
a=s.index("processor_init(\n\tprocessor_t\t\t\tprocessor,")
b=s.index("\n}\n",a)
body=s[a:b]
rep=[("\ttimer_call_setup(&processor->quantum_timer, thread_quantum_expire, processor);","\tMARKP(39);\n\ttimer_call_setup(&processor->quantum_timer, thread_quantum_expire, processor);\n\tMARKP(40);"),
("\tprocessor_data_init(processor);","\tprocessor_data_init(processor);\n\tMARKP(41);"),
("\ts = splsched();\n\tpset_lock(pset);","\ts = splsched();\n\tMARKP(42);\n\tpset_lock(pset);\n\tMARKP(43);"),
("\tpset_unlock(pset);\n\tsplx(s);","\tpset_unlock(pset);\n\tMARKP(44);\n\tsplx(s);\n\tMARKP(45);"),
("\tsimple_unlock(&processor_list_lock);","\tsimple_unlock(&processor_list_lock);\n\tMARKP(46);")]
for o,n in rep:
    assert o in body, o
    body=body.replace(o,n,1)
s=s[:a]+body+s[b:]
open(p,"w").write(s); print("ok")
