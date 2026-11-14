import os, re
root = os.path.expanduser("~/xnu-j1/xnu/bsd/kern/")
NEW = "#if defined(BOARD_CONFIG_QSD8250_LEO) || defined(BOARD_CONFIG_MSM8930_SERRANO)\n"
OLD = "#if defined(BOARD_CONFIG_QSD8250_LEO)\n"
nl = chr(92) + "n"
# kern_exec.c: the two #if around init execve prints
p = root + "kern_exec.c"
s = open(p).read()
for marker in ['    printf("Leo boot: init execve begin', '    printf("Leo boot: init execve returned']:
    i = s.index(marker)
    j = s.rfind(OLD, 0, i)
    assert j >= 0 and i - j < 80, (marker, i - j)
    s = s[:j] + NEW + s[j+len(OLD):]
a = "\t/* Use the user specified program name. */\n"
s = s.replace(a, '\t{ extern int printf(const char *, ...); printf("J1 init: load_init_program begin' + nl + '"); }\n' + a, 1)
open(p, "w").write(s)
# bsd_init.c: utaskbootstrap prints
p = root + "bsd_init.c"
s = open(p).read()
for marker in ['    printf("Leo boot: cloneproc returned', '        kern_return_t resume_result;']:
    i = s.index(marker)
    j = s.rfind(OLD, 0, i)
    assert j >= 0 and i - j < 80, (marker, i - j)
    s = s[:j] + NEW + s[j+len(OLD):]
a = "\tprocess_name(\"init\", p);\n"
s = s.replace(a, a + '\tprintf("J1 init: bsdinit_task' + nl + '");\n', 1)
open(p, "w").write(s)
print("ok")
