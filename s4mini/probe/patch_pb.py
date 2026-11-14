p="/home/user/xnu-j1/xnu/osfmk/kern/processor.c"; s=open(p).read()
a=s.index("processor_bootstrap(void)\n{")
b=s.index("\n}\n",a)
body=s[a:b]
new=body
new=new.replace("{\n\tpset_init(&pset0, &pset_node0);","{\n\tMARKP(30);\n\tpset_init(&pset0, &pset_node0);\n\tMARKP(31);",1)
new=new.replace("\tsimple_lock_init(&pset_node_lock, 0);","\tsimple_lock_init(&pset_node_lock, 0);\n\tMARKP(32);",1)
new=new.replace("\tqueue_init(&threads);","\tqueue_init(&threads);\n\tMARKP(33);",1)
new=new.replace("\tmaster_processor = cpu_to_processor(master_cpu);","\tmaster_processor = cpu_to_processor(master_cpu);\n\tMARKP(34);",1)
new=new.replace("\tprocessor_init(master_processor, master_cpu, &pset0);","\tprocessor_init(master_processor, master_cpu, &pset0);\n\tMARKP(35);",1)
s=s[:a]+new+s[b:]
hdr='''#if defined(BOARD_CONFIG_MSM8930_SERRANO)
extern void ios7m8930_mark(unsigned int n);
#define MARKP(n) ios7m8930_mark(n)
#else
#define MARKP(n) do{}while(0)
#endif
'''
i=s.index("processor_bootstrap(void)")
# insert header before the function's return type line (previous line start)
j=s.rfind("\n\n",0,i)
s=s[:j]+"\n"+hdr+s[j:]
open(p,"w").write(s); print("ok")
