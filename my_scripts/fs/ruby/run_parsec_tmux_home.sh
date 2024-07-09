#!/bin/bash
if (($# < 1))
then
    echo "specify the sim size, level"
    exit 1
fi

SIZE=$1
# LEVEL=$2

declare -a bench=(
    "blackscholes" 
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
    # "vips" 
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

    # "xor_001"
    # "xor_002"
    "xor_003"
    "xor_004"

    "xor_011"
    "xor_012"
    "xor_013"
    "xor_014"

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

VER=0

for L2SIZE in ${l2[@]};do
    for CORE in ${core[@]};do
        for PROT in "${protocol[@]}"
        do
            for BEN in "${bench[@]}"
            do
                tmux has-session -t ${SIZE}${CORE}${PROT}_${L2SIZE}_ver${VER} 2>/dev/null
                if [ $? != 0 ]; then
                    # Set up your session
                    echo "create new session ${SIZE}${CORE}${PROT}_${L2SIZE}_ver${VER}"
                    echo "$BEN"
                    tmux new-session -d -s ${SIZE}${CORE}${PROT}_${L2SIZE}_ver${VER} -n $BEN 
                    tmux send-keys -t ${SIZE}${CORE}${PROT}_${L2SIZE}_ver${VER}:$BEN "python3 my_scripts/fs/ruby/run_parsec.py \
                    --benchmark ${BEN} \
                    --size ${SIZE} \
                    --core ${CORE} \
                    --protocol $PROT \
                    --use_anonymous_latency 1 \
                    --version $VER \
                    --home 1 \
                    --l2size ${L2SIZE}kB" C-m
                else
                    echo "$BEN"
                    tmux new-window -n $BEN -t ${SIZE}${CORE}${PROT}_${L2SIZE}_ver${VER}:
                    tmux send-keys -t ${SIZE}${CORE}${PROT}_${L2SIZE}_ver${VER}:$BEN "python3 my_scripts/fs/ruby/run_parsec.py \
                    --benchmark ${BEN} \
                    --size ${SIZE} \
                    --core ${CORE} \
                    --protocol $PROT \
                    --use_anonymous_latency 1 \
                    --version $VER \
                    --home 1 \
                    --l2size ${L2SIZE}kB" C-m
                fi
            done
        done
    done
done

echo "HOME: launched parsec full system ruby runs. VER ${VER}"

                    # --use_anonymous_latency 1 \
