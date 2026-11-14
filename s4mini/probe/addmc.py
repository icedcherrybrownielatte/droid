import sys
p = sys.argv[1]
s = open(p).read()
key = '\t".thumb_func\\n.globl _memcpy.47\\n'
i = s.find(key)
assert i > 0, "no 47"
add = "".join('\t".thumb_func\\n.globl _memcpy.%d\\n_memcpy.%d:\\n b.w _memcpy\\n"\n' % (n, n) for n in range(3, 47))
open(p, "w").write(s[:i] + add + s[i:])
print("ok")
