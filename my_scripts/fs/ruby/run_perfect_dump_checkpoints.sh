#!/bin/bash
# if (($# < 1))
# then
#     echo "specify the sim size, level"
#     exit 1
# fi


declare -a bench=(
    # "2d_convolution"
    # "dwt53"
    "histogram_equalization"
    # "change-detection"
    # "debayer"
    # "lucas-kanade"
)

declare -a protocol=(
    "dump"
)

declare -a shift=(
    0
    # 1
    # 2
    # 3
    # 4
    # 5
    # 6
    # 7
    # 15
    # 31
)

CACHECFG="skylake"
# CACHECFG="realistic"


for SHIFT in ${shift[@]};do
    for PROT in "${protocol[@]}"
    do
        for BEN in "${bench[@]}"
        do
            tmux has-session -t ${PROT}${SHIFT}_${CACHECFG} 2>/dev/null
            if [ $? != 0 ]; then
                # Set up your session
                echo "create new session ${PROT}${SHIFT}_${CACHECFG}"
                echo "$BEN"
                tmux new-session -d -s ${PROT}${SHIFT}_${CACHECFG} -n $BEN 
                tmux send-keys -t ${PROT}${SHIFT}_${CACHECFG}:$BEN "python3 my_scripts/fs/ruby/run_perfect_dump_checkpoints.py \
                --benchmark ${BEN} \
                --protocol $PROT \
                --cachecfg ${CACHECFG} \
                --index_bits_shift ${SHIFT}" C-m
            else
                echo "$BEN"
                tmux new-window -n $BEN -t ${PROT}${SHIFT}_${CACHECFG}:
                tmux send-keys -t ${PROT}${SHIFT}_${CACHECFG}:$BEN "python3 my_scripts/fs/ruby/run_perfect_dump_checkpoints.py \
                --benchmark ${BEN} \
                --protocol $PROT \
                --cachecfg ${CACHECFG} \
                --index_bits_shift ${SHIFT}" C-m
            fi
        done
    done
done

echo "launched checkpoint dump shift full system ruby runs. "

