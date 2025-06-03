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
    # default=500000000,#0.5B
    default=1000000000,#1B
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
parser.add_argument(
    "--cachecfg",
    type=str,
    required=True,
    help="for 3 level cache, choose either skylake or worse",
    choices=["skylake", "realistic", "size512kB", "size2048kB"],
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

parser.add_argument('--tagptr', action='store_true')
parser.add_argument('--no-tagptr', dest='tagptr', action='store_false')
parser.set_defaults(tagptr=True)

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
    "--llc_lat",
    type=int,
    required=False,
    default=40,
    help='llc latency',
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
    choices=[
             "mesi3", "msi_nine_noxor_nobdi_map3", 
             "msi_exc3", "msi_exc_bdi3",
             "msi_nine_xor_bdi_map3", "msi_nine_xor_thesaurus_map3", 
             "msi_nine_noxor_bdi_map3", "msi_nine_noxor_thesaurus_map3", 
             "msi_nine_xor_nobdi_map3",
             "msi_nine_noxor_bpc_map3",
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

if args.core < 10: pad=1
elif args.core < 100: pad=2
else: pad=3
# default latencies
l2_tag_lat = 2
l2_data_lat = 10
l3_tag_lat = 4
l3_data_lat = 40
dir_tag_lat = 2
dir_data_lat = 4

if args.llc_lat:
    l3_data_lat = args.llc_lat

    

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
# Caches: MESI Three Level Cache Hierarchy
if args.protocol == 'mesi3':
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MESI_THREE_LEVEL_NINE,
        kvm_required=False,
    )
    from gem5.components.cachehierarchies.ruby.mesi_three_level_cache_hierarchy_nine import (
        MESIThreeLevelCacheHierarchyNINE,
    )
    if args.cachecfg == "skylake":
        cache_hierarchy = MESIThreeLevelCacheHierarchyNINE(
            l1d_size="32kB",
            l1d_assoc=8,
            l1i_size="32kB",
            l1i_assoc=8,
            l2_size="1024kB",
            l2_assoc=16,
            l3_tag_size="1408kB",
            l3_tag_assoc=11,
            dir_cache_size="1408kB",
            dir_cache_assoc=11,
            l3_total_size="2816kB",
            num_l3_banks=args.core,
        )
    elif args.cachecfg == "realistic":
        cache_hierarchy = MESIThreeLevelCacheHierarchyNINE(
            l1d_size="32kB",
            l1d_assoc=4,
            l1i_size="32kB",
            l1i_assoc=4,
            l2_size="256kB",
            l2_assoc=8,
            l3_tag_size="1024kB",
            l3_tag_assoc=16,
            dir_cache_size="1024kB",
            dir_cache_assoc=16,
            l3_total_size="2048kB",
            num_l3_banks=args.core,
        )
    elif args.cachecfg == "size512kB":
        cache_hierarchy = MESIThreeLevelCacheHierarchyNINE(
            l1d_size="32kB",
            l1d_assoc=4,
            l1i_size="32kB",
            l1i_assoc=4,
            l2_size="256kB",
            l2_assoc=8,
            l3_tag_size="512kB",
            l3_tag_assoc=16,
            dir_cache_size="512kB",
            dir_cache_assoc=16,
            l3_total_size="1024kB",
            num_l3_banks=args.core,
        )
    elif args.cachecfg == "size2048kB":
        cache_hierarchy = MESIThreeLevelCacheHierarchyNINE(
            l1d_size="32kB",
            l1d_assoc=4,
            l1i_size="32kB",
            l1i_assoc=4,
            l2_size="256kB",
            l2_assoc=8,
            l3_tag_size="2048kB",
            l3_tag_assoc=16,
            dir_cache_size="2048kB",
            dir_cache_assoc=16,
            l3_total_size="4096kB",
            num_l3_banks=args.core,
        )
elif args.protocol == 'msi_exc3':
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MSI_THREE_LEVEL_EXC,
        kvm_required=False,
    )
    from gem5.components.cachehierarchies.ruby.msi_three_level_cache_hierarchy_exc import (
        MSIThreeLevelExcCacheHierarchy,
    )
    if args.cachecfg == "skylake":
        assert False
        l3size_in_kb = 384 #3.67 comp ratio
        l3_sector_number = 64*l3size_in_kb
        l3_assoc = 13

        cache_hierarchy = MSIThreeLevelExcCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=8,
            l1i_size="32kB",
            l1i_assoc=8,
            l2_size="1024kB",
            l2_assoc=16,
            l3_tag_size=f"{l3size_in_kb}kB",
            l3_tag_assoc=l3_assoc,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size=f"{l3size_in_kb}kB",
            dir_cache_assoc=l3_assoc,
            dir_l3_total_size=f"{2*l3size_in_kb}kB",
            num_l3_banks=args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
            l3_data_array_segment_size_in_byte=64,
            l3_data_array_regions=1,
        )
    elif args.cachecfg == "realistic":
        l3size_in_kb = 832 #1.23 comp ratio
        l3_sector_number = 64*l3size_in_kb
        l3_assoc = 13

        cache_hierarchy = MSIThreeLevelExcCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=4,
            l1i_size="32kB",
            l1i_assoc=4,
            l2_size="256kB",
            l2_assoc=8,
            l3_tag_size=f"{l3size_in_kb}kB",
            l3_tag_assoc=l3_assoc,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size=f"{l3size_in_kb}kB",
            dir_cache_assoc=l3_assoc,
            dir_l3_total_size=f"{2*l3size_in_kb}kB",
            num_l3_banks=args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
            l3_data_array_segment_size_in_byte=64,
            l3_data_array_regions=1,
        )
    elif args.cachecfg == "size512kB" or args.cachecfg == "size2048kB":
        if args.cachecfg == "size512kB":
            l3size_in_kb = int(832 / 2)#1.23 comp ratio
        elif args.cachecfg == "size2048kB":
            l3size_in_kb = int(832 * 2)
        else: assert False
        l3_sector_number = 64*l3size_in_kb
        l3_assoc = 13

        cache_hierarchy = MSIThreeLevelExcCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=4,
            l1i_size="32kB",
            l1i_assoc=4,
            l2_size="256kB",
            l2_assoc=8,
            l3_tag_size=f"{l3size_in_kb}kB",
            l3_tag_assoc=l3_assoc,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size=f"{l3size_in_kb}kB",
            dir_cache_assoc=l3_assoc,
            dir_l3_total_size=f"{2*l3size_in_kb}kB",
            num_l3_banks=args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
            l3_data_array_segment_size_in_byte=64,
            l3_data_array_regions=1,
        )
