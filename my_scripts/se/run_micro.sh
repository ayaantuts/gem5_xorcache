#!/bin/bash
if [ $# -lt 3 ]
then
    echo "Usage: ./run_micro.sh comp_scheme path profile_mode flags(optional)"
    exit
fi

comp=$1
path=$2
profile_mode=$3
cpt_flag=""
out=m5out_micro/$comp
mkdir -p $out

if [ ${profile_mode} -eq 1 ]
then
    echo "profile mode"
    debug=PseudoInst

    debug_flag="--debug-flags=${debug}"
    debug_interval=""

elif [ ${profile_mode} -eq 0 ]
then
    echo "normal mode"
    # specify debug flags below
    # debug=CacheAll,ResponsePort,SyscallBase,\
    # SnoopFilter,DRAM,DMA,MemoryAccess,\
    # MMU,PacketQueue,AddrRanges,TLB,TLBVerbose,\
    # XBar,PageTableWalker,AnnotateAll,FmtFlag

    debug=TwinTags,BaseTags,Cache,CacheVerbose,TwinLRU,CacheBlk,PseudoInst

    begin_tick=532004463
    end_tick=532658142

    debug_flag="--debug-flags=${debug}"
    debug_interval="--debug-start=${begin_tick} \
        --debug-end=${end_tick}"

elif [ ${profile_mode} -eq 2 ]
then
    echo "full run debug mode"
    debug=$4

    debug_flag="--debug-flags=${debug}"
    debug_interval=""

elif  [ ${profile_mode} -eq 3 ]
then
    echo "interval debug mode"
    debug=TwinTags,BaseTags,Cache,CacheVerbose,TwinLRU,CacheBlk,PseudoInst
    #CacheTags,
    begin_tick=$4
    end_tick=$5

    debug_flag="--debug-flags=${debug}"
    debug_interval="--debug-start=${begin_tick} \
        --debug-end=${end_tick}"

elif  [ ${profile_mode} -eq 4 ]
then
    echo "direct run mode"

    debug_flag=""
    debug_interval=""

elif [ ${profile_mode} -eq 5 ]
then
    echo "checkpointing mode"

    debug=Checkpoint
    debug_flag="--debug-flags=${debug}"
    debug_interval=""
    cpt_flag="--cpt_path=${out}"
else
    echo "Error: unknow profile option, only 0/1 accepted."
    exit 1
fi

nohup time build/X86_test/gem5.opt \
${debug_flag} \
${debug_interval} \
-d $out \
configs/example/gem5_library/x86-custombinary.py \
--l1d_size=64kB \
--l1i_size=64kB \
--l2_size=128kB \
--comp=$comp \
--path=$path \
$cpt_flag \
> $out/out_${comp}.txt &
