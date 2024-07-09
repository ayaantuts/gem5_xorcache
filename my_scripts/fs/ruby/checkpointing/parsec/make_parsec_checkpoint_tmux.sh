#!/bin/bash

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
    4
    # 16
    # 64
)

declare -a protocol=(
    "no"
    # "hammer"
)

# debug="--flags RubyCacheUtil"
# debug="--flags RubyCacheTrace,Checkpoint"
debug=""



for CORE in ${core[@]};do
    for PROT in "${protocol[@]}"
    do
        for BEN in "${bench[@]}"
        do
            tmux has-session -t ckpt_parsec_fs_${SIZE}${CORE}${PROT} 2>/dev/null
            if [ $? != 0 ]; then
                # Set up your session
                echo "create new session ckpt_parsec_fs_${SIZE}${CORE}${PROT}"
                echo "$BEN"
                tmux new-session -d -s ckpt_parsec_fs_${SIZE}${CORE}${PROT} -n $BEN 
                tmux send-keys -t ckpt_parsec_fs_${SIZE}${CORE}${PROT}:$BEN "python3 my_scripts/fs/ruby/checkpointing/parsec/make_parsec_checkpoint.py \
                --benchmark ${BEN} \
                --size ${SIZE} \
                --core ${CORE} \
                --protocol $PROT $debug" C-m
            else
                echo "$BEN"
                tmux new-window -n $BEN -t ckpt_parsec_fs_${SIZE}${CORE}${PROT}:
                tmux send-keys -t ckpt_parsec_fs_${SIZE}${CORE}${PROT}:$BEN "python3 my_scripts/fs/ruby/checkpointing/parsec/make_parsec_checkpoint.py \
                --benchmark ${BEN} \
                --size ${SIZE} \
                --core ${CORE} \
                --protocol $PROT $debug" C-m
            fi
        done
    done
done

echo "launched parsec full system ruby gen ckpt."

