# this script uses x86_dump binary to dump cache content and address periodically

# compile:
#scons build/X86_MyMESI2/gem5.opt --default=X86 PROTOCOL=MESI_Two_Level_my SLICC_HTML=True -j24
#scons build/X86_test/gem5.opt -j24 --default=x86

import sys
import argparse, subprocess, os, re
from loguru import logger
parser = argparse.ArgumentParser(description="config.")

# parser.add_argument(
#     "--image",
#     type=str,
#     required=False,
#     help="disk image",
#     default="/home/zhewen/repo/gem5-resources/src/spec-2017-flexible/disk-image/spec-2017-flexible/spec-2017-flexible-image/spec-2017-flexible",
# )
parser.add_argument(
    "--image_path_override",
    type=str,
    required=False,
    help="disk image loc override",
)

parser.add_argument(
    "--detailed_inst",
    type=int,
    required=False,
    help="Number of cycles to perform detailed simulation.",
    # default=5000,
    # default=100000000,#0.1B
    # default=500000000,#0.5B
    default=10,
    # default=1000000000,#1B
    # default=30000000000,#30B
)
parser.add_argument(
    "--fully_util",
    type=int,
    required=True,
    help="duplicate processes to fully utilize all cores",
    default=0,
)

parser.add_argument(
    "--index_bits_shift",
    type=int,
    required=True,
    help="bank bits shift",
    default=0,
)
parser.add_argument(
    "--seed",
    type=int,
    required=False,
    default=100,
    help="random seed for random number generator",
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
    help="set when running on home computer, mnt dir",
)
parser.add_argument(
    "--run",
    type=int,
    required=False,
    help="index of this run",
)
parser.add_argument(
    "--size",
    type=str,
    required=False,
    help="benchmark size",
    default="ref",
)
parser.add_argument(
    "--anonymous_latency",
    type=bool,
    required=False,
    default=False,
    help="assign l2 latency regardless of size",
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
    choices=["32kB", "64kB", "128kB","256kB","512kB", "1024kB", "1408kB", "2048kB"],
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
             "mesi2_inc_nobdi", "mesi2_inc_bdi",
             "msi_nine_noxor_nobdi_map3", "msi_nine_xor_bdi_map3", "msi_nine_noxor_bdi_map3", "msi_nine_xor_nobdi_map3",
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
parser.add_argument(
    "--use_anonymous_latency",
    type=bool,
    required=False,
    default=False,
    help="assign cache latency regardless of size",
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
args = parser.parse_args()


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

elif args.protocol == "msi_nine_xor_bdi_map3":
    design = "MyMSI_THREELEVEL_NINE_XOR_MAP"
    design_out = "MyMSI_NINE_XOR_BDI_MAP3"
elif args.protocol == "msi_nine_xor_nobdi_map3":
    design = "MyMSI_THREELEVEL_NINE_XOR_MAP"
    design_out = "MyMSI_NINE_XOR_NOBDI_MAP3"
elif args.protocol == "msi_nine_noxor_bdi_map3":
    design = "MyMSI_THREELEVEL_NINE_XOR_MAP"
    design_out = "MyMSI_NINE_NOXOR_BDI_MAP3"
elif args.protocol == "msi_nine_noxor_nobdi_map3":
    design = "MyMSI_THREELEVEL_NINE_XOR_MAP"
    design_out = "MyMSI_NINE_NOXOR_NOBDI_MAP3"

elif args.protocol == "msi_exc_nobdi":
    design = "MyMSI_EXC"
    design_out = "MyMSI_EXC_NOBDI"
elif args.protocol == "msi_exc_bdi":
    design = "MyMSI_EXC"
    design_out = "MyMSI_EXC_BDI"

elif args.protocol == "mesi2_inc_nobdi":
    design = "MyMESI2_INC_INTRACOMP"
    design_out = "MyMESI2_INC_NOBDI"
elif args.protocol == "mesi2_inc_bdi":
    design = "MyMESI2_INC_INTRACOMP"
    design_out = "MyMESI2_INC_BDI"

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

testname= "fs_spec2017_from_checkpoint"
py_config_file_name = "spec2017-restore-checkpoint.py"

if args.use_anonymous_latency:
    folder_name = "anonymous_latency"
else: folder_name = ""

# if args.ooo == True:
#     if folder_name == "": folder_name = "ooo"
#     else: folder_name += "_ooo"

if args.fast == True:
    if folder_name == "": folder_name = "fast"
    else: folder_name += "_fast"
else: 
    if folder_name == "": folder_name = "opt"
    else: folder_name += "_opt"


if args.protocol == "msi_nine_xor_bdi_map" or args.protocol == "msi_nine_noxor_bdi_map" or \
    args.protocol == "msi_nine_xor_nobdi_map" or \
    args.protocol == "msi_nine_xor_bdi_map3" or args.protocol == "msi_nine_noxor_bdi_map3" or \
    args.protocol == "msi_nine_xor_nobdi_map3" or \
    args.protocol == "msi_exc_bdi":
    ratio = args.l2factor
    ratio_str = f"_ratio{ratio}"
else:
    ratio_str = ""

if args.protocol == "msi_nine_noxor_bdi_map" or args.protocol == "msi_nine_xor_bdi_map" or \
    args.protocol == "msi_nine_noxor_bdi_map3" or args.protocol == "msi_nine_xor_bdi_map3" or \
    args.protocol == "msi_exc_bdi":
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

if (args.protocol == "msi_nine_xor_bdi_map" or args.protocol == "msi_nine_xor_bdi_map3") and args.index_bits_shift != 0:
    transition_mapbit_str += f"_idxshift{args.index_bits_shift}"

path = f"m5out/m5out_{testname}/{folder_name}/{design_out}_{args.l2size}{ratio_str}{seg_str}{region_str}{transition_mapbit_str}_ff{args.ckpt_fastforward_insts}_d{args.detailed_inst}/c{args.core}_proc{args.numProcesses}_run{args.run}_seed{args.seed}"



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
f"{debug_flag} {debug_interval} configs/my_configs/fs/ruby/spec2017/checkpointing/{py_config_file_name}"
    ]

cmd_list[0] += f" --protocol {args.protocol} --ckpt_protocol {args.ckpt_protocol} --ckpt_search_path {args.ckpt_search_path}"
cmd_list[0] += f" --ckpt_fastforward_insts {args.ckpt_fastforward_insts}"
cmd_list[0] += f" --l2size {args.l2size} --detailed_inst {args.detailed_inst}"

cmd_list[0] += f" --l2size {args.l2size}"
cmd_list[0] += f" --l2_transitions_per_cycle {args.l2_transitions_per_cycle}"
cmd_list[0] += f" --xor_policy {args.xor_policy}"
cmd_list[0] += f" --l2_map_bits {args.l2_map_bits}"
cmd_list[0] += f" --l2_num_maptable_set {args.l2_num_maptable_set}"
cmd_list[0] += f" --l2_list_capacity {args.l2_list_capacity}"

if args.protocol == "msi_nine_xor_bdi_map" or args.protocol == "msi_nine_xor_bdi_map3":
    cmd_list[0] += f" --l2factor_xor_bdi {args.l2factor}"
    cmd_list[0] += f" --l2_data_segment_size {args.l2_data_segment_size}"
    cmd_list[0] += f" --l2_data_regions {args.l2_data_regions}"
elif args.protocol == "msi_nine_noxor_bdi_map" or args.protocol == "msi_nine_noxor_bdi_map3":
    cmd_list[0] += f" --l2factor_bdi {args.l2factor}"
    cmd_list[0] += f" --l2_data_segment_size {args.l2_data_segment_size}"
    cmd_list[0] += f" --l2_data_regions {args.l2_data_regions}"
elif args.protocol == "msi_nine_xor_nobdi_map" or args.protocol == "msi_nine_xor_nobdi_map3":
    cmd_list[0] += f" --l2factor_xor {args.l2factor}"
    cmd_list[0] += f" --l2_data_segment_size 64"
elif args.protocol == "msi_nine_noxor_nobdi_map" or args.protocol == "msi_nine_noxor_nobdi_map3":
    cmd_list[0] += f" --l2_data_segment_size 64"

elif args.protocol == "msi_exc_nobdi":
    cmd_list[0] += f" --l2_data_segment_size 64"
    cmd_list[0] += f" --l2_data_regions 1"
elif args.protocol == "msi_exc_bdi":
    cmd_list[0] += f" --l2factor_bdi {args.l2factor}"
    cmd_list[0] += f" --l2_data_segment_size {args.l2_data_segment_size}"
    cmd_list[0] += f" --l2_data_regions {args.l2_data_regions}"

elif args.protocol == "mesi2_inc_nobdi":
    cmd_list[0] += f" --l2_data_segment_size 64"
    cmd_list[0] += f" --l2_data_regions 1"
elif args.protocol == "mesi2_inc_bdi":
    cmd_list[0] += f" --l2factor_bdi {args.l2factor}"
    cmd_list[0] += f" --l2_data_segment_size {args.l2_data_segment_size}"
    cmd_list[0] += f" --l2_data_regions {args.l2_data_regions}"


if args.protocol == "msi_nine_xor_bdi_map":
    cmd_list[0] += f" --index_bits_shift {args.index_bits_shift}"
else:
    cmd_list[0] += f" --index_bits_shift 0"

if args.use_anonymous_latency:
    cmd_list[0] += f" --anonymous_latency 1"
if args.record_line_level_entropy == True:
    cmd_list[0] += f" --record_line_level_entropy"
if args.xor_folding_scheme:
    cmd_list[0] += f" --xor_folding_scheme {args.xor_folding_scheme}"
# if args.ooo == True:
#     cmd_list[0] += f" --ooo"

if args.core:
    cmd_list[0] += f" --core {args.core}"
if args.numProcesses:
    cmd_list[0] += f" --numProcesses {args.numProcesses}"
if args.run:
    cmd_list[0] += f" --run {args.run}"
    

cmd_list[0] += f" --partition 1"
cmd_list[0] += f" --size {args.size}"
cmd_list[0] += f" --fully_util {args.fully_util}"
cmd_list[0] += f" --seed {args.seed}"

############# - copy disk image as local - #############
if args.image_path_override != None:
    default_download_path = args.image_path_override
else:
    if args.home == True:
        default_dir = f"/mnt/disk2/spec-2017-flexible-image"
        dest_dir = default_dir
    else:
        default_dir = f"{os.path.expanduser('~')}/repo/gem5-resources/src/spec-2017-flexible/disk-image/spec-2017-flexible/spec-2017-flexible-image"
        dest_dir = f"{os.path.expanduser('~')}/data/spec2017-flexible-img-copy"

    default_download_path = f"{default_dir}/spec-2017-flexible"
# mnt_path = f"{dest_dir}/restore_spec-2017-flexible-{args.protocol}_{args.run}_{args.size}_c{args.core}_{args.l2size}"
if not os.path.exists(f"{default_download_path}"):
    logger.error(f"disk image spec-2017-flexible not found at {default_download_path}...")

cmd_list[0] += f" --image {default_download_path}"



############# - launch - #############
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
    # tick = int(out.split("Exiting @ tick ")[-1].split(" because")[0])
    # logger.info(f"tick={tick}")


else:
    # nonblocking
    logger.warning(f"nonblocking since {args.flags} enabled")
    with open(f"{path}/err.txt","w") as err, open(f"{path}/out.txt","w") as out:
        p = subprocess.Popen(cmd_list, shell=True, stdout=out, stderr=err)
        print(f'Launched:  ')
        print(f'{p.args}')
