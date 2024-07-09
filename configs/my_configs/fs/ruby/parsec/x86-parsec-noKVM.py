# Zhewen
# reference: configs/example/gem5_library/x86-parsec-benchmarks.py

import argparse
import time

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
from gem5.resources.resource import Resource

from m5.stats.gem5stats import get_simstat


# Following are the list of benchmark programs for parsec.

benchmark_choices = [
    "blackscholes",
    "bodytrack",
    "canneal",
    "dedup",
    "facesim",
    "ferret",
    "fluidanimate",
    "freqmine",
    "raytrace",
    "streamcluster",
    "swaptions",
    "vips",
    "x264",
]

# Following are the input size.

size_choices = ["simsmall", "simmedium", "simlarge"]

parser = argparse.ArgumentParser(
    description="An example configuration script to run the npb benchmarks."
)

# The arguments accepted are the benchmark name and the simulation size.

parser.add_argument(
    "--benchmark",
    type=str,
    required=True,
    help="Input the benchmark program to execute.",
    choices=benchmark_choices,
)
parser.add_argument(
    "--ooo",
    type=bool,
    required=False,
    default=False,
    # action='store_true',
    help="use ooo core",
)
parser.add_argument(
    "--anonymous_latency",
    type=bool,
    required=False,
    default=False,
    help="assign l2 latency regardless of size",
)
parser.add_argument(
    "--size",
    type=str,
    required=True,
    help="Simulation size the benchmark program.",
    choices=size_choices,
)
parser.add_argument(
    "--l2size",
    type=str,
    required=False,
    default="256kB",
    help="l2size string",
    choices=["64kB", "128kB","256kB","512kB", "1024kB", "2048kB"],
)
parser.add_argument(
    "--core",
    type=int,
    required=False,
    default=2,
    help="core ct",
)
parser.add_argument(
    "--protocol",
    type=str,
    help="which protocol to run",
    choices=["baseline", "noisy", "decoupled", "compress", "dedup"],
    required=True,
)
parser.add_argument(
    "--path",
    type=str,
    required=False,
    help="path to the local x86-parsec disk image",
)
args = parser.parse_args()

# We check for the required gem5 build.

specified_l2size = int(args.l2size.split('kB')[0])

if args.anonymous_latency:
    l2_data_lat_map = { #TODO
        32: 10,
        64: 10,
        128: 10,
        256: 10,
        512: 10,
        1024: 10,
        2048: 10,
    }
    l2_tag_lat_map = { #TODO
        32: 2,
        64: 2,
        128: 2,
        256: 2,
        512: 2,
        1024: 2,
        2048: 2,
    }
else:
    l2_data_lat_map = { #TODO
        64: 4,
        128: 7,
        256: 11,
        512: 20,
        1024: 40,
        2048: 53,
    }
    l2_tag_lat_map = { #TODO
        64: 2,
        128: 2,
        256: 2,
        512: 4,
        1024: 4,
        2048: 4,
    }

# Setting up all the fixed system parameters here
# Caches: MESI Two Level Cache Hierarchy
if args.protocol == 'baseline':
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MESI_TWO_LEVEL,
        kvm_required=False,
    )

    from gem5.components.cachehierarchies.ruby.mesi_two_level_cache_hierarchy import (
        MESITwoLevelCacheHierarchy,
    )
    cache_hierarchy = MESITwoLevelCacheHierarchy(
        l1d_size="32kB",
        l1d_assoc=8,
        l1i_size="64kB",
        l1i_assoc=4,
        l2_size=args.l2size,
        l2_assoc=8,
        num_l2_banks=args.core,
        l2_data_lat = l2_data_lat_map[specified_l2size],
        l2_tag_lat = l2_tag_lat_map[specified_l2size],
    )
elif args.protocol == 'noisy': 
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MESI_TWO_LEVEL_MY,
        kvm_required=False,
    )
    from gem5.components.cachehierarchies.ruby.mesi_two_level_cache_hierarchy_my import (
     MESITwoLevelCacheHierarchyMy,
    )
    cache_hierarchy = MESITwoLevelCacheHierarchyMy(
        l1d_size="32kB",
        l1d_assoc=8,
        l1i_size="64kB",
        l1i_assoc=4,
        l2_size=args.l2size,
        l2_assoc=8,
        num_l2_banks=args.core,
        l2_data_lat = l2_data_lat_map[specified_l2size],
        l2_tag_lat = l2_tag_lat_map[specified_l2size],
    )
