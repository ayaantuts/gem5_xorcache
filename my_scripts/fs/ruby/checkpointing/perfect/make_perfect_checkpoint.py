# conpile:
#scons build/X86_MyMESI2/gem5.opt --default=X86 PROTOCOL=MESI_Two_Level_my SLICC_HTML=True -j24
#scons build/X86_test/gem5.opt -j24 --default=x86

import sys
import argparse, subprocess, os, re
from loguru import logger
from tqdm import tqdm
from scipy.stats import gmean
parser = argparse.ArgumentParser(description="config.")
parser.add_argument(
    "--protocol",
    type=str,
    help="which protocol to run",
    choices=["no", "hammer"], # only hammer and no are supported for checkpoint
    required=True,
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
    "--benchmark",
    type=str,
    required=True,
    help="benchname",
)
parser.add_argument(
    "--set",
    type=str,
    required=False,
    default="ser",
    help="run config",
    choices=["ser", "omp"],
)
parser.add_argument(
    "--core",
    type=int,
    required=False,
    default=1,
    help="core ct",
)
parser.add_argument(
    "--hook",
    type=bool,
    required=False,
    default=True,
    help="by default, we use hook to annotate ROI",
)
parser.add_argument(
    "--disassemble",
    type=bool,
    required=False,
    default=False,
    help="by default, we don't need to disassemble",
)
parser.add_argument(
    "--kernel_args",
    required=False,
    type=str,
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

if args.protocol == "hammer":
    design = "MOESI_hammer"
    design_nickname = design
elif args.protocol == "no":
    design = ""
    design_nickname = "no_cache"
else: assert False

if args.hook:
    testname= "fs_perfect"
    py_config_file_name = "perfect-hook-save-checkpoint.py"
    if args.disassemble:
        testname += "_disassemble"
        py_config_file_name = "perfect-hook-disassemble-save-checkpoint.py"
else:
    assert False


path = f"m5out/m5out_{testname}/{design_nickname}/{args.set}_core{args.core}/{args.benchmark}"

isExist = os.path.exists(path)
if not isExist:
   os.makedirs(path)

if design == "": gem5_binary = f"build/X86/gem5.opt"
else:gem5_binary = f"build/X86_{design}/gem5.opt"

if not os.path.isfile(gem5_binary): 
    logger.error(f"gem5 binary file ({gem5_binary}) not exist!")
    exit(1)


cmd_list = [f"nohup time {gem5_binary} -d {path} " + \
f"{debug_flag} {debug_interval} configs/my_configs/fs/ruby/perfect/checkpointing/{py_config_file_name} "
    ]
cmd_list[0] += f" --image /gem5_xorcache/system_files/disks/x86-ubuntu.img"
if args.kernel_args: cmd_list[0] += f" --kernel_args {args.kernel_args}"
cmd_list[0] += f" --protocol {args.protocol}"
cmd_list[0] += f" --set {args.set}"


if args.core:
    cmd_list[0] += f" --core {args.core}"


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
