#!/bin/bash
if [ $# -eq 0 ] 
then 
    echo Usage: ./run_hello.sh comp_scheme
    exit
fi

comp=$1

# specify debug flags below
debug=CacheAll,ResponsePort,SyscallBase,\
SnoopFilter,DRAM,DMA,MemoryAccess,\
MMU,PacketQueue,AddrRanges,TLB,TLBVerbose,\
XBar,PageTableWalker,AnnotateAll,FmtFlag

out=m5out_comp/$comp
mkdir -p $out

build/X86/gem5.opt \
--debug-flags=${debug} \
-d $out \
configs/example/gem5_library/x86-hello.py \
--comp=$comp \
> $out/out_${comp}.txt &