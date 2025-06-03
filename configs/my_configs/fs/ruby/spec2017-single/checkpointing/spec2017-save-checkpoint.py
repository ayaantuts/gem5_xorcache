# Zhewen
# reference: configs/example/gem5_library/x86-spec-cpu2017-benchmarks.py
# Note: this is a modified version of the original file using the flexible spec2017 disk image
# in that the runscript needed to be provided in the command file
"""
Script to run SPEC CPU2017 benchmarks with gem5.
The script expects a benchmark program name and the simulation
size. The system is flexible in number of CPU cores (default 1), MESI Two Level system
cache and 3 GB DDR4 memory. It uses the x86 board.

This script will count the total number of instructions executed
in the ROI. It also tracks how much wallclock and simulated time.

Usage:
------
```
scons build/X86/gem5.opt
./build/X86/gem5.opt \
    configs/example/gem5_library/x86-spec-cpu2017-benchmarks.py \
    --image <full_path_to_the_spec-2017_disk_image> \
    --partition <root_partition_to_mount> \
    --benchmark <benchmark_name> \
    --size <simulation_size>
```
"""
import random
import argparse
import time
import os
import json
import subprocess, re

import m5
from m5.objects import Root

from gem5.utils.requires import requires
from gem5.components.boards.x86_board import X86Board
from gem5.components.memory import DualChannelDDR4_2400
from gem5.components.processors.cpu_types import CPUTypes
from gem5.isas import ISA
from gem5.coherence_protocol import CoherenceProtocol
from gem5.resources.resource import Resource, CustomDiskImageResource
from gem5.components.processors.simple_processor import SimpleProcessor

from m5.stats.gem5stats import get_simstat
from m5.util import warn
from m5.util import fatal

# We check for the required gem5 build.

requires(
    isa_required=ISA.X86,
    coherence_protocol_required=CoherenceProtocol.MESI_TWO_LEVEL,
    kvm_required=True,
)

# Following are the list of benchmark programs for SPEC CPU2017.
# More information is available at:
# https://www.gem5.org/documentation/benchmark_status/gem5-20

benchmark_choices = [
    "500.perlbench_r",
    "502.gcc_r",
    "503.bwaves_r",
    "505.mcf_r",
    "507.cactuBSSN_r",
    "508.namd_r",
    "510.parest_r",
    "511.povray_r",
    "519.lbm_r",
    "520.omnetpp_r",
    "521.wrf_r",
    "523.xalancbmk_r",
    "525.x264_r",
    "527.cam4_r",
    "531.deepsjeng_r",
    "538.imagick_r",
    "541.leela_r",
    "544.nab_r",
    "548.exchange2_r",
    "549.fotonik3d_r",
    "554.roms_r",
    "557.xz_r",
    # "600.perlbench_s",
    # "602.gcc_s",
    # "603.bwaves_s",
    # "605.mcf_s",
    # "607.cactusBSSN_s",
    # "608.namd_s",
    # "610.parest_s",
    # "611.povray_s",
    # "619.lbm_s",
    # "620.omnetpp_s",
    # "621.wrf_s",
    # "623.xalancbmk_s",
    # "625.x264_s",
    # "627.cam4_s",
    # "631.deepsjeng_s",
    # "638.imagick_s",
    # "641.leela_s",
    # "644.nab_s",
    # "648.exchange2_s",
    # "649.fotonik3d_s",
    # "654.roms_s",
    # "996.specrand_fs",
    # "997.specrand_fr",
    # "998.specrand_is",
    # "999.specrand_ir",
]

# Following are the input size.

size_choices = ["test", "train", "ref"]

parser = argparse.ArgumentParser(
    description="An example configuration script to run the \
        SPEC CPU2017 benchmarks."
)

# The arguments accepted are: a. disk-image name, b. benchmark name, c.
# simulation size, and, d. root partition.

# root partition is set to 1 by default.

parser.add_argument(
    "--image",
    type=str,
    required=True,
    help="Input the full path to the built spec-2017 disk-image.",
)

parser.add_argument(
    "--partition",
    type=str,
    required=False,
    default=None,
    help='Input the root partition of the SPEC disk-image. If the disk is \
    not partitioned, then pass "".',
)

parser.add_argument(
    "--fastforward_inst",
    type=int,
    required=False,
    help="Number of cycles to fast-forward the simulation using kvm.",
    default=1000,#1M
)
parser.add_argument(
    "--bench",
    type=str,
    required=True,
    choices=benchmark_choices,
    help="benchmark to run",
)
parser.add_argument(
    "--size",
    type=str,
    required=True,
    help="Simulation size the benchmark program.",
    choices=size_choices,
)

