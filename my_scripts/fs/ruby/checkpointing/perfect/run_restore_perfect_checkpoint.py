import sys
import argparse, subprocess, os, re
from loguru import logger

# Following are the list of benchmark programs for perfec.

benchmark_choices = [
    "2d_convolution",
    "dwt53",
    "histogram_equalization",
    "change-detection",
    "debayer",
    "lucas-kanade",
]

# Following are the input size.

size_choices = [ ]

parser = argparse.ArgumentParser(description="config.")
parser.add_argument(
    "--image_path_override",
    type=str,
    required=False,
    help="disk image loc override",
)
parser.add_argument(
    "--flags",
    type=str,
    required=False,
    help="flag",
    nargs='+',
)
parser.add_argument(
    "--begin",
    type=int,
    required=False,
    help="begin tick",
)
parser.add_argument(
    "--end",
    type=int,
    required=False,
    help="end tick",
)
parser.add_argument(
    "--fast",
    type=bool,
    required=False,
    default=False,
    help="use fast instead of opt",
)
parser.add_argument(
    "--home",
    type=bool,
    required=False,
    default=False,
    help="run with home machine",
)
parser.add_argument(
    "--benchmark",
    type=str,
    required=True,
    help="Input the benchmark program to execute.",
    choices=benchmark_choices,
)
parser.add_argument(
    "--index_bits_shift",
    type=int,
    required=True,
    help="bank bits shift",
    default=0,
)
parser.add_argument(
    "--use_anonymous_latency",
    type=bool,
    required=False,
    default=False,
    help="assign cache latency regardless of size",
)
# parser.add_argument(
#     "--size",
#     type=str,
#     required=True,
#     help="Simulation size the benchmark program.",
#     choices=size_choices,
# )
parser.add_argument(
    "--set",
    type=str,
    required=False,
    default="ser",
    help="run config",
    choices=["ser", "omp"],
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
    "--xor_folding_scheme",
    type=int,
    required=False,
    help="xor folding scheme. 0 for regular; 1 for abi; 2 for lsh;",
    default=0,
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
    default=1,
    help="core ct",
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

parser.add_argument('--record_line_level_entropy', action='store_true')
parser.add_argument('--no-record_line_level_entropy', dest='record_line_level_entropy', action='store_false')
parser.set_defaults(record_line_level_entropy=False)


parser.add_argument('--ooo', action='store_true')
parser.add_argument('--no-ooo', dest='ooo', action='store_false')
parser.set_defaults(ooo=False)
parser.add_argument(
    "--l2factor",
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
    "--suite_name",
    type=str,
    help="suite name used as result dir",
    default="perfect",
    required=False,
)

parser.add_argument(
    "--hook",
    type=bool,
    required=False,
    default=True,
    help="by default, we use hook to annotate ROI",
)
args = parser.parse_args()

assert args.hook


debug_flag = ""
if args.flags:
    debug_flag = "--debug-flags="
    debug_flag += ",".join(args.flags)

debug_interval = ""
if args.begin and args.end:
    interval = (args.begin, args.end)
    debug_interval = f'--debug-start={interval[0]} --debug-end={interval[1]}'

if args.protocol == "baseline":
    design = "test"
elif args.protocol == "noisy":
    design = "MyMESI2"
    design_out = "MyMESI2_Noisy"
elif args.protocol == "decoupled":
    design = "MyMESI2_Decoupled"
    design_out = design
elif args.protocol == "compress":
    design = "MyMESI2_Compress"
    design_out = design
elif args.protocol == "dedup":
    design = "MyMESI2_Dedup"
    design_out = design
elif args.protocol == "bdixor":
    design = "MyMESI2_BDI_XOR"
    design_out = design
elif args.protocol == "xor":
    design = "MyMESI2_BDI_XOR"
    design_out = "MyMESI2_XOR"
elif args.protocol == "msi":
    design = "MyMSI"
    design_out = "MyMSI"
elif args.protocol == "msi_nine":
    design = "MyMSI_NINE"
    design_out = "MyMSI_NINE"
elif args.protocol == "msi_nine_xor":
    design = "MyMSI_NINE_XOR"
    design_out = "MyMSI_NINE_XOR"
elif args.protocol == "msi_nine_noxor":
    design = "MyMSI_NINE_XOR"
    design_out = "MyMSI_NINE_NOXOR"
elif args.protocol == "msi_nine_xor_bdi_map":
    design = "MyMSI_NINE_XOR_MAP"
    design_out = "MyMSI_NINE_XOR_BDI_MAP"
elif args.protocol == "msi_nine_xor_nobdi_map":
    design = "MyMSI_NINE_XOR_MAP"
    design_out = "MyMSI_NINE_XOR_NOBDI_MAP"
elif args.protocol == "msi_nine_noxor_bdi_map":
    design = "MyMSI_NINE_XOR_MAP"
    design_out = "MyMSI_NINE_NOXOR_BDI_MAP"
elif args.protocol == "msi_nine_noxor_nobdi_map":
    design = "MyMSI_NINE_XOR_MAP"
    design_out = "MyMSI_NINE_NOXOR_NOBDI_MAP"
elif args.protocol == "msi_exc_nobdi":
    design = "MyMSI_EXC"
    design_out = "MyMSI_EXC_NOBDI"
elif args.protocol == "msi_exc_bdi":
    design = "MyMSI_EXC"
    design_out = "MyMSI_EXC_BDI"
elif re.search("xor_(\d)(\d)(\d)",args.protocol): 
    design = "MyMESI2_BDI_XOR"
    design_out = "MyMESI2_XOR"

    parameters = re.search("xor_(\d)(\d)(\d)",args.protocol)
    p_dpe = bool(int(parameters.group(1)))
    p_sis = bool(int(parameters.group(2)))
    p_xpi = int(parameters.group(3))

    design_out += "_wProac" if p_dpe else "_woProac"
    design_out += "_set" if p_sis else "_bank"
    if p_xpi == 1: design_out += "_greedy_ran"
    elif p_xpi == 2: design_out += "_nongreedy_ran"
    elif p_xpi == 3: design_out += "_greedy_mru"
    elif p_xpi == 4: design_out += "_nongreedy_mru"
    else: assert False

testname= f"fs_ruby_{args.suite_name}_from_checkpoint"
py_config_file_name = "perfect-hook-restore-checkpoint.py"

if args.use_anonymous_latency:
    folder_name = "anonymous_latency"
else: folder_name = ""

if args.ooo == True:
    if folder_name == "": folder_name = "ooo"
    else: folder_name += "_ooo"

if args.fast == True:
    if folder_name == "": folder_name = "fast"
    else: folder_name += "_fast"
else: 
    if folder_name == "": folder_name = "opt"
    else: folder_name += "_opt"


if args.protocol == "msi_nine_xor_bdi_map" or args.protocol == "msi_nine_noxor_bdi_map" or \
    args.protocol == "msi_nine_xor_nobdi_map" or args.protocol == "msi_exc_bdi":
    ratio = args.l2factor
    ratio_str = f"_ratio{ratio}"
else:
    ratio_str = ""

if args.protocol == "msi_nine_noxor_bdi_map" or args.protocol == "msi_nine_xor_bdi_map" or args.protocol == "msi_exc_bdi":
    region = args.l2_data_regions
    region_str = f"_{region}region"
    seg = args.l2_data_segment_size
    seg_str = f"_{seg}Bseg"
else:
    region_str = ""
    seg_str = ""

transition_mapbit_str = f"_{args.l2_transitions_per_cycle}t_{args.l2_map_bits}mapb_{args.l2_num_maptable_set}x{args.l2_list_capacity}_{args.xor_policy}"

if args.xor_folding_scheme == 0:
    transition_mapbit_str += "_bytelabel"
elif args.xor_folding_scheme == 1:
    transition_mapbit_str += "_sparsebytelabel"
elif args.xor_folding_scheme == 2:
    transition_mapbit_str += "_hycomp"
else: assert False

if args.protocol == "msi_nine_xor_bdi_map" and args.index_bits_shift != 0:
    transition_mapbit_str += f"_idxshift{args.index_bits_shift}"

path = f"m5out/m5out_{testname}/{folder_name}/{design_out}_{args.l2size}{ratio_str}{seg_str}{region_str}{transition_mapbit_str}/c{args.core}/{args.benchmark}"



isExist = os.path.exists(path)
if not isExist:
   os.makedirs(path)

if args.fast == True:
    gem5_binary = f"build/X86_{design}/gem5.fast"
else:
    gem5_binary = f"build/X86_{design}/gem5.opt"

if not os.path.isfile(gem5_binary): 
    logger.error(f"gem5 binary file ({gem5_binary}) not exist!")
    exit(1)


cmd_list = [f"nohup time {gem5_binary} -d {path} " + \
    f"{debug_flag} {debug_interval} configs/my_configs/fs/ruby/perfect/checkpointing/{py_config_file_name}"
        ]

cmd_list[0] += f" --protocol {args.protocol} --ckpt_protocol {args.ckpt_protocol} --ckpt_search_path {args.ckpt_search_path}"
cmd_list[0] += f" --set {args.set}"
if args.core: cmd_list[0] += f" --core {args.core}"

cmd_list[0] += f" --benchmark {args.benchmark} --partition 1"
cmd_list[0] += f" --l2size {args.l2size}"
cmd_list[0] += f" --l2_transitions_per_cycle {args.l2_transitions_per_cycle}"
cmd_list[0] += f" --xor_policy {args.xor_policy}"
cmd_list[0] += f" --l2_map_bits {args.l2_map_bits}"
cmd_list[0] += f" --l2_num_maptable_set {args.l2_num_maptable_set}"
cmd_list[0] += f" --l2_list_capacity {args.l2_list_capacity}"

if args.protocol == "msi_nine_xor_bdi_map":
    cmd_list[0] += f" --l2factor_xor_bdi {args.l2factor}"
    cmd_list[0] += f" --l2_data_segment_size {args.l2_data_segment_size}"
    cmd_list[0] += f" --l2_data_regions {args.l2_data_regions}"
elif args.protocol == "msi_nine_noxor_bdi_map":
    cmd_list[0] += f" --l2factor_bdi {args.l2factor}"
    cmd_list[0] += f" --l2_data_segment_size {args.l2_data_segment_size}"
    cmd_list[0] += f" --l2_data_regions {args.l2_data_regions}"
elif args.protocol == "msi_nine_xor_nobdi_map":
    cmd_list[0] += f" --l2factor_xor {args.l2factor}"
    cmd_list[0] += f" --l2_data_segment_size 64"
elif args.protocol == "msi_nine_noxor_nobdi_map":
    cmd_list[0] += f" --l2_data_segment_size 64"
elif args.protocol == "msi_exc_nobdi":
    cmd_list[0] += f" --l2_data_segment_size 64"
    cmd_list[0] += f" --l2_data_regions 1"
elif args.protocol == "msi_exc_bdi":
    cmd_list[0] += f" --l2factor_bdi {args.l2factor}"
    cmd_list[0] += f" --l2_data_segment_size {args.l2_data_segment_size}"
    cmd_list[0] += f" --l2_data_regions {args.l2_data_regions}"

if args.protocol == "msi_nine_xor_bdi_map":
    cmd_list[0] += f" --index_bits_shift {args.index_bits_shift}"
else:
    cmd_list[0] += f" --index_bits_shift 0"

if args.use_anonymous_latency:
    cmd_list[0] += f" --anonymous_latency 1"
if args.ooo == True:
    cmd_list[0] += f" --ooo"

if args.record_line_level_entropy == True:
    cmd_list[0] += f" --record_line_level_entropy"
if args.xor_folding_scheme:
    cmd_list[0] += f" --xor_folding_scheme {args.xor_folding_scheme}"


# expand ~ dir
if args.image_path_override:
    if not os.path.exists(f"{args.image_path_override}/perfect"):
        logger.error(f"not found {args.image_path_override}/perfect")
        exit(1)
    cmd_list[0] += f" --image {args.image_path_override}/perfect"
else:
    home_dir = os.path.expanduser("~")
    if not os.path.exists(f"{home_dir}/Dropbox/data/perfect-image/perfect"):
        logger.error(f"not found {home_dir}/Dropbox/data/perfect-image/perfect")
        exit(1)
    cmd_list[0] += f" --image {home_dir}/Dropbox/data/perfect-image/perfect"

if not args.flags:
    p = subprocess.Popen(cmd_list, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(f'Launched:  ')
    print(f'{p.args}')
    out,err = p.communicate()
    out = out.decode('utf-8')
    err = err.decode('utf-8')
    if err: 
        logger.error(err)
        ferr = open(f"{path}/err.txt","w")
        ferr.write(err)
        ferr.write(f'{p.args}')
        ferr.close()


    fout = open(f"{path}/out.txt","w")
    fout.write(out)
else:
    # nonblocking
    logger.warning(f"nonblocking since {args.flags} enabled")
    with open(f"{path}/err.txt","w") as err, open(f"{path}/out.txt","w") as out:
        p = subprocess.Popen(cmd_list, shell=True, stdout=out, stderr=err)
        print(f'Launched:  ')
        print(f'{p.args}')