elif args.protocol == 'decoupled': 
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MESI_TWO_LEVEL_DECOUPLED,
        kvm_required=False,
    )
    from gem5.components.cachehierarchies.ruby.mesi_two_level_cache_hierarchy_decoupled import (
     MESITwoLevelCacheHierarchyDecoupled,
    )
    cache_hierarchy = MESITwoLevelCacheHierarchyDecoupled(
        l1d_size="32kB",
        l1d_assoc=8,
        l1i_size="64kB",
        l1i_assoc=4,
        l2_size=args.l2size, # simulating a halved data cache!
        l2_assoc=8, 
        num_l2_banks=args.core,
        l2_data_lat = l2_data_lat_map[specified_l2size/2],
        l2_tag_lat = l2_tag_lat_map[specified_l2size],
    )
elif args.protocol == 'compress': 
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MESI_TWO_LEVEL_COMPRESS,
        kvm_required=False,
    )
    from gem5.components.cachehierarchies.ruby.mesi_two_level_cache_hierarchy_compress import (
     MESITwoLevelCacheHierarchyCompress,
    )
    
    cache_hierarchy = MESITwoLevelCacheHierarchyCompress(
        l1d_size="32kB",
        l1d_assoc=8,
        l1i_size="64kB",
        l1i_assoc=4,
        l2_size=args.l2size, # simulating a halved data cache!
        l2_assoc=8,
        num_l2_banks=args.core,
        num_seg_per_blk=64,
        l2_data_lat = l2_data_lat_map[specified_l2size/2],
        l2_tag_lat = l2_tag_lat_map[specified_l2size],
    )
elif args.protocol == 'dedup': 
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MESI_TWO_LEVEL_DEDUP,
        kvm_required=False,
    )
    from gem5.components.cachehierarchies.ruby.mesi_two_level_cache_hierarchy_dedup import (
     MESITwoLevelCacheHierarchyDedup,
    )
    l2_dataset = specified_l2size * 1024 / 64 / 2
    cache_hierarchy = MESITwoLevelCacheHierarchyDedup(
        l1d_size="32kB",
        l1d_assoc=8,
        l1i_size="64kB",
        l1i_assoc=4,
        l2_size=args.l2size, # simulating a halved data cache!
        l2_assoc=8,
        num_l2_banks=args.core,
        num_seg_per_blk=64,
        l2_data_lat = l2_data_lat_map[specified_l2size/2],
        l2_tag_lat = l2_tag_lat_map[specified_l2size],
        l2_dataArraySet=l2_dataset,
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
if args.ooo:
    processor = SimpleSwitchableProcessor(
        starting_core_type=CPUTypes.TIMING,
        switch_core_type=CPUTypes.O3,
        isa=ISA.X86,
        num_cores=args.core,
    )
else:
    processor = SimpleSwitchableProcessor(
        starting_core_type=CPUTypes.TIMING,
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

# Here we set the FS workload, i.e., parsec benchmark
# After simulation has ended you may inspect
# `m5out/system.pc.com_1.device` to the stdout, if any.

# After the system boots, we execute the benchmark program and wait till the
# ROI `workbegin` annotation is reached (m5_work_begin()). We start collecting
# the number of committed instructions till ROI ends (marked by `workend`).
# We then finish executing the rest of the benchmark.

# Also, we sleep the system for some time so that the output is printed
# properly.


command = (
    "cd /home/gem5/parsec-benchmark;".format(args.benchmark)
    + "source env.sh;"
    + "parsecmgmt -a run -p {} -c gcc-hooks -i {} \
        -n {};".format(
        args.benchmark, args.size, args.core
    )
    + "sleep 5;"
    + "m5 exit;"
)

if args.path:
    # use local copy of disk image to prevent unix file locking
    from gem5.resources.resource import CustomDiskImageResource
    board.set_kernel_disk_workload(
        # PARSEC benchamarks were tested with kernel version 4.19.83
        kernel=Resource("x86-linux-kernel-4.19.83"),
        disk_image=CustomDiskImageResource(
            f"{args.path}/x86-parsec", disk_root_partition="1"
        ),
        readfile_contents=command,
    )
else:
    board.set_kernel_disk_workload(
        # The x86 linux kernel will be automatically downloaded to the
        # `~/.cache/gem5` directory if not already present.
        # PARSEC benchamarks were tested with kernel version 4.19.83
        kernel=Resource("x86-linux-kernel-4.19.83"),
        # The x86-parsec image will be automatically downloaded to the
        # `~/.cache/gem5` directory if not already present.
        disk_image=Resource("x86-parsec"),
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
print("Using ATOMIC cpu")

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

    # We have completed up to this step using ATOMIC cpu. Now we switch to timing
    # cpu for detailed simulation.

    processor.switch()
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
roi_insts = float(
    gem5stats.to_json()["system"]["processor"]["switch0"]["core"][
        "exec_context.thread_0"
    ]["numInsts"]["value"]
) + float(
    gem5stats.to_json()["system"]["processor"]["switch1"]["core"][
        "exec_context.thread_0"
    ]["numInsts"]["value"]
)

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
