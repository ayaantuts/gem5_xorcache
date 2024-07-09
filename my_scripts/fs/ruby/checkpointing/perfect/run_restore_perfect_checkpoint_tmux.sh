#!/bin/bash
if (($# < 1))
then
    echo "specify the config set number"
    exit 1
fi
host=$(hostname)
if [ "$host" = "zhewen-MS-7D25" ]; then
    home="--home 1"
else
    home=""
fi

declare -a bench=(
    "2d_convolution"
    # "dwt53"
    # "histogram_equalization"
    # "change-detection"
    # "debayer"
    # "lucas-kanade"
)

core=(
    # 1
    4
)

# set="ser"
set="omp"

suite="all"

declare -a protocol=(
     "msi_nine_xor_bdi_map"
    #  "msi_nine_noxor_bdi_map"
    #  "msi_nine_xor_nobdi_map"
    #  "msi_nine_noxor_nobdi_map"

    # "msi_exc_nobdi"
    # "msi_exc_bdi"
)

ratio=2.5
# ratio=2
# ratio=1
ratio_str=${ratio/./_}

# ooo="--ooo"
# OOO=1
ooo="--no-ooo"
OOO=0

L2_DATA_SEGEMENT_SIZE=8
L2_TRANSITIONS_PER_CYCLE=1024
L2_DATA_REGIONS=32
INDEX_SHIFT_BITS=3

case $1 in
  1) echo "oppurtunistic"
    xor_policy="oppurtunistic"
    xor_folding_scheme=0
    folding="bytelabel"
    L2_MAP_BITS=8
    L2_NUM_MAPTABLE_SETS=256
    L2_LIST_CAPACITY=1
    ;;
  2) echo "0-bytelabel, 6b, 64x1 =>64x10b=0.078KiB (Sufficient)"
    xor_policy="synergy"
    xor_folding_scheme=0
    folding="bytelabel"
    L2_MAP_BITS=6
    L2_NUM_MAPTABLE_SETS=64
    L2_LIST_CAPACITY=1
    ;;
  3) echo "0-bytelabel, 7b, 128x1 =>128x10b=0.16KiB (Sufficient)"
    xor_policy="synergy"
    xor_folding_scheme=0
    folding="bytelabel"
    L2_MAP_BITS=7
    L2_NUM_MAPTABLE_SETS=128
    L2_LIST_CAPACITY=1
    ;;
  4) echo "0-bytelabel, 8b, 256x1 =>256x10b=0.31KiB (Sufficient)"
    xor_policy="synergy"
    xor_folding_scheme=0
    folding="bytelabel"
    L2_MAP_BITS=8
    L2_NUM_MAPTABLE_SETS=256
    L2_LIST_CAPACITY=1
    ;;

  5) echo "0-bytelabel, 10b, 1024x1 =>1024x10b=1.25KiB (Sufficient)"
    xor_policy="synergy"
    xor_folding_scheme=0
    folding="bytelabel"
    L2_MAP_BITS=10
    L2_NUM_MAPTABLE_SETS=1024
    L2_LIST_CAPACITY=1
    ;;

  6) echo "0-bytelabel, 12b, 4096x1 =>4096x10b=5KiB (L,Sufficient)"
    xor_policy="synergy"
    xor_folding_scheme=0
    folding="bytelabel"
    L2_MAP_BITS=12
    L2_NUM_MAPTABLE_SETS=4096
    L2_LIST_CAPACITY=1
    ;;

  7) echo "1-sparsebytelabel, 6b, 64x1 =>64x10b=0.078KiB (Sufficient)"
    xor_policy="synergy"
    xor_folding_scheme=1
    folding="sparsebytelabel"
    L2_MAP_BITS=6
    L2_NUM_MAPTABLE_SETS=64
    L2_LIST_CAPACITY=1
    ;;
  8) echo "1-sparsebytelabel, 7b, 128x1 =>128x10b=0.16KiB (Sufficient)"
    xor_policy="synergy"
    xor_folding_scheme=1
    folding="sparsebytelabel"
    L2_MAP_BITS=7
    L2_NUM_MAPTABLE_SETS=128
    L2_LIST_CAPACITY=1
    ;;
  9) echo "1-sparsebytelabel, 8b, 256x1 =>256x10b=0.31KiB (Sufficient)"
    xor_policy="synergy"
    xor_folding_scheme=1
    folding="sparsebytelabel"
    L2_MAP_BITS=8
    L2_NUM_MAPTABLE_SETS=256
    L2_LIST_CAPACITY=1
    ;;
  10) echo "1-sparsebytelabel, 10b, 1024x1 =>1024x10b=1.25KiB (Sufficient)"
    xor_policy="synergy"
    xor_folding_scheme=1
    folding="sparsebytelabel"
    L2_MAP_BITS=10
    L2_NUM_MAPTABLE_SETS=1024
    L2_LIST_CAPACITY=1
    ;;
  11) echo "1-sparsebytelabel, 12b, 4096x1 =>4096x10b=5KiB (L,Sufficient)"
    xor_policy="synergy"
    xor_folding_scheme=1
    folding="sparsebytelabel"
    L2_MAP_BITS=12
    L2_NUM_MAPTABLE_SETS=4096
    L2_LIST_CAPACITY=1
    ;;
  
  *) echo "ERROR: this option has not been configured"
    exit 1
  ;; 