elif args.protocol == 'msi_exc_bdi3':
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MSI_THREE_LEVEL_EXC,
        kvm_required=False,
    )
    from gem5.components.cachehierarchies.ruby.msi_three_level_cache_hierarchy_exc import (
        MSIThreeLevelExcCacheHierarchy,
    )
    if args.cachecfg == "skylake":
        assert False
        l3size_in_kb = 384 #3.67 comp ratio
        l3_sector_number = 64*l3size_in_kb
        l3_assoc = 13

        cache_hierarchy = MSIThreeLevelExcCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=8,
            l1i_size="32kB",
            l1i_assoc=8,
            l2_size="1024kB",
            l2_assoc=16,
            l3_tag_size=f"{l3size_in_kb}kB",
            l3_tag_assoc=l3_assoc,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size=f"{l3size_in_kb}kB",
            dir_cache_assoc=l3_assoc,
            dir_l3_total_size=f"{2*l3size_in_kb}kB",
            num_l3_banks=args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
            l3_data_array_segment_size_in_byte=64,
            l3_data_array_regions=1,
            l3_compression="bdi",
        )
    elif args.cachecfg == "realistic":
        l3size_in_kb = 832 #1.33 comp ratio
        l3_sector_number = 40960
        l3_assoc = 13

        cache_hierarchy = MSIThreeLevelExcCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=4,
            l1i_size="32kB",
            l1i_assoc=4,
            l2_size="256kB",
            l2_assoc=8,
            l3_tag_size=f"{l3size_in_kb}kB",
            l3_tag_assoc=l3_assoc,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size=f"{l3size_in_kb}kB",
            dir_cache_assoc=l3_assoc,
            dir_l3_total_size=f"{2*l3size_in_kb}kB",
            num_l3_banks=args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
            l3_data_array_segment_size_in_byte=args.l2_data_segment_size,
            l3_data_array_regions=args.l2_data_regions,
            l3_compression="bdi",
        )
    elif args.cachecfg == "size512kB" or args.cachecfg == "size2048kB":
        if args.cachecfg == "size512kB":
            l3size_in_kb = int(832 / 2) #1.33 comp ratio
            l3_sector_number = int(40960 / 2)
        elif args.cachecfg == "size2048kB":
            l3size_in_kb = int(832 * 2)
            l3_sector_number = int(40960 * 2)
        else : assert False
        l3_assoc = 13

        cache_hierarchy = MSIThreeLevelExcCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=4,
            l1i_size="32kB",
            l1i_assoc=4,
            l2_size="256kB",
            l2_assoc=8,
            l3_tag_size=f"{l3size_in_kb}kB",
            l3_tag_assoc=l3_assoc,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size=f"{l3size_in_kb}kB",
            dir_cache_assoc=l3_assoc,
            dir_l3_total_size=f"{2*l3size_in_kb}kB",
            num_l3_banks=args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
            l3_data_array_segment_size_in_byte=args.l2_data_segment_size,
            l3_data_array_regions=args.l2_data_regions,
            l3_compression="bdi",
        )

