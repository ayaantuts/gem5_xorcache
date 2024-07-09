#!/bin/bash
# this bash scripts uses util/checkpoint_fix_file.py on every spec benchmark in 
# dir: ckpt/spec2017/1c-2GB-valgrind/. This script only need to be run once.

ckpt_base_dir=ckpt/spec2017/1c-2GB-valgrind/
bench_dir=$(find ${ckpt_base_dir} -mindepth 1 -maxdepth 1 -type d -name "*.*")
num_bench=$(find ${ckpt_dir} -mindepth 1 -maxdepth 1 -type d | wc -l)
echo "number of benchmarks: ${num_bench}"
array=(500 503 508 510 525 531 549 548)

for bench in $bench_dir
do
    rem=${bench#$ckpt_base_dir}
    rem="${rem%%.*}"
    rem=$((rem))

    # search
    for i in "${array[@]}"
    do
        if [ "$i" -eq "$rem" ] ; then
            echo $rem
            echo "bench dir is ${bench}"
            python3 util/checkpoint_fix_file.py \
            -d ${bench} \
            -n ${rem}
        fi
    done


    
done