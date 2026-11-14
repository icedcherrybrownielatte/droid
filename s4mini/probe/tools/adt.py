import struct, sys
def parse(d, o=0):
    np, nc = struct.unpack_from('<II', d, o); o += 8
    props = []
    for _ in range(np):
        name = d[o:o + 32].split(b'\0')[0].decode(); ln = struct.unpack_from('<I', d, o + 32)[0]; o += 36
        L = ln & 0x7fffffff
        props.append([name, ln, d[o:o + L]]); o += (L + 3) & ~3
    kids = []
    for _ in range(nc):
        k, o = parse(d, o); kids.append(k)
    return [props, kids], o
def ser(n):
    props, kids = n
    out = struct.pack('<II', len(props), len(kids))
    for name, ln, v in props:
        out += name.encode().ljust(32, b'\0') + struct.pack('<I', (ln & 0x80000000) | len(v)) + v + b'\0' * (((len(v) + 3) & ~3) - len(v))
    for k in kids: out += ser(k)
    return out
def nm(n):
    for p in n[0]:
        if p[0] == 'name': return p[2].split(b'\0')[0].decode()
def dump(n, ind=0):
    print(' ' * ind + str(nm(n)))
    for p in n[0]: print(' ' * ind + '  .', p[0], p[2][:40])
    for k in n[1]: dump(k, ind + 2)
if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    root, end = parse(d)
    print('parsed', end, 'of', len(d), 'roundtrip', ser(root) == d[:end])
    dump(root)
    if len(sys.argv) > 2:
        for k in root[1]:
            if nm(k) == 'chosen':
                names = [p[0] for p in k[0]]
                for pn, v in (('display-scale', struct.pack('<I', 2)), ('display-rotation', struct.pack('<I', 0))):
                    if pn in names: k[0][names.index(pn)][2] = v
                    else: k[0].append([pn, len(v), v])
        open(sys.argv[2], 'wb').write(ser(root) + d[end:])
        print('written', sys.argv[2])