elif args.protocol == 'msi_nine_xor_bdi_map3':
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MSI_THREE_LEVEL_NINE_XOR_MAP,
        kvm_required=False,
    )

    from gem5.components.cachehierarchies.ruby.msi_three_level_cache_hierarchy_nine_xor_map import (
        MSIThreeLevelNineXORMAPCacheHierarchy,
    )
    if args.cachecfg == "skylake":
        l3size_in_kb = 1408
        l3_sector_number = 64*l3size_in_kb
        l3_sector_number = int(math.floor(l3_sector_number / args.l2factor_xor_bdi))
        
        if l3size_in_kb == 1408 and args.l2factor_xor_bdi == 1.5:
            l3_sector_number = 59392
        elif l3size_in_kb == 1408 and args.l2factor_xor_bdi == 3:
            l3_sector_number = 30048
        elif l3size_in_kb == 1408 and args.l2factor_xor_bdi == 2.5:
            l3_sector_number = 35840
        elif l3size_in_kb == 1408 and args.l2factor_xor_bdi == 1:
            l3_sector_number = 90112
        else: assert False, f"l3size_in_kb={l3size_in_kb}, l2factor_xor_bdi={args.l2factor_xor_bdi}"

        cache_hierarchy = MSIThreeLevelNineXORMAPCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=8,
            l1i_size="32kB",
            l1i_assoc=8,

            l2_size = "1024kB",
            l2_assoc = 16,

            l3_tag_size = f"{l3size_in_kb}kB",
            l3_tag_assoc = 11,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size = f"{l3size_in_kb}kB",
            dir_cache_assoc = 11,
            dir_l3_total_size = f"{2*l3size_in_kb}kB",#in KB,
            num_l3_banks = args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_map_bits=args.l2_map_bits,
            l3_list_capacity=args.l2_list_capacity,
            l3_num_maptable_set=args.l2_num_maptable_set,
            l3_compression="bdi",
            l3_data_array_segment_size_in_byte=args.l2_data_segment_size,
            l3_tagptr_size_in_bit=15 if args.tagptr else 0, #depends on number of l3 tags
            l3_data_array_regions=args.l2_data_regions,
            record_line_level_entropy=args.record_line_level_entropy,
            xor_folding_scheme=args.xor_folding_scheme,
            xor_policy=args.xor_policy,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
            index_bits_shift=args.index_bits_shift,
        )
    elif args.cachecfg == "realistic":
        l3size_in_kb = 1024
        l3_sector_number = 64*l3size_in_kb
        l3_sector_number = int(math.floor(l3_sector_number / args.l2factor_xor_bdi))
        
        if l3size_in_kb == 1024 and args.l2factor_xor_bdi == 1.5:
            l3_sector_number = 40960
        elif l3size_in_kb == 1024 and args.l2factor_xor_bdi == 3:
            l3_sector_number = 20480
        elif l3size_in_kb == 1024 and args.l2factor_xor_bdi == 2.5:
            l3_sector_number = 24576
        elif l3size_in_kb == 1024 and args.l2factor_xor_bdi == 2:
            l3_sector_number = 32768
        else: assert False

        cache_hierarchy = MSIThreeLevelNineXORMAPCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=4,
            l1i_size="32kB",
            l1i_assoc=4,

            l2_size = "256kB",
            l2_assoc = 8,

            l3_tag_size = f"{l3size_in_kb}kB",
            l3_tag_assoc = 16,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size = f"{l3size_in_kb}kB",
            dir_cache_assoc = 16,
            dir_l3_total_size = f"{2*l3size_in_kb}kB",#in KB,
            num_l3_banks = args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_map_bits=args.l2_map_bits,
            l3_list_capacity=args.l2_list_capacity,
            l3_num_maptable_set=args.l2_num_maptable_set,
            l3_compression="bdi",
            l3_data_array_segment_size_in_byte=args.l2_data_segment_size,
            l3_tagptr_size_in_bit=14 if args.tagptr else 0, #depends on number of l3 tags
            l3_data_array_regions=args.l2_data_regions,
            record_line_level_entropy=args.record_line_level_entropy,
            xor_folding_scheme=args.xor_folding_scheme,
            xor_policy=args.xor_policy,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
            index_bits_shift=args.index_bits_shift,
        )
    elif args.cachecfg == "size512kB" or args.cachecfg == "size2048kB":
        if args.cachecfg == "size512kB":
            l3size_in_kb = int(1024/2)
            l3_sector_number = 64*l3size_in_kb
            l3_sector_number = int(math.floor(l3_sector_number / args.l2factor_xor_bdi))
            
            if l3size_in_kb == int(1024/2) and args.l2factor_xor_bdi == 1.5:
                l3_sector_number = int(40960/2)
            elif l3size_in_kb == int(1024/2) and args.l2factor_xor_bdi == 3:
                l3_sector_number = int(20480/2)
            elif l3size_in_kb == int(1024/2) and args.l2factor_xor_bdi == 2.5:
                l3_sector_number = int(24576/2)
            elif l3size_in_kb == int(1024/2) and args.l2factor_xor_bdi == 2:
                l3_sector_number = int(32768/2)
            else: assert False
        elif args.cachecfg == "size2048kB":
            l3size_in_kb = int(1024*2)
            l3_sector_number = 64*l3size_in_kb
            l3_sector_number = int(math.floor(l3_sector_number / args.l2factor_xor_bdi))
            
            if l3size_in_kb == int(1024*2) and args.l2factor_xor_bdi == 1.5:
                l3_sector_number = int(40960*2)
            elif l3size_in_kb == int(1024*2) and args.l2factor_xor_bdi == 3:
                l3_sector_number = int(20480*2)
            elif l3size_in_kb == int(1024*2) and args.l2factor_xor_bdi == 2.5:
                l3_sector_number = int(24576*2)
            elif l3size_in_kb == int(1024*2) and args.l2factor_xor_bdi == 2:
                l3_sector_number = int(32768*2)
            else: assert False
        else: assert False


        cache_hierarchy = MSIThreeLevelNineXORMAPCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=4,
            l1i_size="32kB",
            l1i_assoc=4,

            l2_size = "256kB",
            l2_assoc = 8,

            l3_tag_size = f"{l3size_in_kb}kB",
            l3_tag_assoc = 16,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size = f"{l3size_in_kb}kB",
            dir_cache_assoc = 16,
            dir_l3_total_size = f"{2*l3size_in_kb}kB",#in KB,
            num_l3_banks = args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_map_bits=args.l2_map_bits,
            l3_list_capacity=args.l2_list_capacity,
            l3_num_maptable_set=args.l2_num_maptable_set,
            l3_compression="bdi",
            l3_data_array_segment_size_in_byte=args.l2_data_segment_size,
            l3_tagptr_size_in_bit=14 if args.tagptr else 0, #depends on number of l3 tags
            l3_data_array_regions=args.l2_data_regions,
            record_line_level_entropy=args.record_line_level_entropy,
            xor_folding_scheme=args.xor_folding_scheme,
            xor_policy=args.xor_policy,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
            index_bits_shift=args.index_bits_shift,
        )
    else: assert False
