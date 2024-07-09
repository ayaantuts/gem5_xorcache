# Author: Zhewen

"""
This gem5 configuation script creates a simple board to run an X86
custom binary.

This is setup is the close to the simplest setup possible using the gem5
library. It does not contain any kind of caching, IO, or any non-essential
components.

Usage
-----

```
scons build/X86/gem5.opt
./build/X86/gem5.opt configs/my_configs/se/classic/x86-custombinary.py
```
"""

from gem5.isas import ISA
from gem5.utils.requires import requires
from gem5.resources.resource import Resource
from gem5.components.memory import SingleChannelDDR3_1600
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.boards.simple_board import SimpleBoard

# hierarchy
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy_b64d32 import (
    PrivateL1SharedL2CacheHierarchy_b64d32,
)
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy_b64d16 import (
    PrivateL1SharedL2CacheHierarchy_b64d16,
)
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy_b64d8 import (
    PrivateL1SharedL2CacheHierarchy_b64d8,
)
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy_b32d16 import (
    PrivateL1SharedL2CacheHierarchy_b32d16,
)
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy_b32d8 import (
    PrivateL1SharedL2CacheHierarchy_b32d8,
)
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy_b16d8 import (
    PrivateL1SharedL2CacheHierarchy_b16d8,
)
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy_cpack import (
    PrivateL1SharedL2CacheHierarchy_cpack,
)
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy_fpc import (
    PrivateL1SharedL2CacheHierarchy_fpc,
)
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy_fpcd import (
    PrivateL1SharedL2CacheHierarchy_fpcd,
)
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy_fvc import (
    PrivateL1SharedL2CacheHierarchy_fvc,
)
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy_perfect import (
    PrivateL1SharedL2CacheHierarchy_perfect,
)
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy_zero import (
    PrivateL1SharedL2CacheHierarchy_zero,
)
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy_multi import (
    PrivateL1SharedL2CacheHierarchy_multi,
)
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy_bdi import (
    PrivateL1SharedL2CacheHierarchy_bdi,
)
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy_repeat import (
    PrivateL1SharedL2CacheHierarchy_repeat,
)
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy_twin import (
    PrivateL1SharedL2CacheHierarchy_twin,
)

from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy import (
    PrivateL1SharedL2CacheHierarchy,
)
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy_noprefetch import (
    PrivateL1SharedL2CacheHierarchy_noPrefetch,
)

from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.simulate.simulator import Simulator
import argparse
import re
from gem5.resources.resource import CustomResource

# This check ensures the gem5 binary is compiled to the ARM ISA target. If not,
# an exception will be thrown.
requires(isa_required=ISA.X86)

parser = argparse.ArgumentParser(description="config.")

