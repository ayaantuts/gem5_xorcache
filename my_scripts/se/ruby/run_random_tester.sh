#!/bin/bash
if (($# < 1))
then
    echo "specify the frequency"
    exit 1
fi

FREQ=$1
PROT=dedup

for CHECKS in 1000000000
do
    for CORE in 1 2 3 4 5 6 7 8 16 32 64
    do
        python3 my_scripts/se/ruby/run_random_tester.py --checks $CHECKS --core $CORE --freq $FREQ --protocol $PROT --mute &
    done
done

echo "launched all $PROT random tester tests."