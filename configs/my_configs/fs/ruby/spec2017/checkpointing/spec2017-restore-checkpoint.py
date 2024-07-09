# Zhewen
# reference: configs/example/gem5_library/x86-spec-cpu2017-benchmarks.py

# Note1: this is a modified version of the original file using the flexible spec2017 disk image
# in that the runscript needed to be provided in the command file

# Note2: this is also a variant of spec2017.py in that it's intended to be used with x86_dump binary
# which dumps cache contents+address through the hacked stats dump interface.
# This scripts will first use kvm to book system and forward for specified number of cycle to bypass
# the initialization phase of running benchmarks and then warmup the cache for specified number of cycles,
# finally, it will run the benchmark for specified number of cycles and dump a total of 100 cache snapshots.

# instruction version
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
import re
import os
import json
import subprocess, re
import math

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
from gem5.components.memory.simple import SingleChannelSimpleMemory

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
get_cycle_from_tick = lambda tick, freq : tick / (1000/freq) 

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
    "--detailed_inst",
    type=int,
    required=False,
    help="Number of cycles to perform detailed simulation.",
    # default=5000,
    # default=100000000,#0.1B
    default=500000000,#0.5B
    # default=1000000000,#1B
    # default=30000000000,#30B
)
parser.add_argument(
    "--index_bits_shift",
    type=int,
    required=True,
    help="bank bits shift",
    default=0,
)
parser.add_argument(
    "--fully_util",
    type=int,
    required=True,
    help="duplicate processes to fully utilize all cores",
    default=0,
)

parser.add_argument(
    "--seed",
    type=int,
    required=True,
    help="random seed for random number generator",
)
parser.add_argument(
    "--run",
    type=int,
    required=False,
    help="index of this run",
)
parser.add_argument(
    "--anonymous_latency",
    type=bool,
    required=False,
    default=False,
    help="assign l2 latency regardless of size",
)

parser.add_argument(
    "--l2_list_capacity",
    type=int,
    required=False,
    default=8,
    help="list capcity knob",
)
parser.add_argument(
    "--l2_num_maptable_set",
    type=int,
    required=False,
    default=128,
    help="list capcity knob",
)
parser.add_argument(
    "--xor_policy",
    type=str,
    required=False,
    default="balanced",
    choices=["balanced", "synergy", "oppurtunistic"],
    help='l2 transitions per cycle (str)',
)
parser.add_argument('--record_line_level_entropy', action='store_true')
parser.add_argument('--no-record_line_level_entropy', dest='record_line_level_entropy', action='store_false')
parser.set_defaults(record_line_level_entropy=False)

parser.add_argument(
    "--xor_folding_scheme",
    type=int,
    required=False,
    help="xor folding scheme. 0 for dense byte label; 1 for sparse byte label TODO; 2 for hycomp;",
    default=0,
)

# parser.add_argument('--ooo', action='store_true')
# parser.add_argument('--no-ooo', dest='ooo', action='store_false')
# parser.set_defaults(ooo=False)

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
    "--l2size",
    type=str,
    required=False,
    default="256kB",
    help="l2size string",
    choices=["32kB", "64kB", "128kB","256kB","512kB", "1024kB", "2048kB"],
)
parser.add_argument(
    "--l2factor_xor_bdi",
    type=float,
    required=False,
    default=2.0,
    help="l2 data size reduction factor",
)
parser.add_argument(
    "--l2factor_xor",
    type=float,
    required=False,
    default=2.0,
    help="l2 data size reduction factor",
)
parser.add_argument(
    "--l2factor_bdi",
    type=float,
    required=False,
    default=2.0,
    help="l2 data size reduction factor",
)
parser.add_argument(
    "--l2_data_segment_size",
    type=int,
    required=False,
    default=1,
    help="l2 data array segment size in byte",
)
parser.add_argument(
    "--l2_data_regions",
    type=int,
    required=False,
    default=1,
    help="number of data regions",
)
parser.add_argument(
    "--l2_transitions_per_cycle",
    type=str,
    required=False,
    default="4",
    help='l2 transitions per cycle (str)',
)
parser.add_argument(
    "--l2_map_bits",
    type=int,
    required=False,
    default=8,
    help="map table hash fingerprint bits",
)
parser.add_argument(
    "--numProcesses",
    type=int,
    required=False,
    help="num of processes.",
    default=1,
)
parser.add_argument(
    "--protocol",
    type=str,
    help="which protocol to run",
    choices=["baseline", "noisy", "decoupled", "compress", "dedup","bdixor",
             "msi_nine_xor_bdi_map", "msi_nine_noxor_bdi_map",
             "msi_nine_xor_nobdi_map", "msi_nine_noxor_nobdi_map",
             "msi_exc_nobdi", "msi_exc_bdi",
             ],
    required=True,
)
parser.add_argument(
    "--ckpt_protocol",
    type=str,
    help="which protocol to run",
    choices=["hammer", "no",
             ],
    default="no",
    required=False,
)
parser.add_argument(
    "--ckpt_search_path",
    type=str,
    help="checkpoint search path",
    default="m5out",
    required=False,
)