parser.add_argument(
    "--comp",
    type=str,
    required=False,
    default="null",
    help="l2 compression scheme. default to null.",
)
parser.add_argument(
    "--l1d_size",
    type=str,
    required=False,
    default="32kB",
    help="l1d size format string",
)
parser.add_argument(
    "--l1i_size",
    type=str,
    required=False,
    default="32kB",
    help="l1i size format string",
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
args = parser.parse_args()

print(f"l2 compression scheme={args.comp}")

# select hierarchy
if args.comp == "null":
    print(
        "x86-custombinary.py: Using default cache hierarchy: no compressor, no prefetch"
    )
    cache_hierarchy = PrivateL1SharedL2CacheHierarchy_noPrefetch(
        l1d_size=args.l1d_size,
        l1i_size=args.l1i_size,
        l2_size=args.l2_size,
        l2_assoc=args.l2_assoc,
    )
elif args.comp == "prefetch":
    cache_hierarchy = PrivateL1SharedL2CacheHierarchy(
        l1d_size=args.l1d_size,
        l1i_size=args.l1i_size,
        l2_size=args.l2_size,
        l2_assoc=args.l2_assoc,
    )
elif args.comp == "twin":
    l2size_orig = int(re.findall(r"\d+", args.l2_size)[0])
    l2_size_str = args.l2_size.replace(str(l2size_orig), str(2 * l2size_orig))

    cache_hierarchy = PrivateL1SharedL2CacheHierarchy_twin(
        l1d_size=args.l1d_size,
        l1i_size=args.l1i_size,
        l2_size=l2_size_str,
        l2_assoc=args.l2_assoc * 2,
    )
elif args.comp == "b64d32":
    cache_hierarchy = PrivateL1SharedL2CacheHierarchy_b64d32(
        l1d_size=args.l1d_size,
        l1i_size=args.l1i_size,
        l2_size=args.l2_size,
        l2_assoc=args.l2_assoc,
    )
elif args.comp == "b64d16":
    cache_hierarchy = PrivateL1SharedL2CacheHierarchy_b64d16(
        l1d_size=args.l1d_size,
        l1i_size=args.l1i_size,
        l2_size=args.l2_size,
        l2_assoc=args.l2_assoc,
    )
elif args.comp == "b64d8":
    cache_hierarchy = PrivateL1SharedL2CacheHierarchy_b64d8(
        l1d_size=args.l1d_size,
        l1i_size=args.l1i_size,
        l2_size=args.l2_size,
        l2_assoc=args.l2_assoc,
    )
elif args.comp == "b32d16":
    cache_hierarchy = PrivateL1SharedL2CacheHierarchy_b32d16(
        l1d_size=args.l1d_size,
        l1i_size=args.l1i_size,
        l2_size=args.l2_size,
        l2_assoc=args.l2_assoc,
    )
elif args.comp == "b32d8":
    cache_hierarchy = PrivateL1SharedL2CacheHierarchy_b32d8(
        l1d_size=args.l1d_size,
        l1i_size=args.l1i_size,
        l2_size=args.l2_size,
        l2_assoc=args.l2_assoc,
    )
elif args.comp == "b16d8":
    cache_hierarchy = PrivateL1SharedL2CacheHierarchy_b16d8(
        l1d_size=args.l1d_size,
        l1i_size=args.l1i_size,
        l2_size=args.l2_size,
        l2_assoc=args.l2_assoc,
    )
elif args.comp == "cpack":
    cache_hierarchy = PrivateL1SharedL2CacheHierarchy_cpack(
        l1d_size=args.l1d_size,
        l1i_size=args.l1i_size,
        l2_size=args.l2_size,
        l2_assoc=args.l2_assoc,
    )
elif args.comp == "fpc":
    cache_hierarchy = PrivateL1SharedL2CacheHierarchy_fpc(
        l1d_size=args.l1d_size,
        l1i_size=args.l1i_size,
        l2_size=args.l2_size,
        l2_assoc=args.l2_assoc,
    )
elif args.comp == "fpcd":
    cache_hierarchy = PrivateL1SharedL2CacheHierarchy_fpcd(
        l1d_size=args.l1d_size,
        l1i_size=args.l1i_size,
        l2_size=args.l2_size,
        l2_assoc=args.l2_assoc,
    )
elif args.comp == "fvc":
    cache_hierarchy = PrivateL1SharedL2CacheHierarchy_fvc(
        l1d_size=args.l1d_size,
        l1i_size=args.l1i_size,
        l2_size=args.l2_size,
        l2_assoc=args.l2_assoc,
    )
elif args.comp == "multi":
    cache_hierarchy = PrivateL1SharedL2CacheHierarchy_multi(
        l1d_size=args.l1d_size,
        l1i_size=args.l1i_size,
        l2_size=args.l2_size,
        l2_assoc=args.l2_assoc,
    )
elif args.comp == "perfect":
    cache_hierarchy = PrivateL1SharedL2CacheHierarchy_perfect(
        l1d_size=args.l1d_size,
        l1i_size=args.l1i_size,
        l2_size=args.l2_size,
        l2_assoc=args.l2_assoc,
    )
elif args.comp == "repeat":
    cache_hierarchy = PrivateL1SharedL2CacheHierarchy_repeat(
        l1d_size=args.l1d_size,
        l1i_size=args.l1i_size,
        l2_size=args.l2_size,
        l2_assoc=args.l2_assoc,
    )
elif args.comp == "zero":
    cache_hierarchy = PrivateL1SharedL2CacheHierarchy_zero(
        l1d_size=args.l1d_size,
        l1i_size=args.l1i_size,
        l2_size=args.l2_size,
        l2_assoc=args.l2_assoc,
    )
elif args.comp == "bdi":
    cache_hierarchy = PrivateL1SharedL2CacheHierarchy_bdi(
        l1d_size=args.l1d_size,
        l1i_size=args.l1i_size,
        l2_size=args.l2_size,
        l2_assoc=args.l2_assoc,
    )
else:
    print(f"unknown comp config:{args.comp}")
    exit(1)


# We use a single channel DDR3_1600 memory system
memory = SingleChannelDDR3_1600(size="32MB")

# We use a simple Timing processor with one core.
processor = SimpleProcessor(cpu_type=CPUTypes.TIMING, isa=ISA.X86, num_cores=1)

# The gem5 library simble board which can be used to run simple SE-mode
# simulations.
board = SimpleBoard(
    clk_freq="3GHz",
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