# Zhewen
# reference: configs/example/gem5_library/x86-parsec-benchmarks.py

import argparse
import time
import re,os,sys

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

set_choices = [
    "ser",
    "omp",
]
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
command_for_benchmark = {
    "2d_convolution": "./2d_convolution",
    "dwt53": "./dwt53",
    "histogram_equalization": "./histogram_equalization",
    "debayer": "./wami-debayer ../../../inout",
    "change-detection": "./wami-change-detection ../../../inout",
    "lucas-kanade": "./wami-lucas-kanade ../../../inout",
}


parser = argparse.ArgumentParser(
    description="An example configuration script to run the \
        perfect suite (with hook)."
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
parser.add_argument(
    "--set",
    type=str,
    required=False,
    default="ser",
    help="run config. serial or parallel.",
    choices=set_choices,
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
    choices=["baseline", "noisy", "decoupled", "compress", "dedup","bdixor","hammer","dump"],
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
elif args.protocol == "hammer":
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.ARM_MOESI_HAMMER,
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
        l2_data_lat=10,
        l2_tag_lat=2,
    )
elif args.protocol == "dump":
    if args.index_bits_shift is None:
        print("index_bits_shift is not set")
        index_bits_shift = 0
    else:
        index_bits_shift = args.index_bits_shift

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
        num_l2_banks=1,
        l2_data_lat=10,
        l2_tag_lat=2,
        index_bits_shift=index_bits_shift,
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
        l2_size="512kB", # simulating a halved data cache!
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
# ROI `workbegin` annotation is reached (m5_work_begin()). We start collecting
# the number of committed instructions till ROI ends (marked by `workend`).
# We then finish executing the rest of the benchmark.

# Also, we sleep the system for some time so that the output is printed
# properly.

subdir = class_for_benchmark[args.benchmark]
command_str = command_for_benchmark[args.benchmark]
command = f'cd /home/gem5/perfect-suite/suite;\n' \
        f'cd {subdir}/kernels/{args.set};\n' \
        f'echo "{args.benchmark} starts :)";\ncd {args.benchmark};\n' \
        f'{command_str};\n' \
        f'echo "{args.benchmark} ends :)";\n' \
        f'ls;\n' \
        f'echo "ready to exit m5";\n' \
        f'sleep 1; m5 exit;'

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

# We start the simulation

exit_event = m5.simulate()

# The first exit_event ends with a `workbegin` cause. This means that the
# system booted successfully and the execution on the program started.

if exit_event.getCause() == "workbegin":

    print("Done booting Linux")
    print("Resetting stats at the start of ROI!")

    m5.stats.reset()
    start_tick = m5.curTick()
    print(f"at tick {start_tick}")

    # We have completed up to this step using KVM cpu. Now we switch to timing
    # cpu for detailed simulation.

    processor.switch()
    print("Switched CPU done")
else:
    # `workbegin` call was never encountered.

    print("Unexpected termination of simulation before ROI was reached!")
    print(
        "Exiting @ tick {} because {}.".format(
            m5.curTick(), exit_event.getCause()
        )
    )
    exit(-1)

# The next exit_event is to simulate the ROI. It should be exited with a cause
# marked by `workend`.

exit_event = m5.simulate()

# Reached the end of ROI.
# We dump the stats here.

# We exepect that ROI ends with `workend`. Otherwise the simulation ended
# unexpectedly.
if exit_event.getCause() == "workend":
    print("Dump stats at the end of the ROI!")

    m5.stats.dump()
    end_tick = m5.curTick()
else:
    print("Unexpected termination of simulation while ROI was being executed!")
    print(
        "Exiting @ tick {} because {}.".format(
            m5.curTick(), exit_event.getCause()
        )
    )
    exit(-1)

# ROI has ended here, and we get `simInsts` using get_simstat and print it in
# the final print statement.

gem5stats = get_simstat(root)

# We get the number of committed instructions from the timing
# cores. We then sum and print them at the end.
roi_insts = 0
if args.core == 1:
    roi_insts += float(
        gem5stats.to_json()["system"]["processor"][f"switch"]["core"][
            "exec_context.thread_0"
        ]["numInsts"]["value"])
else:
    for i in range(args.core):
        roi_insts += float(
            gem5stats.to_json()["system"]["processor"][f"switch{i}"]["core"][
                "exec_context.thread_0"
            ]["numInsts"]["value"])


# Simulation is over at this point. We acknowledge that all the simulation
# events were successful.
print("All simulation events were successful.")

# We print the final simulation statistics.

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
