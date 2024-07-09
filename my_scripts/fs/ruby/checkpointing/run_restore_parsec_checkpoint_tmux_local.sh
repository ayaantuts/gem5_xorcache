#!/bin/bash
# not working
if (($# < 1))
then
    echo "specify the sim size"
    exit 1
fi

SIZE=$1
# LEVEL=$2

declare -a bench=(
    # "blackscholes" 
    # "bodytrack" 
    # "canneal" 
    # "dedup" 
    # "facesim" 
    # "ferret" 
    # "fluidanimate" 
    # "freqmine" 
    # "raytrace" 
    # "streamcluster" 
    # "swaptions" 
    "vips" 
    # "x264"
)

core=(
    # 2 
    # 4
    16
    # 64
)

declare -a protocol=(
    # "baseline" 
    # "noisy" 
    # "decoupled" 
    # "compress"
    # "dedup" 
    # "bdixor"
    "msi"
    "msi_nine"

    # "xor_001"
    # "xor_002"
    # "xor_003"
    # "xor_004"

    # "xor_011"
    # "xor_012"
    # "xor_013"
    # "xor_014"

    # "xor_101"
    # "xor_102"
    # "xor_103"
    # "xor_104"

    # "xor_111"
    # "xor_112"
    # "xor_113"
    # "xor_114"
)

l2=(
    64
    # 128
    # 256
    # 512
    # 1024
    # 2048
)

debug="--flags Checkpoint"
# debug="--flags Checkpoint,RubyCacheUtil"
# debug="--flags Checkpoint,RubyCacheUtil,RubyCacheUtilBase"
# debug=""


for L2SIZE in ${l2[@]};do
    for CORE in ${core[@]};do
        for PROT in "${protocol[@]}"
        do
            for BEN in "${bench[@]}"
            do
                tmux has-session -t restore_${SIZE}${CORE}${PROT}_${L2SIZE} 2>/dev/null
                if [ $? != 0 ]; then
                    # Set up your session
                    echo "create new session restore_${SIZE}${CORE}${PROT}_${L2SIZE}"
                    echo "$BEN"
                    tmux new-session -d -s restore_${SIZE}${CORE}${PROT}_${L2SIZE} -n $BEN 
                    tmux send-keys -t restore_${SIZE}${CORE}${PROT}_${L2SIZE}:$BEN "python3 my_scripts/fs/ruby/checkpointing/run_restore_parsec_checkpoint.py \
                    --benchmark ${BEN} \
                    --size ${SIZE} \
                    --core ${CORE} \
                    --protocol $PROT \
                    --use_anonymous_latency 1 \
                    --ckpt_search_path /home/happyresearch/Dropbox/result/coherence/m5out \
                    --l2size ${L2SIZE}kB $debug" C-m
                else
                    echo "$BEN"
                    tmux new-window -n $BEN -t restore_${SIZE}${CORE}${PROT}_${L2SIZE}:
                    tmux send-keys -t restore_${SIZE}${CORE}${PROT}_${L2SIZE}:$BEN "python3 my_scripts/fs/ruby/checkpointing/run_restore_parsec_checkpoint.py \
                    --benchmark ${BEN} \
                    --size ${SIZE} \
                    --core ${CORE} \
                    --protocol $PROT \
                    --use_anonymous_latency 1 \
                    --ckpt_search_path /home/happyresearch/Dropbox/result/coherence/m5out \
                    --l2size ${L2SIZE}kB $debug" C-m
                fi
            done
        done
    done
done

echo "launched parsec full system ruby restore ckpt."

