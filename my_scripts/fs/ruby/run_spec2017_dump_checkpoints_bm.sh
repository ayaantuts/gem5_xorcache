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

benchmark="525.x264_r"

NUMCORE=2

python3 my_scripts/fs/ruby/run_spec2017_dump_checkpoints.py \
    --fully_util 1 \
    --core ${NUMCORE} \
    --benchmark ${benchmark} \
    --flags RubyProfiler ${KVM_FLAG}

echo "lanched run for benchmark ${benchmark}"