# Zhewen
# reference: configs/example/gem5_library/x86-spec-cpu2017-benchmarks.py

"""
Script to run perfect suite in gem5.

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
```
"""

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
from gem5.components.processors.simple_switchable_processor import (
    SimpleSwitchableProcessor,
)
from gem5.components.processors.cpu_types import CPUTypes
from gem5.isas import ISA
from gem5.coherence_protocol import CoherenceProtocol
from gem5.resources.resource import Resource, CustomDiskImageResource

from m5.stats.gem5stats import get_simstat
from m5.util import warn
from m5.util import fatal

benchmark_choices = [
    "2d_convolution",
    "dwt53",
    "histogram_equalization",
    "change-detection",
    "debayer",
    "lucas-kanade",
]
class_for_benchmark = {
    "2d_convolution": "pa1",
    "dwt53": "pa1",
    "histogram_equalization": "pa1",
    "change-detection": "wami",
    "debayer": "wami",
    "lucas-kanade": "wami",
}
# suffix_choices = [
#     'X86',
#     "gem5",
# ]
# Following are the input size.

parser = argparse.ArgumentParser(
    description="An example configuration script to run the \
        perfect suite."
)

# The arguments accepted are: a. disk-image name, b. benchmark name, c.
# simulation size, and, d. root partition.

# root partition is set to 1 by default.

parser.add_argument(
    "--image",
    type=str,
    required=True,
    help="Input the full path to the built disk-image.",
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
    "--benchmark",
    type=str,
    required=True,
    help="Input the benchmark program to execute.",
    choices=benchmark_choices,
)
# parser.add_argument(
#     "--suffix",
#     type=str,
#     required=False,
#     default='X86',
#     help="binary suffix.",
#     choices=suffix_choices,
# )

parser.add_argument(
    "--protocol",
    type=str,
    help="which protocol to run",
    choices=["baseline", "noisy", "decoupled", "compress", "dedup","bdixor"],
    required=True,
)

parser.add_argument(
    "--core",
    type=int,
    required=False,
    help="num of cores.",
    default=1,
)

args = parser.parse_args()

# We check for the required gem5 build.
if args.protocol == "baseline":
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MESI_TWO_LEVEL,
        kvm_required=True,
    )
elif args.protocol == "noisy":
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MESI_TWO_LEVEL_MY,
        kvm_required=True,
    )
elif args.protocol == "decoupled":
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MESI_TWO_LEVEL_DECOUPLED,
        kvm_required=True,
    )
elif args.protocol == "compress":
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MESI_TWO_LEVEL_COMPRESS,
        kvm_required=True,
    )
elif args.protocol == "dedup":
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MESI_TWO_LEVEL_DEDUP,
        kvm_required=True,
    )


# We expect the user to input the full path of the disk-image.
if args.image[0] != "/":
    # We need to get the absolute path to this file. We assume that the file is
    # present on the current working directory.
    args.image = os.path.abspath(args.image)

if not os.path.exists(args.image):
    warn("Disk image not found!")
    fatal("The disk-image is not found at {}".format(args.image))

# Setting up all the fixed system parameters here
# Caches: MESI Two Level Cache Hierarchy
# hierarchy
if args.protocol == "baseline":
    from gem5.components.cachehierarchies.ruby.mesi_two_level_cache_hierarchy import (
        MESITwoLevelCacheHierarchy,
    )
    cache_hierarchy = MESITwoLevelCacheHierarchy(
        l1d_size="32kB",
        l1d_assoc=8,
        l1i_size="32kB",
        l1i_assoc=8,
        l2_size="256kB",
        l2_assoc=16,
        num_l2_banks=2,
    )
elif args.protocol == "noisy":
    from gem5.components.cachehierarchies.ruby.mesi_two_level_cache_hierarchy_my import (
     MESITwoLevelCacheHierarchyMy,
    )
    cache_hierarchy = MESITwoLevelCacheHierarchyMy(
        l1d_size="32kB",
        l1d_assoc=8,
        l1i_size="32kB",
        l1i_assoc=8,
        l2_size="256kB",
        l2_assoc=16,
        num_l2_banks=2,
        l2_data_lat=10,
        l2_tag_lat=2,
    )
elif args.protocol == "decoupled":
    from gem5.components.cachehierarchies.ruby.mesi_two_level_cache_hierarchy_decoupled import (
     MESITwoLevelCacheHierarchyDecoupled,
    )
    cache_hierarchy = MESITwoLevelCacheHierarchyDecoupled(
        l1d_size="32kB",
        l1d_assoc=8,
        l1i_size="32kB",
        l1i_assoc=8,
        l2_size="512kB",
        l2_assoc=16,
        num_l2_banks=2,
    )
elif args.protocol == "compress":
    from gem5.components.cachehierarchies.ruby.mesi_two_level_cache_hierarchy_compress import (
     MESITwoLevelCacheHierarchyCompress,
    )
    cache_hierarchy = MESITwoLevelCacheHierarchyCompress(
        l1d_size="32kB",
        l1d_assoc=8,
        l1i_size="32kB",
        l1i_assoc=8,
        l2_size="512kB",
        l2_assoc=16,
        num_l2_banks=2,
        num_seg_per_blk=64,
        l2_data_lat=10,
        l2_tag_lat=2,
    )
