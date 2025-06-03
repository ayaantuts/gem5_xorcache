#!/bin/bash
if (($# < 1))
then
    echo "not using kvm"
    KVM_FLAG=""
else
    KVM=$1
    if [ $KVM -eq 1 ]; then
        echo "using kvm"
        KVM_FLAG="--mode kvm"
    else
        echo "not using kvm"
        KVM_FLAG=""
    fi
fi

# NUMCKPT=10
NUMCKPT=100

declare -a run=(
    1
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

CACHECFG="skylake"
# CACHECFG="realistic"

for RUN in ${run[@]};do
    tmux has-session -t spec_c${NUMCORE}_p${NUMPROC}_${CACHECFG} 2>/dev/null
    if [ $? != 0 ]; then
        # Set up your session
        echo "create new session spec_c${NUMCORE}_p${NUMPROC}_${CACHECFG}"
        echo "$RUN"
        tmux new-session -d -s spec_c${NUMCORE}_p${NUMPROC}_${CACHECFG} -n $RUN 
        tmux send-keys -t spec_c${NUMCORE}_p${NUMPROC}_${CACHECFG}:$RUN "python3 my_scripts/fs/ruby/run_spec2017_dump_checkpoints.py \
        --run ${RUN} \
        --numProcesses ${NUMPROC} \
        --fully_util 1 \
        --core ${NUMCORE} \
        --num_checkpoint ${NUMCKPT} \
        --cachecfg ${CACHECFG} \
        --flags RubyProfiler ${KVM_FLAG}" C-m
    else
        echo "$RUN"
        tmux new-window -n $RUN -t spec_c${NUMCORE}_p${NUMPROC}_${CACHECFG}:
        tmux send-keys -t spec_c${NUMCORE}_p${NUMPROC}_${CACHECFG}:$RUN "python3 my_scripts/fs/ruby/run_spec2017_dump_checkpoints.py \
        --run ${RUN} \
        --numProcesses ${NUMPROC} \
        --fully_util 1 \
        --core ${NUMCORE} \
        --num_checkpoint ${NUMCKPT} \
        --cachecfg ${CACHECFG} \
        --flags RubyProfiler ${KVM_FLAG}" C-m
    fi
done

echo "launched checkpoint dump full system ruby runs spec2017. "

