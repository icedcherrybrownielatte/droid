ENTRY(start)
SECTIONS { . = 0x80208000; .text : { *(.text.start) *(.text*) *(.rodata*) *(.data*) } . = ALIGN(4); _stub_end = .; /DISCARD/ : { *(.comment) *(.ARM.*) *(.note*) } }
