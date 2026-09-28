# bpf/Makefile
# Compile BPF bytecode for DROS enforcement engine.
# Run on a node with kernel headers installed.
#
# Prerequisites (Ubuntu):
#   apt install clang llvm libbpf-dev linux-headers-$(uname -r)
#
# Output: dros_enforce.bpf.o (load with bpftool or cilium/ebpf Go library)

ARCH := $(shell uname -m)
BPF_TARGET := dros_enforce.bpf.o
BPF_SRC := dros_enforce.bpf.c

# Kernel headers path
KINC := /usr/include/$(shell uname -m)-linux-gnu

.PHONY: all clean

all: $(BPF_TARGET)

$(BPF_TARGET): $(BPF_SRC)
	@echo "Compiling BPF: $(BPF_TARGET)"
	clang -g -O2 -target bpf -D__TARGET_ARCH_x86 \
	  -I$(KINC) \
	  -I/usr/include/bpf \
	  -c $(BPF_SRC) -o $(BPF_TARGET)
	@echo "Verifying..."
	llvm-objdump -S $(BPF_TARGET) | head -n 50

clean:
	rm -f $(BPF_TARGET)
