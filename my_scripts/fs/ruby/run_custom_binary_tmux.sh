#!/bin/bash
# if (($# < 1))
# then
#     echo "specify the sim size, level"
#     exit 1
# fi

# SIZE=$1
# LEVEL=$2

declare -a bench=(
    "MGS"
    "MGSM"
    "MGSL"
    # "ws450kb"
    # "ws512kb"
    # "ws1024kb"
    # "ws2048kb"
)

core=(
    16
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

    # "msi_nine_xor_bdi_map"
    # "msi_nine_noxor_bdi_map"
    "msi_nine_xor_nobdi_map"
    # "msi_nine_noxor_nobdi_map"
)

# l2=(
#     # 64
#     # 128
#     256
#     512
# )

# line_entropy=""
line_entropy="--record_line_level_entropy"

debug=""
# debug="--flags ProtocolTrace,RubyGenerated,RubyDataChange,RubyEntropyProfiler"

# for L2SIZE in ${l2[@]};do
    for CORE in ${core[@]};do
        for PROT in "${protocol[@]}"
        do
            for BEN in "${bench[@]}"
            do
                tmux has-session -t micro${CORE}${PROT} 2>/dev/null
                if [ $? != 0 ]; then
                    # Set up your session
                    echo "create new session micro${CORE}${PROT}"
                    echo "$BEN"
                    tmux new-session -d -s micro${CORE}${PROT} -n $BEN 
                    tmux send-keys -t micro${CORE}${PROT}:$BEN "python3 my_scripts/fs/ruby/run_custom_binary.py \
                    --benchmark ${BEN} \
                    --suffix gem5 \
                    --core ${CORE} \
                    $line_entropy \
                    --protocol $PROT $debug" C-m
                else
                    echo "$BEN"
                    tmux new-window -n $BEN -t micro${CORE}${PROT}:
                    tmux send-keys -t micro${CORE}${PROT}:$BEN "python3 my_scripts/fs/ruby/run_custom_binary.py \
                    --benchmark ${BEN} \
                    --suffix gem5 \
                    --core ${CORE} \
                    $line_entropy \
                    --protocol $PROT $debug" C-m
                fi
            done
        done
    done
# done

echo "launched custom binary full system ruby runs."