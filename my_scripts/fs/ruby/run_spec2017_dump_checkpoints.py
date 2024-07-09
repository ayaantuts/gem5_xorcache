# this script uses x86_dump binary to dump cache content and address periodically

# conpile:
#scons build/X86_MyMESI2/gem5.opt --default=X86 PROTOCOL=MESI_Two_Level_my SLICC_HTML=True -j24
#scons build/X86_test/gem5.opt -j24 --default=x86

import sys
import argparse, subprocess, os, re
parser = argparse.ArgumentParser(description="config.")
# parser.add_argument(
#     "--protocol",
#     type=str,
#     help="which protocol to run",
#     choices=["baseline", "noisy", "decoupled","compress","dedup", "bdixor"],
#     required=True,
# )

parser.add_argument(
    "--plotly",
    type=int,
    required=False,
    help="use plotly to plot ipc",
    default=1,
)
parser.add_argument(
    "--mode",
    type=str,
    required=False,
    help="tick or inst mode",
    choices=["tick", "inst", "kvm"],
    default="inst",
)
parser.add_argument(
    "--run",
    type=int,
    required=False,
    help="index of this run",
)
parser.add_argument(
    "--benchmark",
    type=str,
    required=False,
    help="select which benchmark to run (the only one).",
)
parser.add_argument(
    "--num_checkpoint",
    type=int,
    required=False,
    help="Number of checkpoints/snapshots to take.",
    default=100,
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
    "--size",
    type=str,
    required=False,
    help="benchmark size",
    default="ref",
)
parser.add_argument(
    "--core",
    type=int,
    required=False,
    help="core ct",
)
parser.add_argument(
    "--numProcesses",
    type=int,
    required=False,
    help="process count",
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
    required=False,
    default=100,
    help="random seed for random number generator",
)

parser.add_argument(
    "--image",
    type=str,
    required=False,
    help="benchmark size",
    default="/home/zhewen/repo/gem5-resources/src/spec-2017-flexible/disk-image/spec-2017-flexible/spec-2017-flexible-image/spec-2017-flexible",
)

args = parser.parse_args()

design = "dump"


testname= "fs_spec2017_cachedump"
if args.mode == "inst":
    py_config_file_name = "spec2017-checkpoint.py"
elif args.mode == "tick":
    py_config_file_name = "spec2017-checkpoint-tickver.py"
elif args.mode == "kvm":
    py_config_file_name = "spec2017-checkpoint-tickver-kvm.py"
else: assert False

if args.benchmark:
    path = f"m5out/m5out_{testname}/{design}/core{args.core}_{args.benchmark}_full{args.fully_util}"
else:
    path = f"m5out/m5out_{testname}/{design}/core{args.core}_proc{args.numProcesses}_run{args.run}_seed{args.seed}"

isExist = os.path.exists(path)
if not isExist:
   os.makedirs(path)

if args.plotly == 0:
    gem5_binary_path = f"build/X86_{design}/gem5.fast"
    if not os.path.isfile(gem5_binary_path): 
        gem5_binary_path = f"build/X86_{design}/gem5.opt"
        if not os.path.isfile(gem5_binary_path): 
            print(f"gem5 binary file not exist!")
            exit(1)
elif args.plotly == 1:
    gem5_binary_path = f"build/X86_{design}/gem5.opt"
    if not os.path.isfile(gem5_binary_path): 
        print(f"gem5 binary file not exist!")
        exit(1)
else: assert False

debug_interval = ""
if args.begin and args.end:
    interval = (args.begin, args.end)
    debug_interval = f'--debug-start={interval[0]} --debug-end={interval[1]}'

debug_flag = ""
if args.flags:
    debug_flag = "--debug-flags="
    debug_flag += ",".join(args.flags)

if args.plotly == 1:
    cmd_list = [f"nohup time {gem5_binary_path} -d {path} " + \
    f"{debug_flag} {debug_interval} configs/my_configs/fs/ruby/spec2017/{py_config_file_name}"
        ]
else:
    cmd_list = [f"{gem5_binary_path} -d {path} " + \
    f"{debug_flag} {debug_interval} configs/my_configs/fs/ruby/spec2017/{py_config_file_name}"
        ]

cmd_list[0] += f" --image {args.image}"
# cmd_list[0] += f" --protocol {args.protocol}"


if args.core:
    cmd_list[0] += f" --core {args.core}"
if args.numProcesses:
    cmd_list[0] += f" --numProcesses {args.numProcesses}"
if args.benchmark: 
    cmd_list[0] += f" --benchmark {args.benchmark}"
if args.run:
    cmd_list[0] += f" --run {args.run}"
    

cmd_list[0] += f" --partition 1"
cmd_list[0] += f" --size {args.size}"
cmd_list[0] += f" --fully_util {args.fully_util}"
cmd_list[0] += f" --seed {args.seed}"
cmd_list[0] += f" --num_checkpoint {args.num_checkpoint}"
cmd_list[0] += f" --plotly {args.plotly}"
    
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
    