#!/bin/bash
if (($# < 1))
then
    echo "specify the config set number"
    exit 1
fi
fast=""
# fast="--fast 1"
host=$(hostname)
if [ "$host" = "zhewen-MS-7D25" ]; then
    home="--home 1"
else
    home=""
fi
declare -a bench=(
    # "2d_convolution"
    # "dwt53"
    "histogram_equalization"
    # "change-detection"
    # "debayer"
    # "lucas-kanade"
)

# tagptr=""
# TAGPTR="TAGPTR"

tagptr="--no-tagptr"
TAGPTR="NOTAGPTR"

llclat=""
LLCLAT="_"

# llclat="--llc_lat 1"
# LLCLAT="_LLCLAT1"

# llclat="--llc_lat 10"
# LLCLAT="_LLCLAT10"

# llclat="--llc_lat 100"
# LLCLAT="_LLCLAT100"

core=(
    # 1
    4
)

# set="ser"
set="omp"

suite="all"

comparison="isoperf"
# comparison="isoarea"

declare -a protocol=(
    #  "msi_nine_xor_bdi_map"
    #  "msi_nine_noxor_bdi_map"
    #  "msi_nine_xor_nobdi_map"
    #  "msi_nine_noxor_nobdi_map"

    #  "msi_nine_xor_bdi_map3"
     "msi_nine_xor_thesaurus_map3"

    #  "msi_nine_noxor_bdi_map3"
    #  "msi_nine_noxor_thesaurus_map3"

    #  "msi_nine_xor_nobdi_map3"

    #  "msi_nine_noxor_nobdi_map3"
    #  "mesi3"

    # "msi_exc_nobdi"
    # "msi_exc_bdi"

    # "msi_exc3"
    # "msi_exc_bdi3"

    # "mesi2_inc_nobdi"
    # "mesi2_inc_bdi"
)

ratio=2.5
# ratio=1.5
# ratio=2
# ratio=1
# ratio=1.3
ratio_str=${ratio/./_}

# ooo="--ooo"
# OOO=1
ooo="--no-ooo"
OOO=0

L2_DATA_SEGEMENT_SIZE=8
L2_TRANSITIONS_PER_CYCLE=1024
L2_DATA_REGIONS=64

INDEX_SHIFT_BITS=0

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


cachecfg=(
    # "skylake"
    "realistic"
)

debug=""
# debug="--flags RubyThesaurus"
# debug="--flags RubySlicc,RubyGenerated"
# debug="--flags RubySlicc,RubyGenerated --begin 19280132038853 --end 19280132048854"
################################## approxilyzer trace gen ##################################
# debug="--flags ExecEnable,ExecUser,ExecEffAddr,ExecMacro --dfile dump_micro.gz"
# debug="--flags MemoryAccess --dfile mem_dump.gz"

# DISASSEMBLE=""
# DISASSEMBLE="--disassemble 1"
################################## approxilyzer trace gen ##################################

for CFG in ${cachecfg[@]};do
    for CORE in ${core[@]};do
        for PROT in "${protocol[@]}"
        do
            for BEN in "${bench[@]}"
            do
                if [[ "$PROT" = "mesi3" ]]; then
                    session_name=restore_perfect_${comparison}_${SIZE}${CORE}${PROT}_${CFG}_O${OOO}_${L2_TRANSITIONS_PER_CYCLE}t
                    L2_DATA_REGIONS_USED=1
                    L2_DATA_SEGEMENT_SIZE_USED=64
                elif [[ "$PROT" = "msi_nine_noxor_nobdi_map" || "$PROT" = "msi_nine_noxor_nobdi_map3" ]]; then
                    session_name=restore_perfect_${comparison}_${SIZE}${CORE}${PROT}_${CFG}_O${OOO}_${L2_TRANSITIONS_PER_CYCLE}t
                    L2_DATA_REGIONS_USED=1
                    L2_DATA_SEGEMENT_SIZE_USED=64
                elif [[ "$PROT" = "msi_nine_noxor_bdi_map" || "$PROT" = "msi_nine_noxor_bdi_map3"  || "$PROT" = "msi_nine_noxor_thesaurus_map3" ]]; then
                    L2_DATA_REGIONS_USED=$L2_DATA_REGIONS
                    L2_DATA_SEGEMENT_SIZE_USED=$L2_DATA_SEGEMENT_SIZE
                    session_name=restore_perfect_${comparison}_${SIZE}${CORE}${PROT}_${CFG}_O${OOO}_r${ratio_str}_${L2_TRANSITIONS_PER_CYCLE}t_seg${L2_DATA_SEGEMENT_SIZE_USED}_${L2_DATA_REGIONS_USED}region
                elif [[ "$PROT" = "msi_nine_xor_nobdi_map" || "$PROT" = "msi_nine_xor_nobdi_map3" ]]; then
                    L2_DATA_REGIONS_USED=1
                    L2_DATA_SEGEMENT_SIZE_USED=64
                    session_name=restore_perfect_${comparison}_${SIZE}${CORE}${PROT}_${CFG}_O${OOO}_r${ratio_str}_${L2_TRANSITIONS_PER_CYCLE}t_${L2_MAP_BITS}mapb_${L2_NUM_MAPTABLE_SETS}x${L2_LIST_CAPACITY}_${folding}_${xor_policy}
                elif [[ "$PROT" = "msi_nine_xor_bdi_map" || "$PROT" = "msi_nine_xor_bdi_map3" || "$PROT" = "msi_nine_xor_thesaurus_map3" ]]; then
                    L2_DATA_REGIONS_USED=$L2_DATA_REGIONS
                    L2_DATA_SEGEMENT_SIZE_USED=$L2_DATA_SEGEMENT_SIZE
                    session_name=restore_perfect_${comparison}_${SIZE}${CORE}${PROT}_${CFG}_O${OOO}_r${ratio_str}_${L2_TRANSITIONS_PER_CYCLE}t_seg${L2_DATA_SEGEMENT_SIZE_USED}_${L2_DATA_REGIONS_USED}region_${L2_MAP_BITS}mapb_${L2_NUM_MAPTABLE_SETS}x${L2_LIST_CAPACITY}_${folding}_${xor_policy}_${INDEX_SHIFT_BITS}shift
                
                elif [[ "$PROT" = "msi_exc_nobdi" || "$PROT" = "msi_exc3" ]]; then
                    L2_DATA_REGIONS_USED=1
                    L2_DATA_SEGEMENT_SIZE_USED=64
                    session_name=restore_perfect_${comparison}_${SIZE}${CORE}${PROT}_${CFG}_O${OOO}_${L2_TRANSITIONS_PER_CYCLE}t
                elif [[ "$PROT" = "msi_exc_bdi" || "$PROT" = "msi_exc_bdi3" ]]; then
                    L2_DATA_REGIONS_USED=$L2_DATA_REGIONS
                    L2_DATA_SEGEMENT_SIZE_USED=$L2_DATA_SEGEMENT_SIZE
                    session_name=restore_perfect_${comparison}_${SIZE}${CORE}${PROT}_${CFG}_O${OOO}_r${ratio_str}_${L2_TRANSITIONS_PER_CYCLE}t_seg${L2_DATA_SEGEMENT_SIZE_USED}_${L2_DATA_REGIONS_USED}region
                
                  elif [ "$PROT" = "msi_exc_bdi3" ]; then
                      L2_DATA_REGIONS_USED=$L2_DATA_REGIONS
                      L2_DATA_SEGEMENT_SIZE_USED=$L2_DATA_SEGEMENT_SIZE

                elif [ "$PROT" = "mesi2_inc_nobdi" ]; then
                    L2_DATA_REGIONS_USED=1
                    L2_DATA_SEGEMENT_SIZE_USED=64
                    session_name=restore_perfect_${comparison}_${SIZE}${CORE}${PROT}_${CFG}_O${OOO}_${L2_TRANSITIONS_PER_CYCLE}t
                elif [ "$PROT" = "mesi2_inc_bdi" ]; then
                    L2_DATA_REGIONS_USED=$L2_DATA_REGIONS
                    L2_DATA_SEGEMENT_SIZE_USED=$L2_DATA_SEGEMENT_SIZE
                    session_name=restore_perfect_${comparison}_${SIZE}${CORE}${PROT}_${CFG}_O${OOO}_r${ratio_str}_${L2_TRANSITIONS_PER_CYCLE}t_seg${L2_DATA_SEGEMENT_SIZE_USED}_${L2_DATA_REGIONS_USED}region
                else
                    echo "wrong protocol"
                    exit 1
                fi

                session_name=${session_name}${LLCLAT}_${TAGPTR}

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
                    $DISASSEMBLE \
                    --cachecfg ${CFG} \
                    --comparison $comparison \
                    $fast \
                    $llclat $tagptr \
                    $debug " C-m
                else
                    echo "$BEN"
                    tmux new-window -n $BEN -t $session_name:
                    tmux send-keys -t $session_name:$BEN "python3 my_scripts/fs/ruby/checkpointing/perfect/run_restore_perfect_checkpoint.py \
                    --benchmark ${BEN} \
                    --core ${CORE} \
                    --set ${set} \
                    --protocol $PROT \
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
                    $DISASSEMBLE \
                    --cachecfg ${CFG} \
                    --comparison $comparison \
                    $fast \
                    $llclat $tagptr \
                    $debug" C-m
                fi
            done
        done
    done
done

echo "launched perfect full system ruby restore ckpt. "