parser.add_argument(
    "--ckpt_fastforward_insts",
    type=int,
    required=False,
    default=100000000000,
    help="checkpoint ff insts count",
)

args = parser.parse_args()
freq = args.frequency
random.seed(args.seed)

ckpt_path = f"{args.ckpt_search_path}/ckpt/fs_spec2017/{args.ckpt_protocol}_c{args.core}_proc{args.numProcesses}_seed{args.seed}_run{args.run}_ff{args.ckpt_fastforward_insts}/cpt"
# check if ckpt exists
if not os.path.exists(ckpt_path):
    print(f"ckpt not found: {ckpt_path}")
    exit(1)

specified_l2size = int(args.l2size.split('kB')[0])
if args.core < 10: pad=1
elif args.core < 100: pad=2
else: pad=3
numTag_tot = specified_l2size * 1024 / 64
print("numTag_tot=", numTag_tot)

# data_assoc = 4
# print("data_assoc=", data_assoc)

if args.anonymous_latency:
    l2_data_lat_map = { #TODO
        16: 5,
        32: 5,
        64: 5,
        128: 5,
        256: 5,
        512: 5,
        1024: 5,
        2048: 5,
    }
    l2_tag_lat_map = { #TODO
        16: 1,
        32: 1,
        64: 1,
        128: 1,
        256: 1,
        512: 1,
        1024: 1,
        2048: 1,
    }
    dir_data_lat_map = { #TODO
        16: 2,
        32: 2,
        64: 2,
        128: 2,
        256: 2,
        512: 2,
        1024: 2,
        2048: 2,
    }
    dir_tag_lat_map = { #TODO
        16: 2,
        32: 2,
        64: 2,
        128: 2,
        256: 2,
        512: 2,
        1024: 2,
        2048: 2,
    }
else:
    assert False
    

