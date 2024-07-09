# runs example config at configs/my_configs/fs/ruby/parsec/checkpointing/x86-parsec-save-checkpoint.py
# compile:
#scons build/X86_MyMESI2/gem5.opt --default=X86 PROTOCOL=MESI_Two_Level_my SLICC_HTML=True -j24
#scons build/X86_test/gem5.opt -j24 --default=x86

import sys
import argparse, subprocess, os
from loguru import logger
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
    "--size",
    type=str,
    required=True,
    help="size",
)
parser.add_argument(
    "--core",
    type=int,
    required=False,
    default=2,
    help="core ct",
)
parser.add_argument(
    "--no_use_local",
    type=bool,
    required=False,
    default=False,
    help="copy x86_parsec disk image to output dir",
)
parser.add_argument(
    "--home",
    type=bool,
    required=False,
    default=False,
    help="set when running on home computer, mnt dir",
)
parser.add_argument(
    "--use_deprecated",
    type=bool,
    required=False,
    default=False,
    # action='store_true',
    help="use deprecated scripts",
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
elif args.protocol == "no":
    design = ""
else: assert False

testname= "ckpt/fs_ruby_parsec"
path = f"m5out/{testname}/{args.protocol}_c{args.core}_{args.size}/{args.benchmark}"

isExist = os.path.exists(path)
if not isExist:
   os.makedirs(path)

if design == "": gem5_binary = f"build/X86/gem5.opt"
else:gem5_binary = f"build/X86_{design}/gem5.opt"

if not os.path.isfile(gem5_binary): 
    logger.error(f"gem5 binary file ({gem5_binary}) not exist!")
    exit(1)

if args.use_deprecated:
    cmd_list = [f"nohup time {gem5_binary} -d {path} " + \
        f"configs/example/fs.py --kernel ~/.cache/gem5/x86-linux-kernel-4.19.83 --work-begin-exit-count=1 --checkpoint-at-end"
            ]
    if args.core:
        cmd_list[0] += f" --num-cpus {args.core} --num-dirs {args.core}"

    cmd_list[0] += f" --benchmark {args.benchmark} --size {args.size}"
else:
    cmd_list = [f"nohup time {gem5_binary} -d {path} " + \
        f"{debug_flag} {debug_interval} configs/my_configs/fs/ruby/parsec/checkpointing/x86-parsec-save-checkpoint.py"
            ]
    cmd_list[0] += f" --protocol {args.protocol}"
    if args.core:
        cmd_list[0] += f" --core {args.core}"

    cmd_list[0] += f" --benchmark {args.benchmark} --size {args.size}"

assert args.no_use_local == False

############# - copy disk image as local - #############
if args.home == True:
    default_dir = f"/mnt/disk2/parsec-img-copy"
else:
    default_dir = f"{os.path.expanduser('~')}/data/parsec-img-copy"
    
default_download_path = f"{default_dir}/x86-parsec"
mnt_path = f"{default_dir}/ckpt_x86-parsec-{args.protocol}_{args.benchmark}_{args.size}_c{args.core}"

if args.use_deprecated: cmd_list[0] += f" --disk-image {mnt_path}"
else: cmd_list[0] += f" --path {mnt_path}"
# create a local copy
if not os.path.exists(f"{mnt_path}/x86-parsec"):
    # home = os.path.expanduser("~")
    if not os.path.exists(default_download_path):
        logger.error(f"{default_download_path} does not exist!")
        exit(1)
    import shutil
    logger.info(f"creating a local copy of x86-parsec at {mnt_path}...")
    isExist = os.path.exists(mnt_path)
    if not isExist:
        os.makedirs(mnt_path)
    shutil.copy2(default_download_path, mnt_path)
else:
    logger.info(f"already existing x86-parsec at {mnt_path}...")


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

    # removing the local disk image copy
    if mnt_path and os.path.exists(mnt_path):
        logger.info(f"removing local dir {mnt_path}")
        try:
            import shutil
            shutil.rmtree(mnt_path)
        except OSError as e:
            print("Error: %s - %s." % (e.filename, e.strerror))

else:
    # nonblocking
    logger.warning(f"nonblocking since {args.flags} enabled")
    with open(f"{path}/err.txt","w") as err, open(f"{path}/out.txt","w") as out:
        p = subprocess.Popen(cmd_list, shell=True, stdout=out, stderr=err)
        print(f'Launched:  ')
        print(f'{p.args}')