elif args.protocol == 'msi_nine_xor_thesaurus_map3':
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MSI_THREE_LEVEL_NINE_XOR_MAP_THESAURUS,
        kvm_required=False,
    )

    from gem5.components.cachehierarchies.ruby.msi_three_level_cache_hierarchy_nine_xor_map_thesaurus import (
        MSIThreeLevelNineXORMAPCacheHierarchy,
    )
    if args.cachecfg == "realistic":
        l3size_in_kb = 1024
        l3_sector_number = 64*l3size_in_kb
        l3_sector_number = int(math.floor(l3_sector_number / args.l2factor_xor_bdi))
        
        if l3size_in_kb == 1024 and args.l2factor_xor_bdi == 1.5:
            l3_sector_number = 40960
        elif l3size_in_kb == 1024 and args.l2factor_xor_bdi == 3:
            l3_sector_number = 20480
        elif l3size_in_kb == 1024 and args.l2factor_xor_bdi == 2.5:
            l3_sector_number = 24576
        elif l3size_in_kb == 1024 and args.l2factor_xor_bdi == 2:
            l3_sector_number = 32768
        else: assert False

        cache_hierarchy = MSIThreeLevelNineXORMAPCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=4,
            l1i_size="32kB",
            l1i_assoc=4,

            l2_size = "256kB",
            l2_assoc = 8,

            l3_tag_size = f"{l3size_in_kb}kB",
            l3_tag_assoc = 16,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size = f"{l3size_in_kb}kB",
            dir_cache_assoc = 16,
            dir_l3_total_size = f"{2*l3size_in_kb}kB",#in KB,
            num_l3_banks = args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_map_bits=args.l2_map_bits,
            l3_list_capacity=args.l2_list_capacity,
            l3_num_maptable_set=args.l2_num_maptable_set,
            l3_data_array_segment_size_in_byte=args.l2_data_segment_size,
            l3_tagptr_size_in_bit=14 if args.tagptr else 0, #depends on number of l3 tags
            l3_data_array_regions=args.l2_data_regions,
            record_line_level_entropy=args.record_line_level_entropy,
            xor_folding_scheme=args.xor_folding_scheme,
            xor_policy=args.xor_policy,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
            index_bits_shift=args.index_bits_shift,
        )
    elif args.cachecfg == "size512kB" or args.cachecfg == "size2048kB":
        if args.cachecfg == "size512kB":
            l3size_in_kb = int(1024/2)
            l3_sector_number = 64*l3size_in_kb
            l3_sector_number = int(math.floor(l3_sector_number / args.l2factor_xor_bdi))
            
            if l3size_in_kb == int(1024/2) and args.l2factor_xor_bdi == 1.5:
                l3_sector_number = int(40960/2)
            elif l3size_in_kb == int(1024/2) and args.l2factor_xor_bdi == 3:
                l3_sector_number = int(20480/2)
            elif l3size_in_kb == int(1024/2) and args.l2factor_xor_bdi == 2.5:
                l3_sector_number = int(24576/2)
            elif l3size_in_kb == int(1024/2) and args.l2factor_xor_bdi == 2:
                l3_sector_number = int(32768/2)
            else: assert False
        elif args.cachecfg == "size2048kB":
            l3size_in_kb = int(1024*2)
            l3_sector_number = 64*l3size_in_kb
            l3_sector_number = int(math.floor(l3_sector_number / args.l2factor_xor_bdi))
            
            if l3size_in_kb == int(1024*2) and args.l2factor_xor_bdi == 1.5:
                l3_sector_number = int(40960*2)
            elif l3size_in_kb == int(1024*2) and args.l2factor_xor_bdi == 3:
                l3_sector_number = int(20480*2)
            elif l3size_in_kb == int(1024*2) and args.l2factor_xor_bdi == 2.5:
                l3_sector_number = int(24576*2)
            elif l3size_in_kb == int(1024*2) and args.l2factor_xor_bdi == 2:
                l3_sector_number = int(32768*2)
            else: assert False
        else: assert False


        cache_hierarchy = MSIThreeLevelNineXORMAPCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=4,
            l1i_size="32kB",
            l1i_assoc=4,

            l2_size = "256kB",
            l2_assoc = 8,

            l3_tag_size = f"{l3size_in_kb}kB",
            l3_tag_assoc = 16,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size = f"{l3size_in_kb}kB",
            dir_cache_assoc = 16,
            dir_l3_total_size = f"{2*l3size_in_kb}kB",#in KB,
            num_l3_banks = args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_map_bits=args.l2_map_bits,
            l3_list_capacity=args.l2_list_capacity,
            l3_num_maptable_set=args.l2_num_maptable_set,
            l3_data_array_segment_size_in_byte=args.l2_data_segment_size,
            l3_tagptr_size_in_bit=14 if args.tagptr else 0, #depends on number of l3 tags
            l3_data_array_regions=args.l2_data_regions,
            record_line_level_entropy=args.record_line_level_entropy,
            xor_folding_scheme=args.xor_folding_scheme,
            xor_policy=args.xor_policy,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
            index_bits_shift=args.index_bits_shift,
        )
    else: assert False
elif args.protocol == 'msi_nine_xor_nobdi_map3':
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MSI_THREE_LEVEL_NINE_XOR_MAP,
        kvm_required=False,
    )

    from gem5.components.cachehierarchies.ruby.msi_three_level_cache_hierarchy_nine_xor_map import (
        MSIThreeLevelNineXORMAPCacheHierarchy,
    )
    if args.cachecfg == "skylake":
        l3size_in_kb = 1408
        if l3size_in_kb == 1408 and args.l2factor_xor == 1.5:
            l3_sector_number = 59392
        elif l3size_in_kb == 1408 and args.l2factor_xor == 2:
            l3_sector_number = 45056
        elif l3size_in_kb == 1408 and args.l2factor_xor == 2.5:
            l3_sector_number = 35840
        elif l3size_in_kb == 1408 and args.l2factor_xor == 3:
            l3_sector_number = 30048
        elif l3size_in_kb == 1408 and args.l2factor_xor == 1:
            l3_sector_number = 90112
        else: assert False

        cache_hierarchy = MSIThreeLevelNineXORMAPCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=8,
            l1i_size="32kB",
            l1i_assoc=8,

            l2_size="1024kB",
            l2_assoc=16,

            l3_tag_size = f"{l3size_in_kb}kB",
            l3_tag_assoc = 11,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size = f"{l3size_in_kb}kB",
            dir_cache_assoc = 11,
            dir_l3_total_size = f"{2*l3size_in_kb}kB",#in KB,
            num_l3_banks = args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_map_bits=args.l2_map_bits,
            l3_list_capacity=args.l2_list_capacity,
            l3_num_maptable_set=args.l2_num_maptable_set,
            l3_data_array_segment_size_in_byte=args.l2_data_segment_size,
            l3_tagptr_size_in_bit=0, #depends on number of l3 tags
            l3_data_array_regions=args.l2_data_regions,
            record_line_level_entropy=args.record_line_level_entropy,
            xor_folding_scheme=args.xor_folding_scheme,
            xor_policy=args.xor_policy,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
        )
    elif args.cachecfg == "realistic":
        l3size_in_kb = 1024
        l3_sector_number = 64*l3size_in_kb
        l3_sector_number = int(math.floor(l3_sector_number / args.l2factor_xor))

        if l3size_in_kb == 1024 and args.l2factor_xor == 1.5:
            l3_sector_number = 40960
        elif l3size_in_kb == 1024 and args.l2factor_xor == 3:
            l3_sector_number = 20480
        elif l3size_in_kb == 1024 and args.l2factor_xor == 2.5:
            l3_sector_number = 24576
        elif l3size_in_kb == 1024 and args.l2factor_xor == 2:
            l3_sector_number = 32768
        else: assert False

        cache_hierarchy = MSIThreeLevelNineXORMAPCacheHierarchy(
        l1d_size="32kB",
        l1d_assoc=4,
        l1i_size="32kB",
        l1i_assoc=4,

        l2_size="256kB",
        l2_assoc=8,

        l3_tag_size = f"{l3size_in_kb}kB",
        l3_tag_assoc = 16,
        l3_data_size=f"{l3_sector_number}kB",
        dir_cache_size = f"{l3size_in_kb}kB",
        dir_cache_assoc = 16,
        dir_l3_total_size = f"{2*l3size_in_kb}kB",#in KB,
        num_l3_banks = args.core,
        l3_data_lat = l3_data_lat,
        l3_tag_lat = l3_tag_lat,
        dir_data_lat = dir_data_lat,
        dir_tag_lat = dir_tag_lat,
        l3_map_bits=args.l2_map_bits,
        l3_list_capacity=args.l2_list_capacity,
        l3_num_maptable_set=args.l2_num_maptable_set,
        l3_data_array_segment_size_in_byte=args.l2_data_segment_size,
        l3_tagptr_size_in_bit=0, #depends on number of l3 tags
        l3_data_array_regions=args.l2_data_regions,
        record_line_level_entropy=args.record_line_level_entropy,
        xor_folding_scheme=args.xor_folding_scheme,
        xor_policy=args.xor_policy,
        l3_transitions_per_cycle=args.l2_transitions_per_cycle,
    )