parser.add_argument(
    "--frequency",
    type=int,
    required=False,
    help="in ghz",
    default=3,
)
parser.add_argument(
    "--core",
    type=int,
    required=False,
    help="num of cores.",
    default=1,
)
parser.add_argument(
    "--do_ff",
    type=int,
    required=True,
    help="do fast forwarding.",
    default=1,
)
parser.add_argument(
    "--protocol",
    type=str,
    help="which protocol to run",
    choices=["no", "hammer"], # only hammer and no are supported for checkpoint
    required=True,
)
args = parser.parse_args()
freq = args.frequency

# We expect the user to input the full path of the disk-image.
if args.image[0] != "/":
    # We need to get the absolute path to this file. We assume that the file is
    # present on the current working directory.
    args.image = os.path.abspath(args.image)

if not os.path.exists(args.image):
    warn("Disk image not found!")
    print("Instructions on building the disk image can be found at: ")
    print(
        "https://gem5art.readthedocs.io/en/latest/tutorials/spec-tutorial.html"
    )
    fatal("The disk-image is not found at {}".format(args.image))

# Setting up all the fixed system parameters here
# Caches: MESI Two Level Cache Hierarchy
if args.protocol == 'no':
    requires(
        isa_required=ISA.X86,
        kvm_required=True,
    )

    from gem5.components.cachehierarchies.classic.no_cache import NoCache
    cache_hierarchy = NoCache()

elif args.protocol == 'hammer': 
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.ARM_MOESI_HAMMER,
        kvm_required=True,
    )
    from gem5.components.cachehierarchies.ruby.moesi_hammer_two_level_cache_hierarchy import (
     MOESIHammerTwoLevelCacheHierarchy,
    )
    
    cache_hierarchy = MOESIHammerTwoLevelCacheHierarchy(
        l1d_size="32kB",
        l1d_assoc=8,
        l1i_size="32kB",
        l1i_assoc=8,
        l2_size="512kB",
        l2_assoc=16,
        num_dirs=2,
    )

# Memory: Dual Channel DDR4 2400 DRAM device.
# The X86 board only supports 3 GB of main memory.

memory = DualChannelDDR4_2400(size="3GB")

# Here we setup the processor. This is a special switchable processor in which
# a starting core type and a switch core type must be specified. Once a
# configuration is instantiated a user may call `processor.switch()` to switch
# from the starting core types to the switch core types. In this simulation
# we start with KVM cores to simulate the OS boot, then switch to the Timing
# cores for the command we wish to run after boot.

processor = SimpleProcessor(
    cpu_type=CPUTypes.KVM, isa=ISA.X86, num_cores=args.core
)


# Here we setup the board. The X86Board allows for Full-System X86 simulations

board = X86Board(
    clk_freq=f"{freq}GHz",
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy,
)

# SPEC CPU2017 benchmarks output placed in /home/gem5/spec2017/results
# directory on the disk-image. The following folder is created in the
# m5.options.outdir and the output from the disk-image folder is copied to
# this folder.

output_dir = "speclogs_" + "".join(x.strip() for x in time.asctime().split())
output_dir = output_dir.replace(":", "")

# We create this folder if it is absent.
try:
    os.makedirs(os.path.join(m5.options.outdir, output_dir))
except FileExistsError:
    warn("output directory already exists!")

# Here we set the FS workload, i.e., SPEC CPU2017 benchmark
# After simulation has ended you may inspect
# `m5out/system.pc.com_1.device` to the stdout, if any.

# After the system boots, we execute the benchmark program and wait till the
# `m5_exit instruction encountered` is encountered. We start collecting
# the number of committed instructions till ROI ends (marked by another
# `m5_exit instruction encountered`). We then start copying the output logs,
# present in the /home/gem5/spec2017/results directory to the `output_dir`.

# The runscript.sh file places `m5 exit` before and after the following command
# Therefore, we only pass this command without m5 exit.
selected_bench_arr = [args.bench] * args.core

out = "#!/bin/bash\n"
# add build/setup instructions
out += f'runcpu --size {args.size} --iterations 1  --action runsetup --config myconfig.x86.cfg --define gcc_dir="/usr" --noreportable --nobuild {args.bench}\n' \
    f'm5 exit\n'
out += "# launch subshells, where each benchmark will be run continuously\n"

