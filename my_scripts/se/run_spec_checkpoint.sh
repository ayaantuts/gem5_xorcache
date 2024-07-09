#!/bin/bash
if [ $# -eq 0 ]
then
    echo Usage: ./run_spec_checkpoint.sh spec_bench_num
    exit
fi

spec_bench_num=$1

# specify debug flags below
# debug=\
# Decode,\
# CacheAll,ResponsePort,SyscallBase,\
# SnoopFilter,DMA,MemoryAccess,\
# MMU,PacketQueue,AddrRanges,TLB,TLBVerbose,\
# XBar,PageTableWalker,AnnotateAll,FmtFlag

out=m5out_spec_ckpt/${spec_bench_num}
mkdir -p $out

gem5=/home/zhewen/repo/gem5-dev/gem5

nohup ${gem5}/build/X86/gem5.opt \
-d ${gem5}/$out \
${gem5}/configs/example/gem5_library/checkpoints/simpoints-se-checkpoint-spec.py \
--bench_num=${spec_bench_num} \
> ${gem5}/$out/log.txt &