if args.fully_util == 1:
    import math
    from functools import reduce
    def lcm(arr): 
        l=reduce(lambda x,y:(x*y)//math.gcd(x,y),arr)
        return l
    assert args.run, "run should be specified!"
    assert args.core % args.numProcesses == 0
    times = args.core // args.numProcesses
    total_runs = lcm([args.numProcesses, len(benchmark_choices)]) // args.numProcesses
    print(f"total_runs: {total_runs}")
    assert args.run <= total_runs, f"run should be less than total_runs {total_runs}"
    repeat = total_runs * args.numProcesses // len(benchmark_choices)
    # benchmark_permutation = [benchmark_choices for i in range(repeat)]
    # index = 0
    benchmark_permutation = []
    for i in range(repeat):
        seed = int(args.seed + i)
        print(f"setting seed to {seed}")
        random.seed(seed)
        # random.shuffle(i)
        # benchmark_permutation[index] = i
        # index += 1
        import copy
        one_permutation = copy.deepcopy(benchmark_choices)
        random.shuffle(one_permutation)
        benchmark_permutation.append(one_permutation)

    # flatten benchmark_permutation to 1d list
    random.seed(args.seed)
    benchmark_permutation = [item for sublist in benchmark_permutation for item in sublist]
    print(f"benchmark_permutation: {benchmark_permutation}")
else:
    times = 1

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
if args.protocol == 'baseline':
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MESI_TWO_LEVEL,
        kvm_required=True,
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
elif args.protocol == 'msi':
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MSI_TWO_LEVEL,
        kvm_required=True,
    )

    from gem5.components.cachehierarchies.ruby.msi_two_level_cache_hierarchy import (
        MSITwoLevelCacheHierarchy,
    )
    cache_hierarchy = MSITwoLevelCacheHierarchy(
        l1d_size="32kB",
        l1d_assoc=4,
        l1i_size="32kB",
        l1i_assoc=4,
        l2_size=args.l2size,
        l2_assoc=8,
        num_l2_banks=args.core,
        l2_data_lat = l2_data_lat_map[specified_l2size],
        l2_tag_lat = l2_tag_lat_map[specified_l2size],
    )
elif args.protocol == 'msi_nine':
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MSI_TWO_LEVEL_NINE,
        kvm_required=True,
    )

    from gem5.components.cachehierarchies.ruby.msi_two_level_cache_hierarchy_nine import (
        MSITwoLevelNineCacheHierarchy,
    )
    l2size_in_kb = int(args.l2size.split('kB')[0])

    cache_hierarchy = MSITwoLevelNineCacheHierarchy(
        l1d_size="32kB",
        l1d_assoc=4,
        l1i_size="32kB",
        l1i_assoc=4,
        l2_size=args.l2size,
        l2_assoc=8,
        num_l2_banks=args.core,
        l2_data_lat = l2_data_lat_map[specified_l2size],
        l2_tag_lat = l2_tag_lat_map[specified_l2size],
        dir_data_lat = dir_data_lat_map[specified_l2size],
        dir_tag_lat = dir_tag_lat_map[specified_l2size],
        dir_cache_size=args.l2size,
        dir_cache_assoc=8,
        dir_l2_total_size=f"{2*l2size_in_kb}kB",#in KB
    )
elif args.protocol == 'msi_nine_xor_bdi_map':
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MSI_TWO_LEVEL_NINE_XOR_MAP,
        kvm_required=False,
    )

    from gem5.components.cachehierarchies.ruby.msi_two_level_cache_hierarchy_nine_xor_map import (
        MSITwoLevelNineXORMAPCacheHierarchy,
    )
    l2size_in_kb = int(args.l2size.split('kB')[0])
    l2_sector_number = 64*l2size_in_kb
    l2_sector_number = int(math.floor(l2_sector_number / args.l2factor_xor_bdi))
    
    if l2size_in_kb == 64 and args.l2factor_xor_bdi == 1.5:
        l2_sector_number = 2752
    if l2size_in_kb == 64 and args.l2factor_xor_bdi == 3:
        l2_sector_number = 1376
    if l2size_in_kb == 64 and args.l2factor_xor_bdi == 2.5:
        l2_sector_number = 1664

    cache_hierarchy = MSITwoLevelNineXORMAPCacheHierarchy(
        l1d_size="32kB",
        l1d_assoc=4,
        l1i_size="16kB",
        l1i_assoc=4,
        l2_tag_size = args.l2size,
        l2_tag_assoc = 8,
        l2_data_size=f"{l2_sector_number}kB",
        dir_cache_size = args.l2size,
        dir_cache_assoc = 8,
        dir_l2_total_size = f"{2*l2size_in_kb}kB",#in KB,
        num_l2_banks = args.core,
        l2_data_lat = l2_data_lat_map[int(specified_l2size/2)],
        l2_tag_lat = l2_tag_lat_map[specified_l2size],
        dir_data_lat = dir_data_lat_map[specified_l2size],
        dir_tag_lat = dir_tag_lat_map[specified_l2size],
        l2_map_bits=args.l2_map_bits,
        l2_list_capacity=args.l2_list_capacity,
        l2_num_maptable_set=args.l2_num_maptable_set,
        l2_compression="bdi",
        l2_data_array_segment_size_in_byte=args.l2_data_segment_size,
        l2_data_array_regions=args.l2_data_regions,
        record_line_level_entropy=args.record_line_level_entropy,
        xor_folding_scheme=args.xor_folding_scheme,
        xor_policy=args.xor_policy,
        l2_transitions_per_cycle=args.l2_transitions_per_cycle,
        index_bits_shift=args.index_bits_shift,
    )
