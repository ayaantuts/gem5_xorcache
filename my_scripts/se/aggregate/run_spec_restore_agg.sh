#!/bin/bash
if [ $# -ne 2 ]
then
    echo Usage: ./run_spec_restore_agg.sh comp_scheme id
    exit
fi

comp=$1
id=$2
gem5=/home/zhewen/repo/gem5-dev/gem5

# reading number of simpoints
ckpt=agg/
ckpt_dir=$(find ${ckpt} -mindepth 1 -maxdepth 1 -type d -name "${id}*")
echo "ckpt dir is ${ckpt_dir}"
num_simpoint=$(find ${ckpt_dir} -mindepth 1 -maxdepth 1 -type d | wc -l)
echo "number of aggregated simpoints: ${num_simpoint}"

# parse number of core
prefix="c"
suffix="_"
tmp=${id#*${suffix}}   # remove prefix ending in "c"
num_core=${id%${tmp}*}   # remove suffix starting with "_"
num_core=${num_core#*${prefix}}
num_core=${num_core%${suffix}}
echo "number of core: ${num_core}"

# specify debug flags below
debug=\
Decode,\
CacheAll,ResponsePort,SyscallBase,\
SnoopFilter,DMA,MemoryAccess,\
MMU,PacketQueue,AddrRanges,TLB,TLBVerbose,\
XBar,PageTableWalker,AnnotateAll,FmtFlag
# debug=CacheAll

for (( cur=0; cur<$num_simpoint; cur++ ))
do
    for (( x=0; x<$num_core; x++ ))
    do
        out=m5out_spec/${id}/$comp/set${cur}_core${x}
        mkdir -p $out

        nohup time ${gem5}/build/X86/gem5.opt \
        -d ${gem5}/$out \
        ${gem5}/configs/example/gem5_library/checkpoints/simpoints-se-restore-spec-agg.py \
        --comp=$comp \
        --bench_nums=${id} \
        --cur_simpoint=${cur} \
        --core_x=${x} \
        > ${gem5}/$out/restore_log.txt &
    done
    exit
    # --debug-flags=${debug} \
done
