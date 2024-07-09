#!/bin/bash
if [ $# -eq 0 ] 
then 
    echo Usage: ./run_spec_ckpt_alter.sh comp_scheme
    exit
fi

comp=$1

# simpoint related
# simpoint_dir = /home/zhewen/repo/Simpoint.3.2/output/gem5/${spec_bench_name}/
# simpoint_file = ${simpoint_dir}/${spec_bench_name}_simpoint_file
# weight_file = ${simpoint_dir}/${spec_bench_name}_weight_file
# checkpoint_dir = /home/zhewen/repo/gem5-stable/gem5/m5out/${spec_bench_name}/${spec_bench_name}_checkpoint/

# specify debug flags below
debug=CacheAll,ResponsePort,SyscallBase,\
SnoopFilter,DMA,MemoryAccess,\
MMU,PacketQueue,AddrRanges,TLB,TLBVerbose,\
XBar,PageTableWalker,AnnotateAll,FmtFlag #,\
# DRAM
# debug=CacheAll

out=m5out_alter/$comp
mkdir -p $out

gem5=/home/zhewen/repo/gem5-dev/gem5

${gem5}/build/X86/gem5.opt \
-d ${gem5}/$out \
${gem5}/configs/example/gem5_library/checkpoints/simpoints-se-restore-alter.py \
--comp=$comp \
> ${gem5}/$out/out_${comp}.txt &