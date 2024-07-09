#!/bin/bash
# not working
if (($# < 2))
then
    echo "specify the sim size, do warmup"
    exit 1
elif (($# == 3))
then
    HOMEARG=$3
else
    HOMEARG=0
fi

SIZE=$1
WARMUP=$2
# LEVEL=$2

if [[ $WARMUP -eq 1 ]]
then
  warm="--do_warmup 1"
elif [[ $WARMUP -eq 0 ]]
then
  warm="--do_warmup 0"
else
  echo "unknown warmup option"
fi

if [[ $HOMEARG -eq 1 ]]
then
  homearg="--home 1"
elif [[ $HOMEARG -eq 0 ]]
then
  homearg="--home 0"
else
  echo "unknown home option"
fi

declare -a bench=(
    # "blackscholes" 
    # "bodytrack" 
    # "canneal" 
    "dedup" 
    "facesim" 
    "ferret" 
    # "fluidanimate" 
    "freqmine" 
    # "raytrace" 
    "streamcluster" 
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
    # "msi_nine"
    "msi_nine_noxor"
    # "msi_nine_xor"

)

l2=(
    64
    # 128
    # 256
    # 512
    # 1024
    # 2048
)

# debug="--flags Checkpoint"
# debug="--flags Checkpoint,RubyCacheUtil"
# debug="--flags Checkpoint,RubyCacheUtil,RubyCacheUtilBase"
debug=""
# debug="--begin 140979363383132 --end 140979363384133 --flags ProtocolTrace,RubyGenerated"

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
                    --ckpt_search_path /home/zhewen/Dropbox/result/coherence/m5out \
                    --l2size ${L2SIZE}kB $debug $warmup $homearg" C-m
                else
                    echo "$BEN"
                    tmux new-window -n $BEN -t restore_${SIZE}${CORE}${PROT}_${L2SIZE}:
                    tmux send-keys -t restore_${SIZE}${CORE}${PROT}_${L2SIZE}:$BEN "python3 my_scripts/fs/ruby/checkpointing/run_restore_parsec_checkpoint.py \
                    --benchmark ${BEN} \
                    --size ${SIZE} \
                    --core ${CORE} \
                    --protocol $PROT \
                    --use_anonymous_latency 1 \
                    --ckpt_search_path /home/zhewen/Dropbox/result/coherence/m5out \
                    --l2size ${L2SIZE}kB $debug $warmup $homearg" C-m
                fi
            done
        done
    done
done

echo "launched parsec full system ruby restore ckpt."

