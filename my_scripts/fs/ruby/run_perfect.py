# conpile:
#scons build/X86_MyMESI2/gem5.opt --default=X86 PROTOCOL=MESI_Two_Level_my SLICC_HTML=True -j24
#scons build/X86_test/gem5.opt -j24 --default=x86

import sys
import argparse, subprocess, os, re
from tqdm import tqdm
from scipy.stats import gmean
parser = argparse.ArgumentParser(description="config.")
parser.add_argument(
    "--protocol",
    type=str,
    help="which protocol to run",
    choices=["baseline", "noisy", "decoupled","compress","dedup", "bdixor","hammer","dump"],
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
    "--flags",
    type=str,
    required=False,
    help="flag",
    nargs='+',
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
# parser.add_argument(
#     "--suffix",
#     type=str,
#     required=False,
#     help="bench suffix",
# )
parser.add_argument(
    "--core",
    type=int,
    required=False,
    help="core ct",
)
# parser.add_argument(
#     "--use_local",
#     type=bool,
#     required=False,
#     default=True,
#     help="copy a disk image to output dir",
# )
parser.add_argument(
    "--hook",
    type=bool,
    required=False,
    default=True,
    help="by default, we use hook to annotate ROI",
)
args = parser.parse_args()


if args.protocol == "baseline":
    design = "test"
elif args.protocol == "noisy":
    design = "MyMESI2"
elif args.protocol == "decoupled":
    design = "MyMESI2_Decoupled"
elif args.protocol == "compress":
    design = "MyMESI2_Compress"
elif args.protocol == "dedup":
    design = "MyMESI2_Dedup"
elif args.protocol == "bdixor":
    design = "MyMESI2_BDI_XOR"
elif args.protocol == "hammer":
    design = "MOESI_hammer"
elif args.protocol == "dump":
    design = "dump"
else: assert False

if args.hook:
    testname= "fs_perfect"
    py_config_file_name = "perfect-hook.py"
else:
    testname= "fs_perfect_no_hook"
    py_config_file_name = "perfect.py"

path = f"m5out/m5out_{testname}/{design}/{args.benchmark}"
isExist = os.path.exists(path)
if not isExist:
   os.makedirs(path)

if not os.path.isfile(f"build/X86_{design}/gem5.opt"): 
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

cmd_list = [f"nohup time build/X86_{design}/gem5.opt -d {path} " + \
f"{debug_flag} {debug_interval} configs/my_configs/fs/ruby/perfect/{py_config_file_name}"
    ]
cmd_list[0] += f" --image /home/zhewen/repo/gem5-resources/src/perfect/disk-image/perfect/perfect-image/perfect"
cmd_list[0] += f" --protocol {args.protocol}"
cmd_list[0] += f" --set {args.set}"

# if args.use_local == True:
#     assert(False)
#     cmd_list[0] += f" --path {args.path}"

if args.core:
    cmd_list[0] += f" --core {args.core}"
# if args.suffix:
#     cmd_list[0] += f" --suffix {args.suffix}"


cmd_list[0] += f" --benchmark {args.benchmark} --partition 1"
    
if not args.flags:
    p = subprocess.Popen(cmd_list, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(f'Launched:  ')
    print(f'{p.args}')
    out,err = p.communicate()
    out = out.decode('utf-8')
    err = err.decode('utf-8')
    # print(out)
    if err: 
        print(err)
        ferr = open(f"{path}/err.txt","w")
        ferr.write(err)
        ferr.write(f'{p.args}')
        ferr.close()


    fout = open(f"{path}/out.txt","w")
    fout.write(out)
else:
    # nonblocking
    print(f"nonblocking since {args.flags} enabled")
    with open(f"{path}/err.txt","w") as err, open(f"{path}/out.txt","w") as out:
        p = subprocess.Popen(cmd_list, shell=True, stdout=out, stderr=err)
        print(f'Launched:  ')
        print(f'{p.args}')
    