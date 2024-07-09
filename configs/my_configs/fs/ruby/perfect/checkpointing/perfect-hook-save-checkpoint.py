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
from gem5.components.processors.cpu_types import CPUTypes
from gem5.isas import ISA
from gem5.coherence_protocol import CoherenceProtocol
from gem5.resources.resource import Resource, CustomDiskImageResource
from gem5.components.processors.simple_processor import SimpleProcessor

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
    "--core",
    type=int,
    required=False,
    default=1,
    help="core ct",
)
parser.add_argument(
    "--set",
    type=str,
    required=False,
    default="ser",
    help="run config. serial or parallel.",
    choices=set_choices,
)
parser.add_argument(
    "--protocol",
    type=str,
    help="which protocol to run",
    choices=["no", "hammer"], # only hammer and no are supported for checkpoint
    required=True,
)
parser.add_argument(
    "--kernel_args",
    required=False,
    type=str,
)
args = parser.parse_args()




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
if args.kernel_args:
    ka = [args.kernel_args]
    print(f"kernel_args: {ka}")
else:
    ka = None

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
    kernel_args=ka,
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

# The first exit_event ends with a `workbegin` cause. This means that the
# system booted successfully and the execution on the program started.

if exit_event.getCause() == "workbegin":

    print("Done booting Linux")
    
    m5.checkpoint(m5.options.outdir + '/cpt')

    print("Done taking a checkpoint")

    print(
        "Exiting @ tick {} because {}.".format(
            m5.curTick(), exit_event.getCause()
        )
    )
    sys.exit(exit_event.getCode())


else:
    # `workbegin` call was never encountered.

    print("Unexpected termination of simulation before ROI was reached!")
    print(
        "Exiting @ tick {} because {}.".format(
            m5.curTick(), exit_event.getCause()
        )
    )
    exit(-1)


