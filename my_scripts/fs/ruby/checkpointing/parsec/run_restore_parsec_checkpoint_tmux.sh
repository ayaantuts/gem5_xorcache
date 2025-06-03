#!/bin/bash
if (($# < 1))
then
    echo "specify the config set number"
    exit 1
fi

if [ "$USER" = "zpan52" ]; then
    echo "The user is zpan52. This is likely on condor"
    CKPT_SEARCH_PATH=
else
    echo "The user is not zpan52. This is likely on a local machine"
    CKPT_SEARCH_PATH=/home/$USER/Dropbox/result/coherence/m5out
fi

SIZE=simlarge
WARMUP=0
# LEVEL=$2
fast="--fast 1"

if [[ $WARMUP -eq 1 ]]
then
  warm="--do_warmup 1"
elif [[ $WARMUP -eq 0 ]]
then
  warm="--do_warmup 0"
else
  echo "unknown warmup option"
fi
host=$(hostname)
if [ "$host" = "zhewen-MS-7D25" ]; then
    home="--home 1"
else
    home=""
fi
declare -a bench=(
    # "blackscholes" 
    # "bodytrack" 
    # "canneal" 
    # "dedup" 
    # "facesim" 
    # "ferret" 
    "fluidanimate" 
    # "freqmine" 
    # "raytrace" 
    # "streamcluster" 
    # "swaptions" 
    # "vips" 
    # "x264"
)

# tagptr=""
# TAGPTR="TAGPTR"

tagptr="--no-tagptr"
TAGPTR="NOTAGPTR"

core=(
    # 2 
    4
)

suite="all"

comparison="isoperf"
# comparison="isoarea"

declare -a protocol=(
    #  "msi_nine_xor_bdi_map"
    #  "msi_nine_noxor_bdi_map"
    #  "msi_nine_xor_nobdi_map"
    #  "msi_nine_noxor_nobdi_map"

    #  "msi_nine_xor_bdi_map3"
    #  "msi_nine_xor_thesaurus_map3"

    #  "msi_nine_noxor_bdi_map3"
    #  "msi_nine_noxor_bpc_map3"
    #  "msi_nine_noxor_thesaurus_map3"

    #  "msi_nine_xor_nobdi_map3"

    #  "msi_nine_noxor_nobdi_map3"
    #  "mesi3"

    # "msi_exc3"
    "msi_exc_bdi3"

    # "msi_exc_nobdi"
    # "msi_exc_bdi"

    # "mesi2_inc_nobdi"
    # "mesi2_inc_bdi"
)

# ratio=2.5
# ratio=2.0
# ratio=1.5
ratio=1.3
# ratio=1.0
ratio_text=${ratio/./_}


# ooo="--ooo"
# OOO=1
ooo="--no-ooo"
OOO=0

L2_DATA_SEGEMENT_SIZE=8
L2_TRANSITIONS_PER_CYCLE=1024
L2_DATA_REGIONS=256

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
  2) echo "0-bytelabel, 8b, 256x1 =>256x10b=0.31KiB (Sufficient)"
    xor_policy="synergy"
    xor_folding_scheme=0
    folding="bytelabel"
    L2_MAP_BITS=8
    L2_NUM_MAPTABLE_SETS=256
    L2_LIST_CAPACITY=1
    ;;

  3) echo "0-bytelabel, 10b, 1024x1 =>1024x10b=1.25KiB (Sufficient)"
    xor_policy="synergy"
    xor_folding_scheme=0
    folding="bytelabel"
    L2_MAP_BITS=10
    L2_NUM_MAPTABLE_SETS=1024
    L2_LIST_CAPACITY=1
    ;;

  4) echo "0-bytelabel, 12b, 512x4 =>2048x15b=3.75KiB (M)"
    xor_policy="synergy"
    xor_folding_scheme=0
    folding="bytelabel"
    L2_MAP_BITS=12
    L2_NUM_MAPTABLE_SETS=512
    L2_LIST_CAPACITY=4
    ;;
  5) echo "0-bytelabel, 12b, 4096x1 =>4096x10b=5KiB (L,Sufficient)"
    xor_policy="synergy"
    xor_folding_scheme=0
    folding="bytelabel"
    L2_MAP_BITS=12
    L2_NUM_MAPTABLE_SETS=4096
    L2_LIST_CAPACITY=1
    ;;
  6) echo "0-bytelabel, 12b, 128x8 =>1024x20b=2.25KiB (S)"
    xor_policy="synergy"
    xor_folding_scheme=0
    folding="bytelabel"
    L2_MAP_BITS=12
    L2_NUM_MAPTABLE_SETS=128
    L2_LIST_CAPACITY=8
    ;;

  7) echo "0-bytelabel, 24b, 256x4 =>1024x28b=3.5KiB (M)"
    xor_policy="synergy"
    xor_folding_scheme=0
    folding="bytelabel"
    L2_MAP_BITS=24
    L2_NUM_MAPTABLE_SETS=256
    L2_LIST_CAPACITY=4
    ;;
  8) echo "0-bytelabel, 24b, 2048x1 =>2048x23b=5.75KiB (L)"
    xor_policy="synergy"
    xor_folding_scheme=0
    folding="bytelabel"
    L2_MAP_BITS=24
    L2_NUM_MAPTABLE_SETS=2048
    L2_LIST_CAPACITY=1
    ;;
  9) echo "0-bytelabel, 24b, 2048x1 =>512x25b=2.06KiB (S)"
    xor_policy="synergy"
    xor_folding_scheme=0
    folding="bytelabel"
    L2_MAP_BITS=24
    L2_NUM_MAPTABLE_SETS=32
    L2_LIST_CAPACITY=16
    ;;

  10) echo "2-hycomp, 24b, 256x4 =>1024x28b=3.5KiB (M)"
    xor_policy="synergy"
    xor_folding_scheme=2
    folding="hycomp"
    L2_MAP_BITS=24
    L2_NUM_MAPTABLE_SETS=256
    L2_LIST_CAPACITY=4
    ;;
  11) echo "2-hycomp, 24b, 2048x1 =>2048x23b=5.75KiB (L)"
    xor_policy="synergy"
    xor_folding_scheme=2
    folding="hycomp"
    L2_MAP_BITS=24
    L2_NUM_MAPTABLE_SETS=2048
    L2_LIST_CAPACITY=1
    ;;
  12) echo "2-hycomp, 24b, 2048x1 =>512x25b=2.06KiB (S)"
    xor_policy="synergy"
    xor_folding_scheme=2
    folding="hycomp"
    L2_MAP_BITS=24
    L2_NUM_MAPTABLE_SETS=32
    L2_LIST_CAPACITY=16
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
    "size512kB"
    "size2048kB"
)