# add run instructions
for i in range(len(selected_bench_arr)):
    selected_bench = selected_bench_arr[i]
    i_hex = hex(2**i)
    # out += f'taskset {i_hex} runcpu --size {args.size} --iterations 1  --action runsetup --config myconfig.x86.cfg --define gcc_dir="/usr" --noreportable --nobuild {selected_bench} &\n'
    out += (
        f'( \n'
        f'  cd /home/gem5/spec2017/benchspec/CPU/{selected_bench}/run/run_base_refrate_mytest-m64.0000\n'
        f'  count=1\n'
        f'  while true; do\n'
        f'      echo "starting {selected_bench} run ${{count}}!"\n'
        f'      taskset {i_hex} specinvoke\n'
        f'      echo "{selected_bench}  run ${{count}} done!"\n'
        f'      ((count++))\n'
        f'  done\n'
        f') &\n'
    )

# add epilogue instructions
out += f'wait\n' \
    f'echo "All benchmarks finished"\n' \
    f'sleep 5\n' \
    f"m5 exit\n" \
    f'# copy the SPEC result files to host\n' \
    f'for filepath in /home/gem5/spec2017/result/*; do\n' \
    f'    filename=$(basename $filepath)\n' \
    f'    m5 writefile $filepath {output_dir}/$filename\n' \
    f'done\n' \
    f'm5 exit\n'
command = out

# For enabling CustomResource, we pass an additional parameter to mount the
# correct partition.

board.set_kernel_disk_workload(
    # The x86 linux kernel will be automatically downloaded to the
    # `~/.cache/gem5` directory if not already present.
    # SPEC CPU2017 benchamarks were tested with kernel version 4.19.83
    kernel=Resource("x86-linux-kernel-4.19.83"),
    # The location of the x86 SPEC CPU 2017 image
    disk_image=CustomDiskImageResource(
        args.image, disk_root_partition=args.partition
    ),
    readfile_contents=command,
)

# We need this for long running processes.
m5.disableAllListeners()

root = Root(full_system=True, system=board)

# sim_quantum must be set if KVM cores are used.

root.sim_quantum = int(1e9)

board._pre_instantiate()
m5.instantiate()

# We maintain the wall clock time.

globalStart = time.time()

print("Running the simulation")
print("Using KVM cpu")

start_tick = m5.curTick()
end_tick = m5.curTick()
m5.stats.reset()

# We start the simulation

exit_event = m5.simulate()

############################ the first m5_exit ############################
if exit_event.getCause() == "m5_exit instruction encountered":
    # We have completed booting the OS using KVM cpu
    # Reached the start of ROI

    print(f"Done booting Linux at tick {start_tick}")

else:
    print("Unexpected termination of simulation before ROI was reached!")
    print(
        "Exiting @ tick {} because {}.".format(
            m5.curTick(), exit_event.getCause()
        )
    )
    exit(-1)

############################ the second m5_exit ############################
exit_event = m5.simulate()
if exit_event.getCause() == "m5_exit instruction encountered":
    print(f"Done setting up benchmarks at tick {m5.curTick()}")
    if args.do_ff == 0:
        m5.checkpoint(m5.options.outdir + '/cpt')

        print("Done taking a checkpoint")
else:
    print("Unexpected termination of simulation during benchmark setup!")
    print(
        "Exiting @ tick {} because {}.".format(
            m5.curTick(), exit_event.getCause()
        )
    )
    exit(-1)


if args.do_ff == 1:
    # fastforward in the benchmark
    print(len(processor.get_cores()))
    for i in range(args.core):
        processor.get_cores()[i].core.scheduleInstStop(0, args.fastforward_inst, "m5_workbegin instruction encountered")
    num_workbegin_seen = 0
    print(f"[I] starting fastforward phase ({args.fastforward_inst} insts)")
    while True:
        exit_event = m5.simulate()
        if exit_event.getCause() == "m5_workbegin instruction encountered":
            num_workbegin_seen += 1
            if num_workbegin_seen == args.core:
                print(f"Finished fastforwarding for {args.fastforward_inst} insts")
                m5.checkpoint(m5.options.outdir + '/cpt')
                print("Done taking a checkpoint")
                break
        else:
            print("Unexpected termination of simulation while ff was being executed!")
            print(
                "Exiting @ tick {} because {}. {} workbegins seen.".format(
                    m5.curTick(), exit_event.getCause(), num_workbegin_seen
                )
            )
            exit(-1)
else:
    pass