esac


# xor_folding_scheme=4
# folding="Blf"
# xor_folding_scheme=5
# folding="xBm"

line_entropy=""
# line_entropy="--record_line_level_entropy"


l2=(
    # 32
    64
    # 128
    # 256
    # 512
    # 1024
    # 2048
)

debug=""
# debug="--flags RubyDataTransformation"
# debug="--flags ProtocolTrace,RubySlicc,RubyGenerated"
# debug="--flags ProtocolTrace"
# debug="--begin 18208298911130 --end 18208299011131 --flags ProtocolTrace,RubySlicc,RubyGenerated"
# debug="--flags RubyDataTransformation,RubyAssociativeMapTable,RubyDataCluster"

# debug="--begin 18548039648069 --end 18548039658070 --flags ProtocolTrace,RubySlicc,RubyGenerated,RubyReplacement,RubyDataUpdate,RubyCacheFASector" #dwt


for L2SIZE in ${l2[@]};do
    for CORE in ${core[@]};do
        for PROT in "${protocol[@]}"
        do
            for BEN in "${bench[@]}"
            do
                if [ "$PROT" = "msi_nine_noxor_nobdi_map" ]; then
                    session_name=restore_perfect_${SIZE}${CORE}${PROT}_${L2SIZE}_O${OOO}_${L2_TRANSITIONS_PER_CYCLE}t
                    L2_DATA_REGIONS_USED=1
                    L2_DATA_SEGEMENT_SIZE_USED=1
                elif [ "$PROT" = "msi_nine_noxor_bdi_map" ]; then
                    L2_DATA_REGIONS_USED=$L2_DATA_REGIONS
                    L2_DATA_SEGEMENT_SIZE_USED=$L2_DATA_SEGEMENT_SIZE
                    session_name=restore_perfect_${SIZE}${CORE}${PROT}_${L2SIZE}_O${OOO}_r${ratio_str}_${L2_TRANSITIONS_PER_CYCLE}t_seg${L2_DATA_SEGEMENT_SIZE_USED}_${L2_DATA_REGIONS_USED}region
                elif [ "$PROT" = "msi_nine_xor_nobdi_map" ]; then
                    L2_DATA_REGIONS_USED=1
                    L2_DATA_SEGEMENT_SIZE_USED=1
                    session_name=restore_perfect_${SIZE}${CORE}${PROT}_${L2SIZE}_O${OOO}_r${ratio_str}_${L2_TRANSITIONS_PER_CYCLE}t_${L2_MAP_BITS}mapb_${L2_NUM_MAPTABLE_SETS}x${L2_LIST_CAPACITY}_${folding}_${xor_policy}
                elif [ "$PROT" = "msi_nine_xor_bdi_map" ]; then
                    L2_DATA_REGIONS_USED=$L2_DATA_REGIONS
                    L2_DATA_SEGEMENT_SIZE_USED=$L2_DATA_SEGEMENT_SIZE
                    session_name=restore_perfect_${SIZE}${CORE}${PROT}_${L2SIZE}_O${OOO}_r${ratio_str}_${L2_TRANSITIONS_PER_CYCLE}t_seg${L2_DATA_SEGEMENT_SIZE_USED}_${L2_DATA_REGIONS_USED}region_${L2_MAP_BITS}mapb_${L2_NUM_MAPTABLE_SETS}x${L2_LIST_CAPACITY}_${folding}_${xor_policy}_${INDEX_SHIFT_BITS}shift
                elif [ "$PROT" = "msi_exc_nobdi" ]; then
                    L2_DATA_REGIONS_USED=1
                    L2_DATA_SEGEMENT_SIZE_USED=1
                    session_name=restore_perfect_${SIZE}${CORE}${PROT}_${L2SIZE}_O${OOO}_${L2_TRANSITIONS_PER_CYCLE}t
                elif [ "$PROT" = "msi_exc_bdi" ]; then
                    L2_DATA_REGIONS_USED=$L2_DATA_REGIONS
                    L2_DATA_SEGEMENT_SIZE_USED=$L2_DATA_SEGEMENT_SIZE
                    session_name=restore_perfect_${SIZE}${CORE}${PROT}_${L2SIZE}_O${OOO}_r${ratio_str}_${L2_TRANSITIONS_PER_CYCLE}t_seg${L2_DATA_SEGEMENT_SIZE_USED}_${L2_DATA_REGIONS_USED}region
                
                else
                    echo "wrong protocol"
                    exit 1
                fi

                tmux has-session -t $session_name 2>/dev/null
                if [ $? != 0 ]; then
                    # Set up your session
                    echo "create new session $session_name"
                    echo "$BEN"
                    tmux new-session -d -s $session_name -n $BEN 
                    tmux send-keys -t $session_name:$BEN "python3 my_scripts/fs/ruby/checkpointing/perfect/run_restore_perfect_checkpoint.py \
                    --benchmark ${BEN} \
                    --core ${CORE} \
                    --set ${set} \
                    --protocol $PROT \
                    --use_anonymous_latency 1 \
                    --l2factor $ratio \
                    --ckpt_search_path /home/$USER/Dropbox/result/coherence/m5out \
                    $ooo \
                    --l2_data_segment_size ${L2_DATA_SEGEMENT_SIZE_USED} \
                    --l2_data_regions ${L2_DATA_REGIONS_USED} \
                    --l2_transitions_per_cycle ${L2_TRANSITIONS_PER_CYCLE} \
                    --l2_map_bits ${L2_MAP_BITS} \
                    --l2_num_maptable_set ${L2_NUM_MAPTABLE_SETS} \
                    --l2_list_capacity ${L2_LIST_CAPACITY} \
                    $line_entropy \
                    --xor_folding_scheme $xor_folding_scheme \
                    $home \
                    --xor_policy $xor_policy \
                    --suite_name $suite \
                    --index_bits_shift ${INDEX_SHIFT_BITS} \
                    --l2size ${L2SIZE}kB $debug" C-m
                else
                    echo "$BEN"
                    tmux new-window -n $BEN -t $session_name:
                    tmux send-keys -t $session_name:$BEN "python3 my_scripts/fs/ruby/checkpointing/perfect/run_restore_perfect_checkpoint.py \
                    --benchmark ${BEN} \
                    --core ${CORE} \
                    --set ${set} \
                    --protocol $PROT \
                    --use_anonymous_latency 1 \
                    --l2factor $ratio \
                    --ckpt_search_path /home/$USER/Dropbox/result/coherence/m5out \
                    $ooo \
                    --l2_data_segment_size ${L2_DATA_SEGEMENT_SIZE_USED} \
                    --l2_data_regions ${L2_DATA_REGIONS_USED} \
                    --l2_transitions_per_cycle ${L2_TRANSITIONS_PER_CYCLE} \
                    --l2_map_bits ${L2_MAP_BITS} \
                    --l2_num_maptable_set ${L2_NUM_MAPTABLE_SETS} \
                    --l2_list_capacity ${L2_LIST_CAPACITY} \
                    $line_entropy \
                    --xor_folding_scheme $xor_folding_scheme \
                    $home \
                    --xor_policy $xor_policy \
                    --suite_name $suite \
                    --index_bits_shift ${INDEX_SHIFT_BITS} \
                    --l2size ${L2SIZE}kB $debug" C-m
                fi
            done
        done
    done
done

echo "launched perfect full system ruby restore ckpt. "