elif args.protocol == 'msi_nine_noxor_bdi_map3':
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MSI_THREE_LEVEL_NINE_XOR_MAP,
        kvm_required=False,
    )

    from gem5.components.cachehierarchies.ruby.msi_three_level_cache_hierarchy_nine_noxor_map import (
        MSIThreeLevelNineNoXORMAPCacheHierarchy,
    )
    if args.cachecfg == "skylake":
        assert False
        l3size_in_kb = 1408
        l3_sector_number = 64*l3size_in_kb
        l3_sector_number = int(math.floor(l3_sector_number / args.l2factor_bdi))
        if l3size_in_kb == 1408 and args.l2factor_bdi == 1.5:
            l3_sector_number = 59392
        elif l3size_in_kb == 1408 and args.l2factor_bdi == 3:
            l3_sector_number = 30048
        elif l3size_in_kb == 1408 and args.l2factor_bdi == 2.5:
            l3_sector_number = 35840
        elif l3size_in_kb == 1408 and args.l2factor_bdi == 1:
            l3_sector_number = 90112
        else: assert False

        cache_hierarchy = MSIThreeLevelNineNoXORMAPCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=8,
            l1i_size="32kB",
            l1i_assoc=8,

            l2_size="1024kB",
            l2_assoc=16,

            l3_tag_size = f"{l3size_in_kb}kB",
            l3_tag_assoc = 11,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size = f"{l3size_in_kb}kB",
            dir_cache_assoc = 11,
            dir_l3_total_size = f"{2*l3size_in_kb}kB",#in KB,
            num_l3_banks = args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_map_bits=args.l2_map_bits,
            l3_list_capacity=args.l2_list_capacity,
            l3_num_maptable_set=args.l2_num_maptable_set,
            l3_compression="bdi",
            l3_data_array_segment_size_in_byte=args.l2_data_segment_size,
            l3_tagptr_size_in_bit=15 if args.tagptr else 0, #depends on number of l3 tags
            l3_data_array_regions=args.l2_data_regions,
            record_line_level_entropy=args.record_line_level_entropy,
            xor_folding_scheme=args.xor_folding_scheme,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
        )
    elif args.cachecfg == "realistic":
        l3size_in_kb = 1024
        l3_sector_number = 64*l3size_in_kb
        l3_sector_number = int(math.floor(l3_sector_number / args.l2factor_bdi))

        if l3size_in_kb == 1024 and args.l2factor_bdi == 1.5:
            l3_sector_number = 40960
        elif l3size_in_kb == 1024 and args.l2factor_bdi == 1.3:
            l3_sector_number = 49152
        elif l3size_in_kb == 1024 and args.l2factor_bdi == 3:
            l3_sector_number = 20480
        elif l3size_in_kb == 1024 and args.l2factor_bdi == 2.5:
            l3_sector_number = 24576
        elif l3size_in_kb == 1024 and args.l2factor_bdi == 2:
            l3_sector_number = 32768
        else: assert False

        

        cache_hierarchy = MSIThreeLevelNineNoXORMAPCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=4,
            l1i_size="32kB",
            l1i_assoc=4,

            l2_size="256kB",
            l2_assoc=8,

            l3_tag_size = f"{l3size_in_kb}kB",
            l3_tag_assoc = 16,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size = f"{l3size_in_kb}kB",
            dir_cache_assoc = 16,
            dir_l3_total_size = f"{2*l3size_in_kb}kB",#in KB,
            num_l3_banks = args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_map_bits=args.l2_map_bits,
            l3_list_capacity=args.l2_list_capacity,
            l3_num_maptable_set=args.l2_num_maptable_set,
            l3_compression="bdi",
            l3_data_array_segment_size_in_byte=args.l2_data_segment_size,
            l3_tagptr_size_in_bit=14 if args.tagptr else 0, #depends on number of l3 tags
            l3_data_array_regions=args.l2_data_regions,
            record_line_level_entropy=args.record_line_level_entropy,
            xor_folding_scheme=args.xor_folding_scheme,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
        )
    elif args.cachecfg == "size512kB" or args.cachecfg == "size2048kB":
        if args.cachecfg == "size512kB":
            l3size_in_kb = int(1024/2)
            l3_sector_number = 64*l3size_in_kb
            l3_sector_number = int(math.floor(l3_sector_number / args.l2factor_bdi))

            if l3size_in_kb == int(1024/2) and args.l2factor_bdi == 1.5:
                l3_sector_number = int(40960/2)
            elif l3size_in_kb == int(1024/2) and args.l2factor_bdi == 1.3:
                l3_sector_number = int(49152/2)
            elif l3size_in_kb == int(1024/2) and args.l2factor_bdi == 3:
                l3_sector_number = int(20480/2)
            elif l3size_in_kb == int(1024/2) and args.l2factor_bdi == 2.5:
                l3_sector_number = int(24576/2)
            elif l3size_in_kb == int(1024/2) and args.l2factor_bdi == 2:
                l3_sector_number = int(32768/2)
            else: assert False
        elif args.cachecfg == "size2048kB":
            l3size_in_kb = int(1024*2)
            l3_sector_number = 64*l3size_in_kb
            l3_sector_number = int(math.floor(l3_sector_number / args.l2factor_bdi))

            if l3size_in_kb == int(1024*2) and args.l2factor_bdi == 1.5:
                l3_sector_number = int(40960*2)
            elif l3size_in_kb == int(1024*2) and args.l2factor_bdi == 1.3:
                l3_sector_number = int(49152*2)
            elif l3size_in_kb == int(1024*2) and args.l2factor_bdi == 3:
                l3_sector_number = int(20480*2)
            elif l3size_in_kb == int(1024*2) and args.l2factor_bdi == 2.5:
                l3_sector_number = int(24576*2)
            elif l3size_in_kb == int(1024*2) and args.l2factor_bdi == 2:
                l3_sector_number = int(32768*2)
            else: assert False
        else: assert False

        cache_hierarchy = MSIThreeLevelNineNoXORMAPCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=4,
            l1i_size="32kB",
            l1i_assoc=4,

            l2_size="256kB",
            l2_assoc=8,

            l3_tag_size = f"{l3size_in_kb}kB",
            l3_tag_assoc = 16,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size = f"{l3size_in_kb}kB",
            dir_cache_assoc = 16,
            dir_l3_total_size = f"{2*l3size_in_kb}kB",#in KB,
            num_l3_banks = args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_map_bits=args.l2_map_bits,
            l3_list_capacity=args.l2_list_capacity,
            l3_num_maptable_set=args.l2_num_maptable_set,
            l3_compression="bdi",
            l3_data_array_segment_size_in_byte=args.l2_data_segment_size,
            l3_tagptr_size_in_bit=14 if args.tagptr else 0, #depends on number of l3 tags
            l3_data_array_regions=args.l2_data_regions,
            record_line_level_entropy=args.record_line_level_entropy,
            xor_folding_scheme=args.xor_folding_scheme,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
        )
    
    else: assert False
