# bpf/Makefile
# Compile BPF bytecode for DROS enforcement engine.
# Run on a node with linux-libc-dev installed.
#
# Prerequisites (Ubuntu):
#   apt install clang llvm linux-libc-dev
#
# Output: dros_enforce.bpf.o

ARCH := $(shell dpkg-architecture -qDEB_HOST_MULTIARCH 2>/dev/null || echo x86_64-linux-gnu)
BPF_TARGET := dros_enforce.bpf.o
BPF_SRC := dros_enforce.bpf.c

# Kernel/UAPI headers from linux-libc-dev package.
KINC := /usr/include/$(ARCH)

.PHONY: all clean

all: $(BPF_TARGET)

$(BPF_TARGET): $(BPF_SRC)
	@echo "Compiling BPF: $(BPF_TARGET)"
	clang -g -O2 -target bpf -D__TARGET_ARCH_x86 \
	  -I$(KINC) \
	  -I/usr/include/linux \
	  -I/usr/include/asm-generic \
	  -c $(BPF_SRC) -o $(BPF_TARGET)
	@echo "Verifying..."
	llvm-objdump -S $(BPF_TARGET) | head -n 60

clean:
	rm -f $(BPF_TARGET)