elif args.protocol == 'msi_nine_xor_nobdi_map':
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MSI_TWO_LEVEL_NINE_XOR_MAP,
        kvm_required=False,
    )

    from gem5.components.cachehierarchies.ruby.msi_two_level_cache_hierarchy_nine_xor_map import (
        MSITwoLevelNineXORMAPCacheHierarchy,
    )
    l2size_in_kb = int(args.l2size.split('kB')[0])
    l2_sector_number = 64*l2size_in_kb
    l2_sector_number = int(math.floor(l2_sector_number / args.l2factor_xor))

    if l2size_in_kb == 64 and args.l2factor_xor == 1.5:
        l2_sector_number = 2752
    if l2size_in_kb == 64 and args.l2factor_xor == 3:
        l2_sector_number = 1376
    if l2size_in_kb == 64 and args.l2factor_xor == 2.5:
        l2_sector_number = 1664

    cache_hierarchy = MSITwoLevelNineXORMAPCacheHierarchy(
        l1d_size="32kB",
        l1d_assoc=4,
        l1i_size="16kB",
        l1i_assoc=4,
        l2_tag_size = args.l2size,
        l2_tag_assoc = 8,
        l2_data_size=f"{l2_sector_number}kB",
        dir_cache_size = args.l2size,
        dir_cache_assoc = 8,
        dir_l2_total_size = f"{2*l2size_in_kb}kB",#in KB,
        num_l2_banks = args.core,
        l2_data_lat = l2_data_lat_map[int(specified_l2size/2)],
        l2_tag_lat = l2_tag_lat_map[specified_l2size],
        dir_data_lat = dir_data_lat_map[specified_l2size],
        dir_tag_lat = dir_tag_lat_map[specified_l2size],
        l2_map_bits=args.l2_map_bits,
        l2_list_capacity=args.l2_list_capacity,
        l2_num_maptable_set=args.l2_num_maptable_set,
        l2_data_array_segment_size_in_byte=args.l2_data_segment_size,
        l2_data_array_regions=args.l2_data_regions,
        record_line_level_entropy=args.record_line_level_entropy,
        xor_folding_scheme=args.xor_folding_scheme,
        xor_policy=args.xor_policy,
        l2_transitions_per_cycle=args.l2_transitions_per_cycle,
    )