elif args.protocol == 'msi_nine_noxor_bpc_map3':
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MSI_THREE_LEVEL_NINE_XOR_MAP,
        kvm_required=False,
    )

    from gem5.components.cachehierarchies.ruby.msi_three_level_cache_hierarchy_nine_noxor_map import (
        MSIThreeLevelNineNoXORMAPCacheHierarchy,
    )
    if args.cachecfg == "skylake":
        assert False
        l3size_in_kb = 1408
        l3_sector_number = 64*l3size_in_kb
        l3_sector_number = int(math.floor(l3_sector_number / args.l2factor_bdi))
        if l3size_in_kb == 1408 and args.l2factor_bdi == 1.5:
            l3_sector_number = 59392
        elif l3size_in_kb == 1408 and args.l2factor_bdi == 3:
            l3_sector_number = 30048
        elif l3size_in_kb == 1408 and args.l2factor_bdi == 2.5:
            l3_sector_number = 35840
        elif l3size_in_kb == 1408 and args.l2factor_bdi == 1:
            l3_sector_number = 90112
        else: assert False

        cache_hierarchy = MSIThreeLevelNineNoXORMAPCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=8,
            l1i_size="32kB",
            l1i_assoc=8,

            l2_size="1024kB",
            l2_assoc=16,

            l3_tag_size = f"{l3size_in_kb}kB",
            l3_tag_assoc = 11,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size = f"{l3size_in_kb}kB",
            dir_cache_assoc = 11,
            dir_l3_total_size = f"{2*l3size_in_kb}kB",#in KB,
            num_l3_banks = args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_map_bits=args.l2_map_bits,
            l3_list_capacity=args.l2_list_capacity,
            l3_num_maptable_set=args.l2_num_maptable_set,
            l3_compression="bitplane",
            l3_data_array_segment_size_in_byte=args.l2_data_segment_size,
            l3_tagptr_size_in_bit=15 if args.tagptr else 0, #depends on number of l3 tags
            l3_data_array_regions=args.l2_data_regions,
            record_line_level_entropy=args.record_line_level_entropy,
            xor_folding_scheme=args.xor_folding_scheme,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
        )
    elif args.cachecfg == "realistic":
        l3size_in_kb = 1024
        l3_sector_number = 64*l3size_in_kb
        l3_sector_number = int(math.floor(l3_sector_number / args.l2factor_bdi))

        if l3size_in_kb == 1024 and args.l2factor_bdi == 1.5:
            l3_sector_number = 40960
        elif l3size_in_kb == 1024 and args.l2factor_bdi == 1.3:
            l3_sector_number = 49152
        elif l3size_in_kb == 1024 and args.l2factor_bdi == 3:
            l3_sector_number = 20480
        elif l3size_in_kb == 1024 and args.l2factor_bdi == 2.5:
            l3_sector_number = 24576
        elif l3size_in_kb == 1024 and args.l2factor_bdi == 2:
            l3_sector_number = 32768
        else: assert False

        

        cache_hierarchy = MSIThreeLevelNineNoXORMAPCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=4,
            l1i_size="32kB",
            l1i_assoc=4,

            l2_size="256kB",
            l2_assoc=8,

            l3_tag_size = f"{l3size_in_kb}kB",
            l3_tag_assoc = 16,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size = f"{l3size_in_kb}kB",
            dir_cache_assoc = 16,
            dir_l3_total_size = f"{2*l3size_in_kb}kB",#in KB,
            num_l3_banks = args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_map_bits=args.l2_map_bits,
            l3_list_capacity=args.l2_list_capacity,
            l3_num_maptable_set=args.l2_num_maptable_set,
            l3_compression="bitplane",
            l3_data_array_segment_size_in_byte=args.l2_data_segment_size,
            l3_tagptr_size_in_bit=14 if args.tagptr else 0, #depends on number of l3 tags
            l3_data_array_regions=args.l2_data_regions,
            record_line_level_entropy=args.record_line_level_entropy,
            xor_folding_scheme=args.xor_folding_scheme,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
        )
    elif args.cachecfg == "size512kB" or args.cachecfg == "size2048kB":
        if args.cachecfg == "size512kB":
            l3size_in_kb = int(1024/2)
            l3_sector_number = 64*l3size_in_kb
            l3_sector_number = int(math.floor(l3_sector_number / args.l2factor_bdi))

            if l3size_in_kb == int(1024/2) and args.l2factor_bdi == 1.5:
                l3_sector_number = int(40960/2)
            elif l3size_in_kb == int(1024/2) and args.l2factor_bdi == 1.3:
                l3_sector_number = int(49152/2)
            elif l3size_in_kb == int(1024/2) and args.l2factor_bdi == 3:
                l3_sector_number = int(20480/2)
            elif l3size_in_kb == int(1024/2) and args.l2factor_bdi == 2.5:
                l3_sector_number = int(24576/2)
            elif l3size_in_kb == int(1024/2) and args.l2factor_bdi == 2:
                l3_sector_number = int(32768/2)
            else: assert False
        elif args.cachecfg == "size2048kB":
            l3size_in_kb = int(1024*2)
            l3_sector_number = 64*l3size_in_kb
            l3_sector_number = int(math.floor(l3_sector_number / args.l2factor_bdi))

            if l3size_in_kb == int(1024*2) and args.l2factor_bdi == 1.5:
                l3_sector_number = int(40960*2)
            elif l3size_in_kb == int(1024*2) and args.l2factor_bdi == 1.3:
                l3_sector_number = int(49152*2)
            elif l3size_in_kb == int(1024*2) and args.l2factor_bdi == 3:
                l3_sector_number = int(20480*2)
            elif l3size_in_kb == int(1024*2) and args.l2factor_bdi == 2.5:
                l3_sector_number = int(24576*2)
            elif l3size_in_kb == int(1024*2) and args.l2factor_bdi == 2:
                l3_sector_number = int(32768*2)
            else: assert False
        else: assert False

        cache_hierarchy = MSIThreeLevelNineNoXORMAPCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=4,
            l1i_size="32kB",
            l1i_assoc=4,

            l2_size="256kB",
            l2_assoc=8,

            l3_tag_size = f"{l3size_in_kb}kB",
            l3_tag_assoc = 16,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size = f"{l3size_in_kb}kB",
            dir_cache_assoc = 16,
            dir_l3_total_size = f"{2*l3size_in_kb}kB",#in KB,
            num_l3_banks = args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_map_bits=args.l2_map_bits,
            l3_list_capacity=args.l2_list_capacity,
            l3_num_maptable_set=args.l2_num_maptable_set,
            l3_compression="bitplane",
            l3_data_array_segment_size_in_byte=args.l2_data_segment_size,
            l3_tagptr_size_in_bit=14 if args.tagptr else 0, #depends on number of l3 tags
            l3_data_array_regions=args.l2_data_regions,
            record_line_level_entropy=args.record_line_level_entropy,
            xor_folding_scheme=args.xor_folding_scheme,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
        )
    
    else: assert False
