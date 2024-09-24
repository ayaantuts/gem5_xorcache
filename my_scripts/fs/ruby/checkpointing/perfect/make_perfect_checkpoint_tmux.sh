#!/bin/bash
# if (($# < 1))
# then
#     echo "specify the sim size, level"
#     exit 1
# fi


declare -a bench=(
    # "2d_convolution"
    # "dwt53"
    # "histogram_equalization"
    # "change-detection"
    # "debayer"
    "lucas-kanade"
)

declare -a protocol=(
    "no"
)

SET="ser"
CORE="1"
# SET="omp"
# CORE="4"

KERNELARG=""
# KERNELARG="--kernel_args memmap=512K@1M"


DISASSEMBLEARG=""
DISASSEMBLEARG="--disassemble 1"

for PROT in "${protocol[@]}"
do
    for BEN in "${bench[@]}"
    do
        tmux has-session -t perfect_${PROT} 2>/dev/null
        if [ $? != 0 ]; then
            # Set up your session
            echo "create new session perfect_${PROT}"
            echo "$BEN"
            tmux new-session -d -s perfect_${PROT} -n $BEN 
            tmux send-keys -t perfect_${PROT}:$BEN "python3 my_scripts/fs/ruby/checkpointing/perfect/make_perfect_checkpoint.py \
            --benchmark ${BEN} \
            --set ${SET} \
            --core ${CORE} \
            ${KERNELARG} \
            ${DISASSEMBLEARG} \
            --protocol $PROT" C-m
        else
            echo "$BEN"
            tmux new-window -n $BEN -t perfect_${PROT}:
            tmux send-keys -t perfect_${PROT}:$BEN "python3 my_scripts/fs/ruby/checkpointing/perfect/make_perfect_checkpoint.py \
            --benchmark ${BEN} \
            --set ${SET} \
            --core ${CORE} \
            ${KERNELARG} \
            ${DISASSEMBLEARG} \
            --protocol $PROT" C-m
        fi
    done
done

echo "launched perfect full system ruby runs. "