elif args.protocol == 'msi_nine_noxor_bdi_map':
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MSI_TWO_LEVEL_NINE_XOR_MAP,
        kvm_required=False,
    )

    from gem5.components.cachehierarchies.ruby.msi_two_level_cache_hierarchy_nine_noxor_map import (
        MSITwoLevelNineNoXORMAPCacheHierarchy,
    )
    l2size_in_kb = int(args.l2size.split('kB')[0])
    l2_sector_number = 64*l2size_in_kb
    l2_sector_number = int(math.floor(l2_sector_number / args.l2factor_bdi))
    if l2size_in_kb == 64 and args.l2factor_bdi == 1.5:
        l2_sector_number = 2752
    if l2size_in_kb == 64 and args.l2factor_bdi == 3:
        l2_sector_number = 1376
    if l2size_in_kb == 64 and args.l2factor_bdi == 2.5:
        l2_sector_number = 1664

    cache_hierarchy = MSITwoLevelNineNoXORMAPCacheHierarchy(
        l1d_size="32kB",
        l1d_assoc=4,
        l1i_size="16kB",
        l1i_assoc=4,
        l2_tag_size = args.l2size,
        l2_tag_assoc = 8,
        l2_data_size=f"{l2_sector_number}kB",
        dir_cache_size = args.l2size,
        dir_cache_assoc = 8,
        dir_l2_total_size = f"{2*l2size_in_kb}kB",#in KB,
        num_l2_banks = args.core,
        l2_data_lat = l2_data_lat_map[int(specified_l2size/2)],
        l2_tag_lat = l2_tag_lat_map[specified_l2size],
        dir_data_lat = dir_data_lat_map[specified_l2size],
        dir_tag_lat = dir_tag_lat_map[specified_l2size],
        l2_map_bits=args.l2_map_bits,
        l2_list_capacity=args.l2_list_capacity,
        l2_num_maptable_set=args.l2_num_maptable_set,
        l2_compression="bdi",
        l2_data_array_segment_size_in_byte=args.l2_data_segment_size,
        l2_data_array_regions=args.l2_data_regions,
        record_line_level_entropy=args.record_line_level_entropy,
        xor_folding_scheme=args.xor_folding_scheme,
        l2_transitions_per_cycle=args.l2_transitions_per_cycle,
    )
elif args.protocol == 'msi_nine_noxor_nobdi_map':
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MSI_TWO_LEVEL_NINE_XOR_MAP,
        kvm_required=False,
    )

    from gem5.components.cachehierarchies.ruby.msi_two_level_cache_hierarchy_nine_noxor_map import (
        MSITwoLevelNineNoXORMAPCacheHierarchy,
    )
    l2size_in_kb = int(args.l2size.split('kB')[0])
    l2_sector_number = 64*l2size_in_kb

    cache_hierarchy = MSITwoLevelNineNoXORMAPCacheHierarchy(
        l1d_size="32kB",
        l1d_assoc=4,
        l1i_size="16kB",
        l1i_assoc=4,
        l2_tag_size = args.l2size,
        l2_tag_assoc = 8,
        l2_data_size=f"{l2_sector_number}kB",
        dir_cache_size = args.l2size,
        dir_cache_assoc = 8,
        dir_l2_total_size = f"{2*l2size_in_kb}kB",#in KB,
        num_l2_banks = args.core,
        l2_data_lat = max(l2_data_lat_map[int(specified_l2size/2)], l2_tag_lat_map[int(specified_l2size/2)]),
        l2_tag_lat = max(l2_data_lat_map[int(specified_l2size/2)], l2_tag_lat_map[int(specified_l2size/2)]),
        dir_data_lat = dir_data_lat_map[specified_l2size],
        dir_tag_lat = dir_tag_lat_map[specified_l2size],
        l2_map_bits=args.l2_map_bits,
        l2_list_capacity=args.l2_list_capacity,
        l2_num_maptable_set=args.l2_num_maptable_set,
        l2_data_array_segment_size_in_byte=args.l2_data_segment_size,
        l2_data_array_regions=args.l2_data_regions,
        record_line_level_entropy=args.record_line_level_entropy,
        xor_folding_scheme=args.xor_folding_scheme,
        l2_transitions_per_cycle=args.l2_transitions_per_cycle,
    )
elif args.protocol == 'msi_exc_nobdi':
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MSI_TWO_LEVEL_EXC,
        kvm_required=False,
    )

    from gem5.components.cachehierarchies.ruby.msi_two_level_cache_hierarchy_exc import (
        MSITwoLevelExcCacheHierarchy,
    )
    l2size_in_kb = int(args.l2size.split('kB')[0])
    l2_sector_number = 64*l2size_in_kb

    cache_hierarchy = MSITwoLevelExcCacheHierarchy(
        l1d_size="32kB",
        l1d_assoc=4,
        l1i_size="16kB",
        l1i_assoc=4,
        l2_tag_size = args.l2size,
        l2_tag_assoc = 8,
        l2_data_size=f"{l2_sector_number}kB",
        dir_cache_size = args.l2size,
        dir_cache_assoc = 8,
        dir_l2_total_size = f"{2*l2size_in_kb}kB",#in KB,
        num_l2_banks = args.core,
        l2_data_lat = max(l2_data_lat_map[int(specified_l2size/2)], l2_tag_lat_map[int(specified_l2size/2)]),
        l2_tag_lat = max(l2_data_lat_map[int(specified_l2size/2)], l2_tag_lat_map[int(specified_l2size/2)]),
        dir_data_lat = dir_data_lat_map[specified_l2size],
        dir_tag_lat = dir_tag_lat_map[specified_l2size],
        l2_transitions_per_cycle=args.l2_transitions_per_cycle,
        l2_data_array_segment_size_in_byte=64,
        l2_data_array_regions=1,
        # l2_compression="bdi",
    )