debug=""

# debug="--begin 18657334935377 --end 18657334945378 --flags ProtocolTrace,RubyGenerated,RubySlicc"


for CFG in ${cachecfg[@]};do
    for CORE in ${core[@]};do
            for PROT in "${protocol[@]}"
            do
                for BEN in "${bench[@]}"
                do
                    if [[ "$PROT" = "mesi3" ]]; then
                        session_name=restore_parsec_${comparison}_${SIZE}${CORE}${PROT}_${CFG}_O${OOO}_${L2_TRANSITIONS_PER_CYCLE}t
                        L2_DATA_REGIONS_USED=1
                        L2_DATA_SEGEMENT_SIZE_USED=64
                    elif [[ "$PROT" = "msi_nine_noxor_nobdi_map" || "$PROT" = "msi_nine_noxor_nobdi_map3" ]]; then
                        session_name=restore_parsec_${comparison}_${SIZE}${CORE}${PROT}_${CFG}_O${OOO}_${L2_TRANSITIONS_PER_CYCLE}t
                        L2_DATA_REGIONS_USED=1
                        L2_DATA_SEGEMENT_SIZE_USED=64
                    elif [[ "$PROT" = "msi_nine_noxor_bdi_map" || "$PROT" = "msi_nine_noxor_bdi_map3" || "$PROT" = "msi_nine_noxor_bpc_map3"  || "$PROT" = "msi_nine_noxor_thesaurus_map3" ]]; then
                        L2_DATA_REGIONS_USED=$L2_DATA_REGIONS
                        L2_DATA_SEGEMENT_SIZE_USED=$L2_DATA_SEGEMENT_SIZE
                        session_name=restore_parsec_${comparison}_${SIZE}${CORE}${PROT}_${CFG}_O${OOO}_r${ratio_text}_${L2_TRANSITIONS_PER_CYCLE}t_seg${L2_DATA_SEGEMENT_SIZE_USED}_${L2_DATA_REGIONS_USED}region
                    elif [[ "$PROT" = "msi_nine_xor_nobdi_map" || "$PROT" = "msi_nine_xor_nobdi_map3" ]]; then
                        L2_DATA_REGIONS_USED=1
                        L2_DATA_SEGEMENT_SIZE_USED=64
                        session_name=restore_parsec_${comparison}_${SIZE}${CORE}${PROT}_${CFG}_O${OOO}_r${ratio_text}_${L2_TRANSITIONS_PER_CYCLE}t_${L2_MAP_BITS}mapb_${L2_NUM_MAPTABLE_SETS}x${L2_LIST_CAPACITY}_${folding}_${xor_policy}
                    elif [[ "$PROT" = "msi_nine_xor_bdi_map" || "$PROT" = "msi_nine_xor_bdi_map3" || "$PROT" = "msi_nine_xor_thesaurus_map3" ]]; then
                        L2_DATA_REGIONS_USED=$L2_DATA_REGIONS
                        L2_DATA_SEGEMENT_SIZE_USED=$L2_DATA_SEGEMENT_SIZE
                        session_name=restore_parsec_${comparison}_${SIZE}${CORE}${PROT}_${CFG}_O${OOO}_r${ratio_text}_${L2_TRANSITIONS_PER_CYCLE}t_seg${L2_DATA_SEGEMENT_SIZE_USED}_${L2_DATA_REGIONS_USED}region_${L2_MAP_BITS}mapb_${L2_NUM_MAPTABLE_SETS}x${L2_LIST_CAPACITY}_${folding}_${xor_policy}_${INDEX_SHIFT_BITS}shift
                    
                    elif [[ "$PROT" = "msi_exc_nobdi" || "$PROT" = "msi_exc3" ]]; then
                      L2_DATA_REGIONS_USED=1
                      L2_DATA_SEGEMENT_SIZE_USED=64
                      session_name=restore_parsec_${comparison}_${SIZE}${CORE}${PROT}_${CFG}_O${OOO}_${L2_TRANSITIONS_PER_CYCLE}t
                    elif [[ "$PROT" = "msi_exc_bdi" || "$PROT" = "msi_exc_bdi3" ]]; then
                      L2_DATA_REGIONS_USED=$L2_DATA_REGIONS
                      L2_DATA_SEGEMENT_SIZE_USED=$L2_DATA_SEGEMENT_SIZE
                      session_name=restore_parsec_${comparison}_${SIZE}${CORE}${PROT}_${CFG}_O${OOO}_r${ratio_str}_${L2_TRANSITIONS_PER_CYCLE}t_seg${L2_DATA_SEGEMENT_SIZE_USED}_${L2_DATA_REGIONS_USED}region
                  
                    elif [ "$PROT" = "mesi2_inc_nobdi" ]; then
                        L2_DATA_REGIONS_USED=1
                        L2_DATA_SEGEMENT_SIZE_USED=64
                        session_name=restore_parsec_${comparison}_${SIZE}${CORE}${PROT}_${CFG}_O${OOO}_${L2_TRANSITIONS_PER_CYCLE}t
                    elif [ "$PROT" = "mesi2_inc_bdi" ]; then
                        L2_DATA_REGIONS_USED=$L2_DATA_REGIONS
                        L2_DATA_SEGEMENT_SIZE_USED=$L2_DATA_SEGEMENT_SIZE
                        session_name=restore_parsec_${comparison}_${SIZE}${CORE}${PROT}_${CFG}_O${OOO}_r${ratio_str}_${L2_TRANSITIONS_PER_CYCLE}t_seg${L2_DATA_SEGEMENT_SIZE_USED}_${L2_DATA_REGIONS_USED}region
                    else
                        echo "wrong protocol"
                        exit 1
                    fi

                    session_name=${session_name}_${TAGPTR}

                    tmux has-session -t $session_name 2>/dev/null
                    if [ $? != 0 ]; then
                        # Set up your session
                        echo "create new session $session_name"
                        echo "$BEN"
                        tmux new-session -d -s $session_name -n $BEN 
                        tmux send-keys -t $session_name:$BEN "python3 my_scripts/fs/ruby/checkpointing/parsec/run_restore_parsec_checkpoint.py \
                        --benchmark ${BEN} \
                        --size ${SIZE} \
                        --core ${CORE} \
                        --l2factor $ratio \
                        --ckpt_search_path ${CKPT_SEARCH_PATH} \
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
                        --protocol $PROT \
                        --index_bits_shift ${INDEX_SHIFT_BITS} \
                        --cachecfg ${CFG} \
                        --comparison $comparison \
                        $fast $tagptr \
                        $debug $warmup" C-m
                    else
                        echo "$BEN"
                        tmux new-window -n $BEN -t $session_name:
                        tmux send-keys -t $session_name:$BEN "python3 my_scripts/fs/ruby/checkpointing/parsec/run_restore_parsec_checkpoint.py \
                        --benchmark ${BEN} \
                        --size ${SIZE} \
                        --core ${CORE} \
                        --l2factor $ratio \
                        --ckpt_search_path ${CKPT_SEARCH_PATH} \
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
                        --protocol $PROT \
                        --index_bits_shift ${INDEX_SHIFT_BITS} \
                        --cachecfg ${CFG} \
                        --comparison $comparison \
                        $fast $tagptr \
                        $debug $warmup" C-m
                    fi
                done
            done
    done
done

echo "launched parsec full system ruby restore ckpt."

