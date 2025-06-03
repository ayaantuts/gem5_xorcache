# Zhewen
# reference: configs/example/gem5_library/x86-parsec-benchmarks.py

import argparse
import time
import re,os,sys
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
    "--benchmark",
    type=str,
    required=True,
    help="Input the benchmark program to execute.",
    choices=benchmark_choices,
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

parser.add_argument(
    "--index_bits_shift",
    type=int,
    required=True,
    help="bank bits shift",
    default=0,
)
parser.add_argument('--ooo', action='store_true')
parser.add_argument('--no-ooo', dest='ooo', action='store_false')
parser.set_defaults(ooo=False)

parser.add_argument('--tagptr', action='store_true')
parser.add_argument('--no-tagptr', dest='tagptr', action='store_false')
parser.set_defaults(tagptr=True)

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
    help='xor policy name',
)
parser.add_argument(
    "--core",
    type=int,
    required=False,
    default=1,
    help="core ct",
)
parser.add_argument(
    "--protocol",
    type=str,
    help="which protocol to run",
    choices=[
             "mesi3", "msi_nine_noxor_nobdi_map3", 
             "msi_exc3", "msi_exc_bdi3",
             "msi_nine_xor_bdi_map3",  "msi_nine_xor_thesaurus_map3", 
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
parser.add_argument('--disassemble', action='store_true')
parser.add_argument('--no-disassemble', dest='disassemble', action='store_false')
parser.set_defaults(disassemble=False)

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
    "--set",
    type=str,
    required=False,
    default="ser",
    help="run config. serial or parallel.",
    choices=set_choices,
)
args = parser.parse_args()

if args.disassemble == True:
    ckpt_path = f"{args.ckpt_search_path}/ckpt/m5_fs_perfect_disassemble/{args.set}_core{args.core}/{args.benchmark}/cpt"
else:
    ckpt_path = f"{args.ckpt_search_path}/ckpt/m5_fs_perfect/{args.set}_core{args.core}/{args.benchmark}/cpt"

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
# memory = SimpleMemory(bandwidth="49GB/s", latency="50ns", latency_var="0ns")

# Here we setup the processor. This is a special switchable processor in which
# a starting core type and a switch core type must be specified. Once a
# configuration is instantiated a user may call `processor.switch()` to switch
# from the starting core types to the switch core types. In this simulation
# we start with KVM cores to simulate the OS boot, then switch to the Timing
# cores for the command we wish to run after boot.

if args.ooo == True:
    processor = SimpleProcessor(
        cpu_type=CPUTypes.O3, isa=ISA.X86, num_cores=args.core
    )
else:
    processor = SimpleProcessor(
        cpu_type=CPUTypes.TIMING, isa=ISA.X86, num_cores=args.core
        # cpu_type=CPUTypes.ATOMIC, isa=ISA.X86, num_cores=args.core
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
from gem5.resources.resource import CustomResource

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
    checkpoint=CustomResource(ckpt_path),
    # The x86 linux kernel will be automatically downloaded to the
    # `~/.cache/gem5` directory if not already present.
    # SPEC CPU2017 benchamarks were tested with kernel version 4.19.83
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

# We start the simulation

exit_event = m5.simulate()

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
if args.ooo == True:
    if args.core == 1:
        roi_insts += float(
            gem5stats.to_json()["system"]["processor"][f"cores"]["core"]["numInsts"]["value"])
    else:
        for i in range(args.core):
            roi_insts += float(
                gem5stats.to_json()["system"]["processor"][f"cores{i}"]["core"]["numInsts"]["value"])
else:
    if args.core == 1:
        roi_insts += float(
            gem5stats.to_json()["system"]["processor"][f"cores"]["core"][
                "exec_context.thread_0"
            ]["numInsts"]["value"])
    else:
        for i in range(args.core):
            roi_insts += float(
                gem5stats.to_json()["system"]["processor"][f"cores{i}"]["core"][
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