elif args.protocol == 'msi_exc_bdi':
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MSI_TWO_LEVEL_EXC,
        kvm_required=False,
    )

    from gem5.components.cachehierarchies.ruby.msi_two_level_cache_hierarchy_exc import (
        MSITwoLevelExcCacheHierarchy,
    )
    l2size_in_kb = int(args.l2size.split('kB')[0])
    l2_sector_number = 64*l2size_in_kb
    l2_sector_number = int(math.floor(l2_sector_number / args.l2factor_bdi))
    if l2size_in_kb == 64 and args.l2factor_bdi == 1.5:
        l2_sector_number = 2752
    if l2size_in_kb == 64 and args.l2factor_bdi == 3:
        l2_sector_number = 1376
    if l2size_in_kb == 64 and args.l2factor_bdi == 2.5:
        l2_sector_number = 1664

    cache_hierarchy = MSITwoLevelExcCacheHierarchy(
        l1d_size="32kB",
        l1d_assoc=4,
        l1i_size="16kB",
        l1i_assoc=4,
        l2_tag_size = args.l2size,
        l2_tag_assoc = 8,
        l2_data_size=f"{l2_sector_number}kB",
        dir_cache_size = args.l2size,
        dir_cache_assoc = 8,
        dir_l2_total_size = f"{2*l2size_in_kb}kB",#in KB,
        num_l2_banks = args.core,
        l2_data_lat = max(l2_data_lat_map[int(specified_l2size/2)], l2_tag_lat_map[int(specified_l2size/2)]),
        l2_tag_lat = max(l2_data_lat_map[int(specified_l2size/2)], l2_tag_lat_map[int(specified_l2size/2)]),
        dir_data_lat = dir_data_lat_map[specified_l2size],
        dir_tag_lat = dir_tag_lat_map[specified_l2size],
        l2_transitions_per_cycle=args.l2_transitions_per_cycle,
        l2_data_array_segment_size_in_byte=args.l2_data_segment_size,
        l2_data_array_regions=args.l2_data_regions,
        l2_compression="bdi",
    )
else:
    print("Unknown protocol")
    exit(1)

# Memory: Dual Channel DDR4 2400 DRAM device.
# The X86 board only supports 3 GB of main memory.

memory = DualChannelDDR4_2400(size="3GB")
# memory = SingleChannelSimpleMemory("50ns", "0ns", "19.2GB/s", size="3GB")

# Here we setup the processor. This is a special switchable processor in which
# a starting core type and a switch core type must be specified. Once a
# configuration is instantiated a user may call `processor.switch()` to switch
# from the starting core types to the switch core types. In this simulation
# we start with KVM cores to simulate the OS boot, then switch to the Timing
# cores for the command we wish to run after boot.

