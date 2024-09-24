# conpile:
#scons build/X86_MyMESI2/gem5.opt --default=X86 PROTOCOL=MESI_Two_Level_my SLICC_HTML=True -j24
#scons build/X86_test/gem5.opt -j24 --default=x86

import sys
import argparse, subprocess, os, re
from tqdm import tqdm
from scipy.stats import gmean
from loguru import logger
parser = argparse.ArgumentParser(description="config.")

parser.add_argument(
    "--flags",
    type=str,
    required=False,
    help="flag",
    nargs='+',
)
parser.add_argument(
    "--dfile",
    type=str,
    required=False,
    help="debug file",
)
parser.add_argument(
    "--protocol",
    type=str,
    help="which protocol to run",
    choices=["baseline", "noisy", "decoupled", "compress", "dedup","bdixor",
             "msi",

             "msi_nine_xor_bdi_map", "msi_nine_noxor_bdi_map",
             "msi_nine_xor_nobdi_map", "msi_nine_noxor_nobdi_map",
             ],
    required=True,
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
    "--benchmark",
    type=str,
    required=True,
    help="benchname",
)
parser.add_argument(
    "--suffix",
    type=str,
    required=False,
    help="bench suffix",
)
parser.add_argument(
    "--core",
    type=int,
    required=False,
    default=1,
    help="core ct",
)

parser.add_argument('--record_line_level_entropy', action='store_true')
parser.add_argument('--no-record_line_level_entropy', dest='record_line_level_entropy', action='store_false')
parser.set_defaults(record_line_level_entropy=False)
# parser.add_argument(
#     "--use_local",
#     type=bool,
#     required=False,
#     default=True,
#     help="copy a disk image to output dir",
# )
args = parser.parse_args()


if args.protocol == "baseline":
    design = ""
    design_out = "test"
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
elif args.protocol == "msi":
    design = "MyMSI"
    design_out = design
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
else: assert False

testname= "fs_custombianry"

path = f"m5out/m5out_{testname}/{design_out}/{args.benchmark}"
isExist = os.path.exists(path)
if not isExist:
   os.makedirs(path)

if design == "": binary = "X86"
else: binary = f"X86_{design}"
if not os.path.isfile(f"build/{binary}/gem5.opt"): 
    print(f"gem5 binary file not exist!")
    exit(1)

debug_interval = ""
if args.begin and args.end:
    interval = (args.begin, args.end)
    debug_interval = f'--debug-start={interval[0]} --debug-end={interval[1]}'

debug_flag = ""
if args.flags:
    debug_flag = "--debug-flags="
    debug_flag += ",".join(args.flags)
    if args.dfile:
        debug_flag += f" --debug-file={args.dfile}"

cmd_list = [f"nohup time build/{binary}/gem5.opt -d {path} " + \
f"{debug_flag} {debug_interval} configs/my_configs/fs/ruby/custombinary/custombinary.py"
    ]
cmd_list[0] += f" --image /home/zhewen/repo/gem5-resources/src/custom_binary/disk-image/custom_binary/custom_binary-image/custom_binary"
cmd_list[0] += f" --protocol {args.protocol}"

# if args.use_local == True:
#     assert(False)
#     cmd_list[0] += f" --path {args.path}"

if args.core:
    cmd_list[0] += f" --core {args.core}"
if args.suffix:
    cmd_list[0] += f" --suffix {args.suffix}"


cmd_list[0] += f" --benchmark {args.benchmark} --partition 1"
    
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
