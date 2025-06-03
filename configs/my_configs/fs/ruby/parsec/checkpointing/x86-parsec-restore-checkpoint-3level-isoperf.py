# Reference: configs/example/gem5_library/checkpoints/riscv-hello-restore-checkpoint.py
# this should run on condor; KVM fastforwarding has been skipped.
import argparse
import time
import re
import os
import json
import math

import m5
from m5.objects import Root

from gem5.utils.requires import requires
from gem5.components.boards.x86_board import X86Board
from gem5.components.memory import DualChannelDDR4_2400
from gem5.components.processors.cpu_types import CPUTypes
from gem5.isas import ISA
from gem5.coherence_protocol import CoherenceProtocol
from gem5.resources.resource import Resource
from gem5.components.processors.simple_processor import SimpleProcessor

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
    help="xor folding scheme. 0 for regular; 1 for abi; 2 for lsh; 3 for bmap_fold",
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
    "--index_bits_shift",
    type=int,
    required=True,
    help="bank bits shift",
    default=0,
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
    default=2,
    help="core ct",
)
parser.add_argument(
    "--protocol",
    type=str,
    help="which protocol to run",
    choices=["mesi3", "msi_nine_noxor_nobdi_map3", 
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
    "--path",
    type=str,
    required=False,
    help="path to the local x86-parsec disk image",
)

parser.add_argument(
    "--size",
    type=str,
    required=True,
    help="Simulation size the benchmark program.",
    choices=size_choices,
)
parser.add_argument(
    "--warmup_instr_step",
    type=int,
    required=False,
    default=100,
    help="warmp instruction step",
)
parser.add_argument(
    "--llc_lat",
    type=int,
    required=False,
    default=40,
    help='llc latency',
)
args = parser.parse_args()
ckpt_path = f"{args.ckpt_search_path}/ckpt/fs_ruby_parsec/{args.ckpt_protocol}_c{args.core}_{args.size}/{args.benchmark}/cpt"
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

# We use a simple processor.
if args.ooo == True:
    processor = SimpleProcessor(
        cpu_type=CPUTypes.O3, isa=ISA.X86, num_cores=args.core
    )
else:
    processor = SimpleProcessor(
        cpu_type=CPUTypes.TIMING, isa=ISA.X86, num_cores=args.core
    )


# Here we setup the board. The X86Board allows for Full-System X86 simulations

board = X86Board(
    clk_freq="3GHz",
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy,
)

# Here we set the checkpoint resource. 
# This checkpoint was taken from running this gem5 configuration script,
# my_scripts/fs/ruby/checkpointing/make_parsec_checkpoint.py
# from gem5.resources.resource import CustomDiskImageResource
from gem5.resources.resource import CustomResource
if args.path:
    from gem5.resources.resource import CustomDiskImageResource
    board.set_kernel_disk_workload(
        # the workload should be the same as the save-checkpoint script
        checkpoint=CustomResource(ckpt_path),
        kernel=CustomResource("x86-linux-kernel-4.19.83"),
        disk_image=CustomDiskImageResource(
            f"{args.path}/x86-parsec", disk_root_partition="1"
        ),
    )
else:
    board.set_kernel_disk_workload(
        checkpoint=CustomResource(ckpt_path),
        kernel=Resource("x86-linux-kernel-4.19.83"),
        disk_image=Resource("x86-parsec"),
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
if args.warmup_instr_step != 0:
    phase_ct = 0
    while True:
        for i in range(args.core):
            processor.get_cores()[i].core.scheduleInstStop(0, args.warmup_instr_step, "m5_workbegin instruction encountered")
        num_workbegin_seen = 0
        print(f"[I] starting warmup phase #{phase_ct} (quantum {args.warmup_instr_step} insts)")
        while True:
            exit_event = m5.simulate()
            if exit_event.getCause() == "m5_workbegin instruction encountered":
                num_workbegin_seen += 1
                if num_workbegin_seen == args.core:
                    print(f"    Finished warmup phase #{phase_ct}")
                    break
            else:
                print("Unexpected termination of simulation while warmup was being executed!")
                print(
                    "Exiting @ tick {} because {}. {} workbegins seen.".format(
                        m5.curTick(), exit_event.getCause(), num_workbegin_seen
                    )
                )
                exit(-1)
        # read stats to see utilization numTagInUse_max

        gem5stats = get_simstat(root)

        max_arr = []
        for i in range(args.core):
            max = float(
                    json.loads(gem5stats.dumps())["system"]["cache_hierarchy"]["ruby_system"][f"l2_controllers{i}"]["L2cache"]
                        ["numTagInUse_max"]["value"]
                )
            max_arr.append(max)
        util = [max_ / numTag_tot * 100 for max_ in max_arr]
        overall_util = sum(max_arr) / (numTag_tot * args.core) * 100
        # if all(num > 90 for num in util): 
        if overall_util > 50: 
            print(f"[I] Warmup done! l2cache Utilization: {util}, overall: {overall_util}")
            break
        else: 
            print(f"    l2cache Utilization: {util}, overall: {overall_util}")
        phase_ct += 1

    start_tick = m5.curTick()

    with open(m5.options.outdir+f"/warmup{phase_ct}_{m5.curTick()}_done.json", 'w+') as f:
        gem5stats.dump(fp=f, indent=6)

    print(f"[I] Resetting stats and starting detailed simulation phase at tick {start_tick}!")
    m5.stats.reset()

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
for i in range(args.core):
    if args.core == 1:
        roi_insts += float(
            json.loads(gem5stats.dumps())["system"]["processor"][f"cores"]["core"]
                ["exec_context.thread_0"]["numInsts"]["value"]
        )
    else:
        roi_insts += float(
            json.loads(gem5stats.dumps())["system"]["processor"][f"cores{i}"]["core"]
                ["exec_context.thread_0"]["numInsts"]["value"]
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
