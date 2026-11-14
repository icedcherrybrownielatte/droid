import os
p = os.path.expanduser("~/xnu-j1/xnu/osfmk/kern/ast.c")
s = open(p).read()
def rep(a,b):
    global s
    assert a in s, a
    s = s.replace(a,b,1)
rep("\t\tif (\t(reasons & AST_URGENT)\t\t\t\t&&\n", "\t\tios7m8930_mark(1044);\n\t\tif (\t(reasons & AST_URGENT)\t\t\t\t&&\n")
rep("\t\t\tml_set_interrupts_enabled(enable);\n\n#ifdef\tMACH_BSD", "\t\t\tios7m8930_mark(1045);\n\t\t\tml_set_interrupts_enabled(enable);\n\t\t\tios7m8930_mark(1046);\n\n#ifdef\tMACH_BSD")
rep("\t\t\t\tbsd_ast(thread);\n", "\t\t\t\tios7m8930_mark(1047);\n\t\t\t\tbsd_ast(thread);\n\t\t\t\tios7m8930_mark(1048);\n")
open(p,"w").write(s)
print("ok")