elif args.protocol == "dedup":
    from gem5.components.cachehierarchies.ruby.mesi_two_level_cache_hierarchy_dedup import (
     MESITwoLevelCacheHierarchyDedup,
    )
    cache_hierarchy = MESITwoLevelCacheHierarchyDedup(
        l1d_size="32kB",
        l1d_assoc=8,
        l1i_size="32kB",
        l1i_assoc=8,
        l2_size="512kB",
        l2_assoc=16,
        num_l2_banks=2,
        num_seg_per_blk=64,
        l2_data_lat=10,
        l2_tag_lat=2,
        l2_dataArraySet=4096,
    )
elif args.protocol == 'bdixor': 
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MESI_TWO_LEVEL_BDI_XOR,
        kvm_required=True,
    )
    from gem5.components.cachehierarchies.ruby.mesi_two_level_cache_hierarchy_bdixor import (
     MESITwoLevelCacheHierarchyBDIXOR,
    )
    
    cache_hierarchy = MESITwoLevelCacheHierarchyBDIXOR(
        l1d_size="32kB",
        l1d_assoc=8,
        l1i_size="32kB",
        l1i_assoc=8,
        l2_size="512kB", # simulating a halved data cache!
        l2_assoc=16,
        num_l2_banks=2,
        num_seg_per_blk=64,
        l2_data_lat = 10,
        l2_tag_lat = 2,
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

processor = SimpleSwitchableProcessor(
    starting_core_type=CPUTypes.KVM,
    switch_core_type=CPUTypes.TIMING,
    isa=ISA.X86,
    num_cores=args.core,
)

# Here we setup the board. The X86Board allows for Full-System X86 simulations

board = X86Board(
    clk_freq="3GHz",
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy,
)


# Here we set the FS workload, i.e., benchmark
# After simulation has ended you may inspect
# `m5out/system.pc.com_1.device` to the stdout, if any.

# After the system boots, we execute the benchmark program and wait till the
# `m5_exit instruction encountered` is encountered. We start collecting
# the number of committed instructions till ROI ends (marked by another
# `m5_exit instruction encountered`). 

# The runscript.sh file places `m5 exit` before and after the following command
# Therefore, we only pass this command without m5 exit.
subdir = class_for_benchmark[args.benchmark]
out = f'cd /home/gem5/perfect-suite/suite;\n' \
        f'cd {subdir}/kernels/ser;\n' \
        f'echo "{args.benchmark} starts :)";\ncd {args.benchmark};\n' \
        f'm5 exit;\n' \
        f'./{args.benchmark};\n' \
        f'echo "{args.benchmark} ends :)";\n' \
        f'ls;\n' \
        f'm5 exit;\n' \
        f'echo "ready to exit m5";\n' \
        f'm5 exit;'

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

# sim_quantum must be set when KVM cores are used.

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

exit_event = m5.simulate()

############################ the first m5_exit ############################
if exit_event.getCause() == "m5_exit instruction encountered":
    # We have completed booting the OS using KVM cpu
    # Reached the start of ROI

    print("first m5 exit: Done booting Linux,  switching core")
    # print("Resetting stats at the start of ROI!")

    m5.stats.reset()
    start_tick = m5.curTick()
    print(f"at tick {start_tick}")

    # We switch to timing cpu for detailed simulation.

    processor.switch()
else:
    print("Unexpected termination of simulation before ROI was reached!")
    print(
        "Exiting @ tick {} because {}.".format(
            m5.curTick(), exit_event.getCause()
        )
    )
    exit(-1)

# Simulate the ROI
exit_event = m5.simulate()

# Reached the end of ROI
gem5stats = get_simstat(root)

# We get the number of committed instructions from the timing
# cores. We then sum and print them at the end.

# system.processor.switch0.core.exec_context.thread_0.numInsts
roi_insts = 0
for i in range(args.core):
    if args.core == 1:
        roi_insts += float(
            json.loads(gem5stats.dumps())["system"]["processor"][f"switch"]["core"]
                ["exec_context.thread_0"]["numInsts"]["value"]
        )
    else:
        roi_insts += float(
            json.loads(gem5stats.dumps())["system"]["processor"][f"switch{i}"]["core"]
                ["exec_context.thread_0"]["numInsts"]["value"]
        )

############################ the 2nd m5_exit ############################
if exit_event.getCause() == "m5_exit instruction encountered":
    print("second m5 exit: after run script")
    # print("Dump stats at the end of the ROI!")
    m5.stats.dump()
    end_tick = m5.curTick()
    # m5.stats.reset()

else:
    print("Unexpected termination of simulation while ROI was being executed!")
    print(
        "Exiting @ tick {} because {}.".format(
            m5.curTick(), exit_event.getCause()
        )
    )
    exit(-1)

# We need to execute epilogue

exit_event = m5.simulate()

############################ the 3rd m5_exit ############################
if exit_event.getCause() == "m5_exit instruction encountered":
    print("third m5 exit: done epilogue!")

else:
    print("Unexpected termination of simulation while executing epilogue!")
    print(
        "Exiting @ tick {} because {}.".format(
            m5.curTick(), exit_event.getCause()
        )
    )
    exit(-1)

print("Done with the simulation")
print()
print("Performance statistics:")

print("Simulated time in ROI: %.2fs" % ((end_tick - start_tick) / 1e12))
print("Instructions executed in ROI: %d" % ((roi_insts)))
print("Ran a total of", m5.curTick() / 1e12, "simulated seconds")
print(
    "Total wallclock time: %.2fs, %.2f min"
    % (time.time() - globalStart, (time.time() - globalStart) / 60)
)
