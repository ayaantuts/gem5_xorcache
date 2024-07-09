Compile XOR Cache: 
```scons build/X86_MyMSI_NINE_XOR_MAP/gem5.fast --default=X86 PROTOCOL=MSI_Two_Level_NINE_XOR_MAP SLICC_HTML=True -j24```

Run simulation on benchmarks (perfect, parsec, spec2017). 
Scripts are located in ```my_scripts/fs/ruby/checkpointing```. Take perfect for example. Note that some benchmark in parsec and spec2017 simulations can take as long as 40+ hours.
1. Create benchmark checkpoint (will exit and create checkpoint when system boot up and ready to execute region of interest). Note that you need a x86 machine for kvm acceleration. 
    ```./my_scripts/fs/ruby/checkpointing/perfect/make_perfect_checkpoint_tmux.sh```
    Note that this creates one tmux session per checkpoint. Run ```tmux ls``` and ```tmux a -t ...``` to inspect terminal output.
2. Run detailed simulation on benchmark starting from checkpoint.
```./my_scripts/fs/ruby/checkpointing/perfect/run_restore_perfect_checkpoint_tmux.sh```
3. examine generated stats.txt in m5out/
