#!/usr/bin/env python3
"""Minimal Apple-format device tree for the S4 mini XNU bring-up."""
import struct,sys
def prop(name,val):
    if isinstance(val,str): val=val.encode()+b'\0'
    elif isinstance(val,int): val=struct.pack('<I',val)
    pad=(-len(val))%4
    return name.encode().ljust(32,b'\0')+struct.pack('<I',len(val))+val+b'\0'*pad
def node(props,children=()):
    b=struct.pack('<II',len(props),len(children))
    for n,v in props: b+=prop(n,v)
    for c in children: b+=c
    return b
chosen=node([("name","chosen"),("firmware-version","uniLoader-serrano"),("debug-enabled",0)],
            [node([("name","memory-map")])])
cpu0=node([("name","cpu"),("device_type","cpu"),("reg",0),("cpu-id",0),("compatible","cortex,krait")])
cpus=node([("name","cpus")],[cpu0])
armio=node([("name","arm-io"),("device_type","bus"),("compatible","arm-io,msm8930")])
defaults=node([("name","defaults")])
root=node([("name","device-tree"),("device_type","bootrom"),("model","GT-I9190"),
           ("compatible",b"S4MINI,1\0AppleARM\0".decode()[:-1] if False else "S4MINI,1"),
           ("serial-number","0000"),("#address-cells",1),("#size-cells",1)],
          [chosen,cpus,armio,defaults])
# compatible must hold two strings; patch property bytes manually
root=root.replace(prop("compatible","S4MINI,1"),prop("compatible",b"S4MINI,1\0AppleARM\0"),1)
open(sys.argv[1],"wb").write(root)
print(len(root))
