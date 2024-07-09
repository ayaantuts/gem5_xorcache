#!/bin/bash
if (($# < 2))
then
    echo "specify (core,total dim of arr)"
    exit 1
fi
CORE=$1
SIZE=$2

debug=""

# debug="--flags X86,Exec,Registers"
# debug="--flags RubyDataBlock"

# debug="--flags RubyCacheUtil,ProtocolTrace,X86,Exec,Registers"
# debug="--flags RubyCacheUtil,ProtocolTrace,RubyGenerated,RubySlicc --begin 895857598000 --end 895858098001"


# debug="--flags RubyCacheUtil,ProtocolTrace,RubyGenerated,RubySlicc,RubyCacheFASector --begin 1858959323000 --end 1858959333001"
# debug="--flags RubyCacheUtil,ProtocolTrace --begin 0 --end 361001"
# debug="--flags RubyCacheUtil,ProtocolTrace"
# debug="--flags RubyCacheUtil,ProtocolTrace,RubyGenerated,RubySlicc,RubySystem --begin 516681000 --end 516690001"
# debug="--flags RubyCacheUtil,ProtocolTrace,RubyGenerated,RubySlicc,RubySystem,RubyDataBlock --begin 5165074000 --end 5165079001"
# debug="--flags RubySystem --begin 3725270000 --end 5165079000"
# debug="--flags RubyCacheUtil"
# debug="--flags RubySystem"


declare -a bench=(
    # "threads" 
    # "threads_gem5" 
    "merge_sort" 
    # "merge_sort_gem5" 
    # "estimate_pi"
    # "share"
    # "share_l"
    # "share_l_gem5"
    # "rand_arr"
)

declare -a protocol=(
    # "baseline" 
    # "noisy" 
    # "decoupled" 
    # "compress"
    # "dedup" 
    # "bdixor"
    # "xor"
    # "msi"
    # "msi_nine"
    # "msi_nine_noxor"
    # "msi_nine_xor"
    # "msi_nine_xor_bdi_map"
    # "msi_nine_noxor_bdi_map"
    "msi_nine_xor_nobdi_map"
    "msi_nine_noxor_nobdi_map"
)
declare -a search_in_bank=(
    # "true" 
    # "false" 
)

declare -a ignore_proactive_eviction=(
    # "true"
    # "false" 
)

declare -a xor_policy_id=(
    # 1
    # 2
    # 3
    # 4
    # 5
    # 6
)

RUN=1

for PROT in "${protocol[@]}"
do
    for BEN in "${bench[@]}"
    do
        PATHBEN=tests/test-progs/${BEN}/bin/x86/linux/${BEN}

        if [[ "$PROT" == 'bdixor' || "$PROT" == 'xor' ]]; then
        
            for SIB in "${search_in_bank[@]}"
            do
                if [[ "$SIB" == 'true' ]]; then
                    SIBSTRING="--search_in_bank"
                else
                    SIBSTRING=""
                fi
                
                for IPC in "${ignore_proactive_eviction[@]}"
                do
                    if [[ "$IPC" == 'true' ]]; then
                        IPCSTRING="--ignore_proactive_eviction"
                    else
                        IPCSTRING=""
                    fi

                    for XOR in "${xor_policy_id[@]}"
                    do
                        tmux has-session -t arr${SIZE}c${CORE}${PROT}_RUN${RUN}_SIB${SIB}_IPC${IPC}_XOR${XOR} 2>/dev/null
                        if [ $? != 0 ]; then
                            # Set up your session
                            echo "create new session arr${SIZE}c${CORE}${PROT}_RUN${RUN}_SIB${SIB}_IPC${IPC}_XOR${XOR}"
                            echo "$BEN"
                            tmux new-session -d -s arr${SIZE}c${CORE}${PROT}_RUN${RUN}_SIB${SIB}_IPC${IPC}_XOR${XOR} -n $BEN 
                            tmux send-keys -t arr${SIZE}c${CORE}${PROT}_RUN${RUN}_SIB${SIB}_IPC${IPC}_XOR${XOR}:$BEN "python3 my_scripts/se/ruby/run_simple_ruby.py \
                            --path ${PATHBEN} \
                            --arg ${SIZE} \
                            --core ${CORE} \
                            --protocol $PROT \
                            $SIBSTRING \
                            $IPCSTRING \
                            --xor_policy $XOR \
                            $debug \
                            --o3 \
                            --run $RUN" C-m
                        else
                            echo "$BEN"
                            tmux new-window -n $BEN -t arr${SIZE}c${CORE}${PROT}_RUN${RUN}_SIB${SIB}_IPC${IPC}_XOR${XOR}:
                            tmux send-keys -t arr${SIZE}c${CORE}${PROT}_RUN${RUN}_SIB${SIB}_IPC${IPC}_XOR${XOR}:$BEN "python3 my_scripts/se/ruby/run_simple_ruby.py \
                            --path ${PATHBEN} \
                            --arg ${SIZE} \
                            --core ${CORE} \
                            --protocol $PROT \
                            $SIBSTRING \
                            $IPCSTRING \
                            --xor_policy $XOR \
                            $debug \
                            --o3 \
                            --run $RUN" C-m
                        fi
                    done
                done
            done
        else
            tmux has-session -t arr${SIZE}c${CORE}${PROT}_RUN${RUN} 2>/dev/null
            if [ $? != 0 ]; then
                # Set up your session
                echo "create new session arr${SIZE}c${CORE}${PROT}_RUN${RUN}"
                echo "$BEN"
                tmux new-session -d -s arr${SIZE}c${CORE}${PROT}_RUN${RUN} -n $BEN 
                tmux send-keys -t arr${SIZE}c${CORE}${PROT}_RUN${RUN}:$BEN "python3 my_scripts/se/ruby/run_simple_ruby.py \
                --path ${PATHBEN} \
                --arg ${SIZE} \
                --core ${CORE} \
                --protocol $PROT \
                $debug \
                --o3 \
                --run $RUN" C-m
            else
                echo "$BEN"
                tmux new-window -n $BEN -t arr${SIZE}c${CORE}${PROT}_RUN${RUN}:
                tmux send-keys -t arr${SIZE}c${CORE}${PROT}_RUN${RUN}:$BEN "python3 my_scripts/se/ruby/run_simple_ruby.py \
                --path ${PATHBEN} \
                --arg ${SIZE} \
                --core ${CORE} \
                --protocol $PROT \
                $debug \
                --o3 \
                --run $RUN" C-m
            fi
        fi
    done
done
            # --ignore_proactive_eviction \
            # --search_in_bank \

echo ""
echo ""
echo "launched micro bench se ruby runs. RUN ${RUN}"