elif args.protocol == 'msi_nine_noxor_thesaurus_map3':
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MSI_THREE_LEVEL_NINE_XOR_MAP_THESAURUS,
        kvm_required=False,
    )

    from gem5.components.cachehierarchies.ruby.msi_three_level_cache_hierarchy_nine_noxor_map_thesaurus import (
        MSIThreeLevelNineNoXORMAPCacheHierarchy,
    )
    if args.cachecfg == "skylake":
        assert False
        l3size_in_kb = 1408
        l3_sector_number = 64*l3size_in_kb
        l3_sector_number = int(math.floor(l3_sector_number / args.l2factor_bdi))
        if l3size_in_kb == 1408 and args.l2factor_bdi == 1.5:
            l3_sector_number = 59392
        elif l3size_in_kb == 1408 and args.l2factor_bdi == 3:
            l3_sector_number = 30048
        elif l3size_in_kb == 1408 and args.l2factor_bdi == 2.5:
            l3_sector_number = 35840
        else: assert False

        cache_hierarchy = MSIThreeLevelNineNoXORMAPCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=8,
            l1i_size="32kB",
            l1i_assoc=8,

            l2_size="1024kB",
            l2_assoc=16,

            l3_tag_size = f"{l3size_in_kb}kB",
            l3_tag_assoc = 11,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size = f"{l3size_in_kb}kB",
            dir_cache_assoc = 11,
            dir_l3_total_size = f"{2*l3size_in_kb}kB",#in KB,
            num_l3_banks = args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_map_bits=args.l2_map_bits,
            l3_list_capacity=args.l2_list_capacity,
            l3_num_maptable_set=args.l2_num_maptable_set,
            l3_data_array_segment_size_in_byte=args.l2_data_segment_size,
            l3_tagptr_size_in_bit=15 if args.tagptr else 0, #depends on number of l3 tags
            l3_data_array_regions=args.l2_data_regions,
            record_line_level_entropy=args.record_line_level_entropy,
            xor_folding_scheme=args.xor_folding_scheme,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
        )
    elif args.cachecfg == "realistic":
        l3size_in_kb = 1024
        l3_sector_number = 64*l3size_in_kb
        l3_sector_number = int(math.floor(l3_sector_number / args.l2factor_bdi))

        if l3size_in_kb == 1024 and args.l2factor_bdi == 1.5:
            l3_sector_number = 40960
        elif l3size_in_kb == 1024 and args.l2factor_bdi == 3:
            l3_sector_number = 20480
        elif l3size_in_kb == 1024 and args.l2factor_bdi == 2.5:
            l3_sector_number = 24576
        elif l3size_in_kb == 1024 and args.l2factor_bdi == 2:
            l3_sector_number = 32768
        else: assert False

        

        cache_hierarchy = MSIThreeLevelNineNoXORMAPCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=4,
            l1i_size="32kB",
            l1i_assoc=4,

            l2_size="256kB",
            l2_assoc=8,

            l3_tag_size = f"{l3size_in_kb}kB",
            l3_tag_assoc = 16,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size = f"{l3size_in_kb}kB",
            dir_cache_assoc = 16,
            dir_l3_total_size = f"{2*l3size_in_kb}kB",#in KB,
            num_l3_banks = args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_map_bits=args.l2_map_bits,
            l3_list_capacity=args.l2_list_capacity,
            l3_num_maptable_set=args.l2_num_maptable_set,
            l3_data_array_segment_size_in_byte=args.l2_data_segment_size,
            l3_tagptr_size_in_bit=14 if args.tagptr else 0, #depends on number of l3 tags
            l3_data_array_regions=args.l2_data_regions,
            record_line_level_entropy=args.record_line_level_entropy,
            xor_folding_scheme=args.xor_folding_scheme,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
        )
    elif args.cachecfg == "size512kB" or args.cachecfg == "size2048kB":
        if args.cachecfg == "size512kB":
            l3size_in_kb = int(1024/2)
            l3_sector_number = 64*l3size_in_kb
            l3_sector_number = int(math.floor(l3_sector_number / args.l2factor_bdi))

            if l3size_in_kb == int(1024/2) and args.l2factor_bdi == 1.5:
                l3_sector_number = int(40960/2)
            elif l3size_in_kb == int(1024/2) and args.l2factor_bdi == 3:
                l3_sector_number = int(20480/2)
            elif l3size_in_kb == int(1024/2) and args.l2factor_bdi == 2.5:
                l3_sector_number = int(24576/2)
            elif l3size_in_kb == int(1024/2) and args.l2factor_bdi == 2:
                l3_sector_number = int(32768/2)
            else: assert False
        elif args.cachecfg == "size2048kB":
            l3size_in_kb = int(1024*2)
            l3_sector_number = 64*l3size_in_kb
            l3_sector_number = int(math.floor(l3_sector_number / args.l2factor_bdi))

            if l3size_in_kb == int(1024*2) and args.l2factor_bdi == 1.5:
                l3_sector_number = int(40960*2)
            elif l3size_in_kb == int(1024*2) and args.l2factor_bdi == 3:
                l3_sector_number = int(20480*2)
            elif l3size_in_kb == int(1024*2) and args.l2factor_bdi == 2.5:
                l3_sector_number = int(24576*2)
            elif l3size_in_kb == int(1024*2) and args.l2factor_bdi == 2:
                l3_sector_number = int(32768*2)
            else: assert False
        else: assert False

        cache_hierarchy = MSIThreeLevelNineNoXORMAPCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=4,
            l1i_size="32kB",
            l1i_assoc=4,

            l2_size="256kB",
            l2_assoc=8,

            l3_tag_size = f"{l3size_in_kb}kB",
            l3_tag_assoc = 16,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size = f"{l3size_in_kb}kB",
            dir_cache_assoc = 16,
            dir_l3_total_size = f"{2*l3size_in_kb}kB",#in KB,
            num_l3_banks = args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_map_bits=args.l2_map_bits,
            l3_list_capacity=args.l2_list_capacity,
            l3_num_maptable_set=args.l2_num_maptable_set,
            l3_data_array_segment_size_in_byte=args.l2_data_segment_size,
            l3_tagptr_size_in_bit=14 if args.tagptr else 0, #depends on number of l3 tags
            l3_data_array_regions=args.l2_data_regions,
            record_line_level_entropy=args.record_line_level_entropy,
            xor_folding_scheme=args.xor_folding_scheme,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
        )
    else: assert False

