# runs example config at configs/example/gem5_library/x86-parsec-benchmarks-checkpoint.py
# compile:
#scons build/X86_MyMESI2/gem5.opt --default=X86 PROTOCOL=MESI_Two_Level_my SLICC_HTML=True -j24
#scons build/X86_test/gem5.opt -j24 --default=x86

import sys
import argparse, subprocess, os, re
from loguru import logger
parser = argparse.ArgumentParser(description="config.")
parser.add_argument(
    "--protocol",
    type=str,
    help="which protocol to run",
    choices=["baseline", "noisy", "decoupled", "compress", "dedup","bdixor",
             "dump",
             "xor_001","xor_011","xor_101","xor_111",
             "xor_002","xor_012","xor_102","xor_112",
             "xor_003","xor_013","xor_103","xor_113",
             "xor_004","xor_014","xor_104","xor_114",
             "msi",
             ],
    required=True,
)
parser.add_argument(
    "--cachecfg",
    type=str,
    required=False,
    help="for 3 level cache, choose either skylake or worse",
    choices=["skylake", "realistic"],
    default="skylake",
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
    "--version",
    type=int,
    required=True,
    help="ver",
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
# parser.add_argument(
#     "--no_use_local",
#     type=bool,
#     required=False,
#     default=False,
#     help="copy x86_parsec disk image to output dir",
# )
parser.add_argument(
    "--fast",
    type=bool,
    required=False,
    default=False,
    help="use fast version of gem5",
)
# parser.add_argument(
#     "--home",
#     type=bool,
#     required=False,
#     default=False,
#     help="set when running on home computer, mnt dir",
# )
# parser.add_argument(
#     "--use_anonymous_latency",
#     type=bool,
#     required=False,
#     default=False,
#     help="assign cache latency regardless of size",
# )
parser.add_argument(
    "--ooo",
    type=bool,
    required=False,
    default=False,
    # action='store_true',
    help="use ooo core",
)
args = parser.parse_args()



if args.protocol == "dump":
    design = "DUMP"
    design_out = design
else: assert False

testname= "fs_ruby_parsec_cachedump"
# if args.use_anonymous_latency:
path = f"m5out/m5out_{testname}/anonymous_latency/version{args.version}/{design_out}_{args.cachecfg}/c{args.core}/{args.size}/{args.benchmark}"
if args.fast == True:
    path = f"m5out/m5out_{testname}/anonymous_latency/version{args.version}_fast/{design_out}_{args.cachecfg}/c{args.core}/{args.size}/{args.benchmark}"
# else: 
#     path = f"m5out/m5out_{testname}/version{args.version}/{design_out}_{args.cachecfg}/c{args.core}/{args.size}/{args.benchmark}"
#     if args.fast == True:
#         path = f"m5out/m5out_{testname}/version{args.version}_fast/{design_out}_{args.cachecfg}/c{args.core}/{args.size}/{args.benchmark}"

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

debug_interval = ""
if args.begin and args.end:
    interval = (args.begin, args.end)
    debug_interval = f'--debug-start={interval[0]} --debug-end={interval[1]}'

debug_flag = ""
if args.flags:
    debug_flag = "--debug-flags="
    debug_flag += ",".join(args.flags)


cmd_list = [f"nohup time {gem5_binary} -d {path} " + \
    f"{debug_flag} {debug_interval} configs/my_configs/fs/ruby/parsec/x86-parsec-checkpoint.py"
        ]
cmd_list[0] += f" --protocol {args.protocol}"
if args.core:
    cmd_list[0] += f" --core {args.core}"
if args.ooo:
    cmd_list[0] += f" --ooo 1"
# if args.use_anonymous_latency:
#     cmd_list[0] += f" --anonymous_latency 1"

cmd_list[0] += f" --benchmark {args.benchmark} --size {args.size}"

if args.cachecfg:
    cmd_list[0] += f" --cachecfg {args.cachecfg}"
    
# if args.no_use_local == False:
#     if args.home == True:
#         default_dir = f"/mnt/disk2/parsec-img-copy"
#     else:
#         default_dir = f"{os.path.expanduser('~')}/data/parsec-img-copy"
        
#     default_download_path = f"{default_dir}/x86-parsec"
#     mnt_path = f"{default_dir}/x86-parsec-{args.protocol}{args.cache_level}_{args.benchmark}_{args.size}_c{args.core}_{args.l2size}_ver{args.version}"
#     if args.fast == True:
#         mnt_path += "_fast"
#     cmd_list[0] += f" --path {mnt_path}"
#     # create a local copy
#     if not os.path.exists(f"{mnt_path}/x86-parsec"):
#         # home = os.path.expanduser("~")
#         if not os.path.exists(default_download_path):
#             logger.error(f"{default_download_path} does not exist!")
#             exit(1)
#         import shutil
#         logger.info(f"creating a local copy of x86-parsec at {mnt_path}...")
#         isExist = os.path.exists(mnt_path)
#         if not isExist:
#             os.makedirs(mnt_path)
#         shutil.copy2(default_download_path, mnt_path)
#     else:
#         logger.info(f"already existing x86-parsec at {mnt_path}...")


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
    # if mnt_path and os.path.exists(mnt_path):
    #     logger.info(f"removing local dir {mnt_path}")
    #     try:
    #         import shutil
    #         shutil.rmtree(mnt_path)
    #     except OSError as e:
    #         print("Error: %s - %s." % (e.filename, e.strerror))

else:
    # nonblocking
    logger.warning(f"nonblocking since {args.flags} enabled")
    with open(f"{path}/err.txt","w") as err, open(f"{path}/out.txt","w") as out:
        p = subprocess.Popen(cmd_list, shell=True, stdout=out, stderr=err)
        print(f'Launched:  ')
        print(f'{p.args}')
