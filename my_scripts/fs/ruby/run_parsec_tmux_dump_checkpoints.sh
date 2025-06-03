#!/bin/bash
if (($# < 1))
then
    echo "specify the sim size"
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
    4
    # 16
    # 64
)

declare -a protocol=(
    # "baseline" 
    # "noisy" 
    # "decoupled" 
    # "compress"
    # "dedup" 
    # "bdixor"
    # "msi"
    "dump"
)


CACHECFG="skylake"
# CACHECFG="realistic"

VER=0

for CORE in ${core[@]};do
    for PROT in "${protocol[@]}"
    do
        for BEN in "${bench[@]}"
        do
            tmux has-session -t ckpt_${SIZE}${CORE}${PROT}_ver${VER}_${CACHECFG} 2>/dev/null
            if [ $? != 0 ]; then
                # Set up your session
                echo "create new session ckpt_${SIZE}${CORE}${PROT}_ver${VER}_${CACHECFG}"
                echo "$BEN"
                tmux new-session -d -s ckpt_${SIZE}${CORE}${PROT}_ver${VER}_${CACHECFG} -n $BEN 
                tmux send-keys -t ckpt_${SIZE}${CORE}${PROT}_ver${VER}_${CACHECFG}:$BEN "python3 my_scripts/fs/ruby/run_parsec_dump_checkpoints.py \
                --benchmark ${BEN} \
                --size ${SIZE} \
                --core ${CORE} \
                --protocol $PROT \
                --version $VER \
                --cachecfg ${CACHECFG}" C-m
            else
                echo "$BEN"
                tmux new-window -n $BEN -t ckpt_${SIZE}${CORE}${PROT}_ver${VER}_${CACHECFG}:
                tmux send-keys -t ckpt_${SIZE}${CORE}${PROT}_ver${VER}_${CACHECFG}:$BEN "python3 my_scripts/fs/ruby/run_parsec_dump_checkpoints.py \
                --benchmark ${BEN} \
                --size ${SIZE} \
                --core ${CORE} \
                --protocol $PROT \
                --version $VER \
                --cachecfg ${CACHECFG}" C-m
            fi
        done
    done
done

echo "launched parsec full system ruby runs. VER ${VER}"

                    # --use_anonymous_latency 1 \