elif args.protocol == 'msi_nine_noxor_nobdi_map3':
    requires(
        isa_required=ISA.X86,
        coherence_protocol_required=CoherenceProtocol.MSI_THREE_LEVEL_NINE_XOR_MAP,
        kvm_required=False,
    )

    from gem5.components.cachehierarchies.ruby.msi_three_level_cache_hierarchy_nine_noxor_map import (
        MSIThreeLevelNineNoXORMAPCacheHierarchy,
    )
    if args.cachecfg == "skylake":
        assert False
        l3size_in_kb = 1408
        l3_sector_number = 64*l3size_in_kb

        cache_hierarchy = MSIThreeLevelNineNoXORMAPCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=8,
            l1i_size="32kB",
            l1i_assoc=8,

            l2_size="1024kB",
            l2_assoc=16,

            l3_tag_size = f"{l3size_in_kb}kB",
            l3_tag_assoc = 11,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size = f"{l3size_in_kb}kB",
            dir_cache_assoc = 11,
            dir_l3_total_size = f"{2*l3size_in_kb}kB",#in KB,
            num_l3_banks = args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_map_bits=args.l2_map_bits,
            l3_list_capacity=args.l2_list_capacity,
            l3_num_maptable_set=args.l2_num_maptable_set,
            l3_data_array_segment_size_in_byte=args.l2_data_segment_size,
            l3_tagptr_size_in_bit=0, #depends on number of l3 tags
            l3_data_array_regions=args.l2_data_regions,
            record_line_level_entropy=args.record_line_level_entropy,
            xor_folding_scheme=args.xor_folding_scheme,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
        )
    elif args.cachecfg == "realistic":
        l3size_in_kb = 1024
        l3_sector_number = 64*l3size_in_kb

        cache_hierarchy = MSIThreeLevelNineNoXORMAPCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=4,
            l1i_size="32kB",
            l1i_assoc=4,

            l2_size="256kB",
            l2_assoc=8,

            l3_tag_size = f"{l3size_in_kb}kB",
            l3_tag_assoc = 16,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size = f"{l3size_in_kb}kB",
            dir_cache_assoc = 16,
            dir_l3_total_size = f"{2*l3size_in_kb}kB",#in KB,
            num_l3_banks = args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_map_bits=args.l2_map_bits,
            l3_list_capacity=args.l2_list_capacity,
            l3_num_maptable_set=args.l2_num_maptable_set,
            l3_data_array_segment_size_in_byte=args.l2_data_segment_size,
            l3_tagptr_size_in_bit=0, #depends on number of l3 tags
            l3_data_array_regions=args.l2_data_regions,
            record_line_level_entropy=args.record_line_level_entropy,
            xor_folding_scheme=args.xor_folding_scheme,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
        )
    elif args.cachecfg == "size512kB" or args.cachecfg == "size2048kB":
        if args.cachecfg == "size512kB":
            l3size_in_kb = int(1024/2)
        elif args.cachecfg == "size2048kB":
            l3size_in_kb = int(1024*2)
        else: assert False
        l3_sector_number = 64*l3size_in_kb

        cache_hierarchy = MSIThreeLevelNineNoXORMAPCacheHierarchy(
            l1d_size="32kB",
            l1d_assoc=4,
            l1i_size="32kB",
            l1i_assoc=4,

            l2_size="256kB",
            l2_assoc=8,

            l3_tag_size = f"{l3size_in_kb}kB",
            l3_tag_assoc = 16,
            l3_data_size=f"{l3_sector_number}kB",
            dir_cache_size = f"{l3size_in_kb}kB",
            dir_cache_assoc = 16,
            dir_l3_total_size = f"{2*l3size_in_kb}kB",#in KB,
            num_l3_banks = args.core,
            l3_data_lat = l3_data_lat,
            l3_tag_lat = l3_tag_lat,
            dir_data_lat = dir_data_lat,
            dir_tag_lat = dir_tag_lat,
            l3_map_bits=args.l2_map_bits,
            l3_list_capacity=args.l2_list_capacity,
            l3_num_maptable_set=args.l2_num_maptable_set,
            l3_data_array_segment_size_in_byte=args.l2_data_segment_size,
            l3_tagptr_size_in_bit=0, #depends on number of l3 tags
            l3_data_array_regions=args.l2_data_regions,
            record_line_level_entropy=args.record_line_level_entropy,
            xor_folding_scheme=args.xor_folding_scheme,
            l3_transitions_per_cycle=args.l2_transitions_per_cycle,
        )
    
    else: assert False

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
