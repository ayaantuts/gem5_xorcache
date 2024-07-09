#!/bin/bash


declare -a run=(
    # 1
    # 2
    # 3
    # 4
    # 5
    # 6
    # 7
    # 8
    # 9
    # 10
    # 11
)

# NUMPROC=16
# NUMCORE=16
NUMPROC=4
NUMCORE=4
# FFINSTS=100000000 # 100M
FFINSTS=100000000000 # 100B
# FFINSTS=1000000000000 # 1000B
# FFINSTS=10000000000000 # 10000B

for RUN in ${run[@]};do
    tmux has-session -t spec_c${NUMCORE}_p${NUMPROC}_ff${FFINSTS} 2>/dev/null
    if [ $? != 0 ]; then
        # Set up your session
        echo "create new session spec_c${NUMCORE}_p${NUMPROC}_ff${FFINSTS}"
        echo "$RUN"
        tmux new-session -d -s spec_c${NUMCORE}_p${NUMPROC}_ff${FFINSTS} -n $RUN 
        tmux send-keys -t spec_c${NUMCORE}_p${NUMPROC}_ff${FFINSTS}:$RUN "python3 my_scripts/fs/ruby/checkpointing/spec2017/make_spec2017_checkpoint.py \
        --run ${RUN} \
        --numProcesses ${NUMPROC} \
        --protocol no \
        --fully_util 1 \
        --do_ff 1 \
        --fastforward_inst ${FFINSTS} \
        --core ${NUMCORE}" C-m
    else
        echo "$RUN"
        tmux new-window -n $RUN -t spec_c${NUMCORE}_p${NUMPROC}_ff${FFINSTS}:
        tmux send-keys -t spec_c${NUMCORE}_p${NUMPROC}_ff${FFINSTS}:$RUN "python3 my_scripts/fs/ruby/checkpointing/spec2017/make_spec2017_checkpoint.py \
        --run ${RUN} \
        --numProcesses ${NUMPROC} \
        --protocol no \
        --fully_util 1 \
        --do_ff 0 \
        --fastforward_inst ${FFINSTS} \
        --core ${NUMCORE}" C-m
    fi
done

echo "launched checkpoint gen full system ruby runs spec2017. "