processor = SimpleProcessor(
    cpu_type=CPUTypes.TIMING, isa=ISA.X86, num_cores=args.core
    # cpu_type=CPUTypes.ATOMIC, isa=ISA.X86, num_cores=args.core
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
selected_bench_arr = []
index_arr = []
starting_loc = (args.run-1) * args.numProcesses
for i in range(args.numProcesses):
    assert benchmark_permutation, "benchmark_permutation should not be empty!"
    selected_bench = benchmark_permutation[starting_loc + i]

    for j in range(times):
        selected_bench_arr.append(selected_bench)


out = ""
# add build/setup instructions
selected_benchs = " ".join(selected_bench_arr)
out += f'runcpu --size {args.size} --iterations 1  --action runsetup --config myconfig.x86.cfg --define gcc_dir="/usr" --noreportable --nobuild {selected_benchs}\n' \
    f'm5 exit\n'

# add run instructions
for i in range(len(selected_bench_arr)):
    selected_bench = selected_bench_arr[i]
    i_hex = hex(2**i)
    # out += f'taskset {i_hex} runcpu --size {args.size} --iterations 1  --action runsetup --config myconfig.x86.cfg --define gcc_dir="/usr" --noreportable --nobuild {selected_bench} &\n'
    # out += f'( cd /home/gem5/spec2017/benchspec/CPU/{selected_bench}/run/run_base_refrate_mytest-m64.0000; echo "starting {selected_bench}!"; taskset {i_hex} specinvoke ; echo "{selected_bench} done!" ) &\n'
    out += (
        f'( \n'
        f'  cd /home/gem5/spec2017/benchspec/CPU/{selected_bench}/run/run_base_refrate_mytest-m64.0000\n'
        f'  count=1\n'
        f'  while true; do\n'
        f'      echo "starting {selected_bench} run ${{count}}!"\n'
        f'      taskset {i_hex} specinvoke\n'
        f'      echo "{selected_bench}  run ${{count}} done!"\n'
        f"      ((count++))\n"
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
from gem5.resources.resource import CustomResource
board.set_kernel_disk_workload(
    # The x86 linux kernel will be automatically downloaded to the
    # `~/.cache/gem5` directory if not already present.
    # SPEC CPU2017 benchamarks were tested with kernel version 4.19.83
    checkpoint=CustomResource(ckpt_path),
    # kernel=Resource("x86-linux-kernel-4.19.83"),

    kernel=CustomResource("x86-linux-kernel-4.19.83"),
    # The location of the x86 SPEC CPU 2017 image
    disk_image=CustomDiskImageResource(
        args.image, disk_root_partition=args.partition
    ),
    readfile_contents=command,
)



# We need this for long running processes.
m5.disableAllListeners()

root = Root(full_system=True, system=board)
board._pre_instantiate()
m5.instantiate(board._checkpoint.as_posix())

# We maintain the wall clock time.

globalStart = time.time()

print("Running the simulation")

start_tick = m5.curTick()
end_tick = m5.curTick()
m5.stats.reset()

for i in range(args.core):
    processor.get_cores()[i].core.scheduleInstStop(0, args.detailed_inst, "m5_workend instruction encountered")
num_workend_seen = 0

core_fin_set = set()
cumulated_stats_line = 0
ipc_roi_per_core = []
for i in range(args.core):
    ipc_roi_per_core.append(-1)
while True:
    exit_event = m5.simulate()

    if exit_event.getCause() == "m5_workend instruction encountered":
        num_workend_seen += 1
        core_fin = -1

        gem5stats = get_simstat(root)
        if args.core == 1: 
            core_fin = 0
            total_insts = float(gem5stats.to_json()["system"]["processor"][f"cores"]["core"][
                "exec_context.thread_0"]["numInsts"]["value"])
            assert total_insts == args.detailed_inst, f"total_insts: {total_insts}, args.detailed_inst: {args.detailed_inst}"
        else: 
            for i in range(args.core):
                if i in core_fin_set: continue
                total_insts = float(gem5stats.to_json()["system"]["processor"][f"cores{i}"]["core"][
                    "exec_context.thread_0"]["numInsts"]["value"])
                if total_insts == args.detailed_inst:
                    core_fin = i
                    core_fin_set.add(i)
                    break
            assert core_fin != -1, f"core_fin: {core_fin}"

        end_tick = m5.curTick()
        duration_ticks = end_tick - start_tick
        duration_cycles = get_cycle_from_tick(duration_ticks, freq)
        ipc_core_fin = float(total_insts) / duration_cycles
        ipc_roi_per_core[core_fin] = ipc_core_fin
        print(f"Finished detailed sim for {args.detailed_inst} instructions core {core_fin} with ipc of {ipc_core_fin}")
        m5.stats.dump()
        # copy stats.txt file at this point to stats.{core_fin}.txt
        import shutil
        orig_stats = os.path.join(m5.options.outdir, "stats.txt")
        new_stats = os.path.join(m5.options.outdir, f"stats.{core_fin}.txt")
        # shutil.copyfile(orig_stats, new_stats)

        # count the number of lines in stats.txt
        with open(orig_stats, 'r') as f: cur_stats_lines = len(f.readlines())

        # if cumulated_stats_line != 0:
        # keep only cur_stats_lines - cumulated_stats_lines lines in new_stats
        with open(orig_stats, 'r') as f: lines = f.readlines()
        with open(new_stats, 'w') as f: f.writelines(lines[cumulated_stats_line:cur_stats_lines])
        print(f"stats.txt now has {cur_stats_lines} lines, save line {cumulated_stats_line} to {cur_stats_lines} to {new_stats}")
        cumulated_stats_line = cur_stats_lines


        if num_workend_seen == args.core:
            print(f"Finished detailed sim for {args.detailed_inst} instructions on every core")
            print("Dump stats at the end of the ROI!")

            ############### process stats ###############
            end_tick = m5.curTick()
            duration_ticks = end_tick - start_tick
            duration_cycles = get_cycle_from_tick(duration_ticks, freq)
            gem5stats = get_simstat(root)
            duration_start_tick = m5.curTick()

            duration_insts = []
            total_insts_arr = []
            if args.core == 1:
                total_insts = float(gem5stats.to_json()["system"]["processor"][f"cores"]["core"][
                        "exec_context.thread_0"]["numInsts"]["value"])
                total_insts_arr.append(total_insts)
            else:
                for i in range(args.core):
                    total_insts = float(gem5stats.to_json()["system"]["processor"][f"cores{i}"]["core"][
                        "exec_context.thread_0"]["numInsts"]["value"])
                    total_insts_arr.append(total_insts)
            ipc_running_avg = [float(i)/get_cycle_from_tick(end_tick-start_tick, freq) if i != 0 else 0.0 for i in total_insts_arr]
            
            print(f"IPC running avg: {ipc_running_avg}")
            break
    else:
        print("Unexpected termination of simulation while ROI was being executed!")
        print(
            "Exiting @ tick {} because {}.".format(
                m5.curTick(), exit_event.getCause()
            )
        )
        exit(-1)

end_tick = m5.curTick()
# ROI has ended here, and we get `simInsts` using get_simstat and print it in
# the final print statement.

gem5stats = get_simstat(root)

# We get the number of committed instructions from the timing
# cores. We then sum and print them at the end.
total_insts_arr = []
if args.core == 1:
    total_insts = float(gem5stats.to_json()["system"]["processor"][f"cores"]["core"][
            "exec_context.thread_0"]["numInsts"]["value"])
    total_insts_arr.append(total_insts)
else:
    for i in range(args.core):
        total_insts = float(gem5stats.to_json()["system"]["processor"][f"cores{i}"]["core"][
            "exec_context.thread_0"]["numInsts"]["value"])
        total_insts_arr.append(total_insts)
ipc = [float(i)/get_cycle_from_tick(end_tick-start_tick, freq) for i in total_insts_arr]

print("Done with the simulation")
print()
print("Performance statistics:")

print("Simulated time in ROI: %.2fs" % ((end_tick - start_tick) / 1e12))
print(f"Instructions executed in ROI: {total_insts_arr}")
print(f"ipc ROI: {ipc}")
print(f"ipc ROI per core: {ipc_roi_per_core}")
print("Ran a total of", m5.curTick() / 1e12, "simulated seconds")
print(
    "Total wallclock time: %.2fs, %.2f min"
    % (time.time() - globalStart, (time.time() - globalStart) / 60)
)
