#!/bin/bash
if [ $# -ne 2 ]
then
    echo Usage: ./run_spec_restore_dump_cache.sh comp_scheme spec_bench_num
    exit
fi

comp=$1
spec_bench_num=$2
gem5=/home/zhewen/repo/gem5-dev/gem5

# reading number of simpoints
ckpt=ckpt/spec2017/1c-2GB-valgrind/
ckpt_dir=$(find ${ckpt} -mindepth 1 -maxdepth 1 -type d -name "${spec_bench_num}*")
echo "ckpt dir is ${ckpt_dir}"
num_simpoint=$(find ${ckpt_dir} -mindepth 1 -maxdepth 1 -type d | wc -l)
echo "number of simpoints: ${num_simpoint}"

# specify debug flags below
# debug=\
# Decode,\
# CacheAll,ResponsePort,SyscallBase,\
# SnoopFilter,DMA,MemoryAccess,\
# MMU,PacketQueue,AddrRanges,TLB,TLBVerbose,\
# XBar,PageTableWalker,AnnotateAll,FmtFlag
# debug=CacheAll
debug=Checkpoint
# debug_flag="--debug-flags=${debug}"
debug_flag=""

for (( cur=0; cur<$num_simpoint; cur++ ))
do
    out=m5out_spec_dump_cache_2_to_1/${spec_bench_num}/$comp/${cur}
    mkdir -p $out

    nohup time ${gem5}/build/X86_test/gem5.opt \
    ${debug_flag} \
    -d ${gem5}/$out \
    ${gem5}/configs/example/gem5_library/checkpoints/simpoints-se-restore-spec-dump-cache.py \
    --l1d_size=64kB \
    --l1i_size=64kB \
    --l2_size=128kB \
    --comp=$comp \
    --bench_num=${spec_bench_num} \
    --cur_simpoint=${cur} \
    > ${gem5}/$out/restore_log.txt &
    # exit
done
