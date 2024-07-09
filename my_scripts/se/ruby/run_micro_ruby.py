# compile
# scons build/X86_test/gem5.opt --default=X86 PROTOCOL=MESI_Two_Level SLICC_HTML=True -j24

import sys
import argparse, subprocess, os, re
from tqdm import tqdm
from scipy.stats import gmean

parser = argparse.ArgumentParser(description="config.")
parser.add_argument(
    "--protocol",
    type=str,
    help="which protocol to run",
    choices=["baseline", "noisy", "decoupled", "bdixor"],
    required=True,
)
parser.add_argument(
    "--path",
    type=str,
    required=False,
    help="path to binary",
)
parser.add_argument(
    "--mode",
    type=str,
    choices=['profile', 'interval-debug', 'fullrun-debug', 'roi-debug', 'direct', 'help'],
    required=True,
    help="mode",
)
parser.add_argument(
    "--debug",
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
args = parser.parse_args()


if args.mode != 'help':
    assert args.path

if args.mode == 'profile':
    debug = ['PseudoInst']
    interval = None
elif args.mode == 'interval-debug':
    assert args.debug and args.begin and args.end
    debug = args.debug
    interval = (args.begin, args.end)
elif args.mode == 'fullrun-debug':
    assert args.debug
    debug = args.debug
    interval = None
elif args.mode == 'roi-debug':
    assert False
elif args.mode == 'direct':
    debug = None
    interval = None
elif args.mode == 'help':
    debug = None
    interval = None

if debug and len(debug) > 0: debug_flag = "--debug-flags="+",".join(debug)
else: debug_flag = ''
if interval: debug_interval = f'--debug-start={interval[0]} --debug-end={interval[1]}'
else: debug_interval = ''

if args.protocol == "baseline":
    name_ = "X86_test"
    suf = ""
elif args.protocol == "noisy":
    name_ = "X86_MyMESI2"
    suf = "-mymesi"
elif args.protocol == "decoupled":
    name_ = "X86_MyMESI2_Decoupled"
    suf = "-mymesidecoupled"
else: assert False

path = f"m5out/m5out_micro/ruby/{name_}"
isExist = os.path.exists(path)
if not isExist:
   os.makedirs(path)

if not os.path.isfile(f"build/{name_}/gem5.opt"): 
    print(f"gem5 binary file not exist!")
    exit(1)
if args.mode != 'help' and not os.path.isfile(args.path): 
    print(f"guest binary file not exist!")
    exit(1)
cmd_list = [f"nohup time build/{name_}/gem5.opt {debug_flag} {debug_interval} -d {path} " + \
   f"configs/my_configs/se/ruby/x86-custombinary-ruby{suf}.py " + \
    "--l1d_size=64kB " + \
    "--l1i_size=64kB " + \
    "--l2_size=128kB " + \
    "--frequency=1GHz " + \
    f"--path={args.path}"
    ]
if args.mode == 'help':
   cmd_list = [f"build/{name_}/gem5.opt " + \
        "--debug-help"
    ]
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

if args.mode == 'help':
    print(out)
else:
    fout = open(f"{path}/out.txt","w")
    fout.write(out)

