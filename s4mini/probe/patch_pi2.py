p="/home/user/xnu-j1/xnu/osfmk/kern/processor.c"; s=open(p).read()
o="\tsimple_lock(&processor_list_lock);\n\tif (processor_list == NULL)\n\t\tprocessor_list = processor;\n\telse\n\t\tprocessor_list_tail->processor_list = processor;\n\tprocessor_list_tail = processor;\n\tprocessor_count++;\n\tsimple_unlock(&processor_list_lock);\n\tMARKP(46);"
assert o in s
n="\tMARKP(47);\n\tsimple_lock(&processor_list_lock);\n\tMARKP(48);\n\tif (processor_list == NULL)\n\t\tprocessor_list = processor;\n\telse\n\t\tprocessor_list_tail->processor_list = processor;\n\tMARKP(49);\n\tprocessor_list_tail = processor;\n\tprocessor_count++;\n\tMARKP(50);\n\tsimple_unlock(&processor_list_lock);\n\tMARKP(46);"
s=s.replace(o,n,1)
open(p,"w").write(s); print("ok")
