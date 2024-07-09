# Author: Zhewen

"""
This gem5 configuation script creates a simple board to run an X86
custom binary.

This design uses ruby cache and more specifically it uses my implementation
of mesi two level.

This is setup is the close to the simplest setup possible using the gem5
library. It does not contain any kind of caching, IO, or any non-essential
components.

Usage
-----

```
scons build/X86_MyMESI2/gem5.opt
build/X86_MyMESI2/gem5.opt configs/my_configs/se/ruby/x86-custombinary-ruby-mymesidecoupled.py
```
"""

from gem5.isas import ISA
from gem5.utils.requires import requires
from gem5.resources.resource import Resource
from gem5.components.memory import SingleChannelDDR3_1600
from gem5.components.memory import DualChannelDDR4_2400
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.boards.simple_board import SimpleBoard

# hierarchy
from gem5.components.cachehierarchies.ruby.mesi_two_level_cache_hierarchy import (
    MESITwoLevelCacheHierarchy,
)
from gem5.components.cachehierarchies.ruby.mesi_two_level_cache_hierarchy_my import (
    MESITwoLevelCacheHierarchyMy,
)
from gem5.components.cachehierarchies.ruby.mesi_two_level_cache_hierarchy_decoupled import (
    MESITwoLevelCacheHierarchyDecoupled,
)

from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.simulate.simulator import Simulator
import argparse
import re
from gem5.coherence_protocol import CoherenceProtocol
from gem5.resources.resource import CustomResource

# This check ensures the gem5 binary is compiled to the ARM ISA target. If not,
# an exception will be thrown.
requires(
    isa_required=ISA.X86,
    coherence_protocol_required=CoherenceProtocol.MESI_TWO_LEVEL_DECOUPLED,
    kvm_required=True,
)


parser = argparse.ArgumentParser(description="config.")

parser.add_argument(
    "--l1d_size",
    type=str,
    required=False,
    default="32kB",
    help="l1d size format string",
)
parser.add_argument(
    "--l1d_assoc",
    type=int,
    required=False,
    default=8,
    help="l2 associativity",
)
parser.add_argument(
    "--l1i_size",
    type=str,
    required=False,
    default="32kB",
    help="l1i size format string",
)
parser.add_argument(
    "--l1i_assoc",
    type=int,
    required=False,
    default=8,
    help="l2 associativity",
)
parser.add_argument(
    "--l2_size",
    type=str,
    required=False,
    default="256kB",
    help="l2 size format string",
)
parser.add_argument(
    "--l2_assoc",
    type=int,
    required=False,
    default=16,
    help="l2 associativity",
)
parser.add_argument(
    "--num_l2_banks",
    type=int,
    required=False,
    default=1,
    help="l2 banks",
)
parser.add_argument(
    "--path",
    type=str,
    required=True,
    help="path to binary to run",
)
parser.add_argument(
    "--cpt_path",
    type=str,
    help="cpt_path (optional)",
)
parser.add_argument(
    "--frequency",
    type=str,
    default='3GHz',
    help="cpu frequency",
)
args = parser.parse_args()


# select hierarchy

cache_hierarchy = MESITwoLevelCacheHierarchyDecoupled(
    l1d_size=args.l1d_size,
    l1d_assoc=args.l1d_assoc,
    l1i_size=args.l1i_size,
    l1i_assoc=args.l1i_assoc,
    l2_size=args.l2_size,
    l2_assoc=args.l2_assoc,
    num_l2_banks=args.num_l2_banks,
)


# Memory: Dual Channel DDR4 2400 DRAM device.
# The X86 board only supports 3 GB of main memory.
memory = DualChannelDDR4_2400(size="3GB")

# We use a simple Timing processor with one core.
processor = SimpleProcessor(cpu_type=CPUTypes.TIMING, isa=ISA.X86, num_cores=1)

# The gem5 library simble board which can be used to run simple SE-mode
# simulations.
board = SimpleBoard(
    clk_freq=args.frequency,
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy,
)

# Here we set the workload. In this case we want to run a simple "Hello World!"
# program compiled to the ARM ISA. The `Resource` class will automatically
# download the binary from the gem5 Resources cloud bucket if it's not already
# present.
binary = CustomResource(local_path=f"{args.path}")
board.set_se_binary_workload(
    # The `Resource` class reads the `resources.json` file from the gem5
    # resources repository:
    # https://gem5.googlesource.com/public/gem5-resource.
    # Any resource specified in this file will be automatically retrieved.
    # At the time of writing, this file is a WIP and does not contain all
    # resources. Jira ticket:https://gem5.atlassian.net/browse/GEM5-1096
    binary=binary,
)

# Lastly we run the simulation.
simulator = Simulator(board=board)
simulator.run()

print(
    "Exiting @ tick {} because {}.".format(
        simulator.get_current_tick(), simulator.get_last_exit_event_cause()
    )
)

if args.cpt_path:
    checkpoint_path = args.cpt_path
    print("Taking a checkpoint at", checkpoint_path)
    simulator.save_checkpoint(checkpoint_path)
    print("Done taking a checkpoint")