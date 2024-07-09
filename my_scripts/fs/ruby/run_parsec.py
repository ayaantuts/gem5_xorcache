# runs example config at configs/example/gem5_library/x86-parsec-benchmarks.py
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
             "xor_001","xor_011","xor_101","xor_111",
             "xor_002","xor_012","xor_102","xor_112",
             "xor_003","xor_013","xor_103","xor_113",
             "xor_004","xor_014","xor_104","xor_114",
             "msi","msi_nine",
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
parser.add_argument(
    "--cache_level",
    type=int,
    required=False,
    default=2,
    help="cache hierarchy level",
)
parser.add_argument(
    "--l2size",
    type=str,
    required=False,
    default="256kB",
    help="l2size string",
    choices=["64kB", "128kB","256kB","512kB","1024kB","2048kB"],
)
parser.add_argument(
    "--no_use_local",
    type=bool,
    required=False,
    default=False,
    help="copy x86_parsec disk image to output dir",
)
parser.add_argument(
    "--fast",
    type=bool,
    required=False,
    default=False,
    help="use fast version of gem5",
)
parser.add_argument(
    "--condor",
    type=bool,
    required=False,
    default=False,
    help="set when running on condor",
)
parser.add_argument(
    "--home",
    type=bool,
    required=False,
    default=False,
    help="set when running on home computer, mnt dir",
)
parser.add_argument(
    "--use_anonymous_latency",
    type=bool,
    required=False,
    default=False,
    help="assign cache latency regardless of size",
)
parser.add_argument(
    "--ooo",
    type=bool,
    required=False,
    default=False,
    # action='store_true',
    help="use ooo core",
)
args = parser.parse_args()

if args.condor:
    assert args.no_use_local == True, "must enable no_use_local to false when running on condor"
    assert not args.flags, "are u sure?"

if args.cache_level == 2:
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

    else: assert False
elif args.cache_level == 3:
    if args.protocol == "baseline":
        design = "MyMESI3_Silent"
    else:
        assert False
else: assert False

testname= "fs_ruby_parsec"
if args.use_anonymous_latency:
    path = f"m5out/m5out_{testname}/anonymous_latency/version{args.version}/{design_out}_{args.l2size}/c{args.core}/{args.size}/{args.benchmark}"
    if args.fast == True:
        path = f"m5out/m5out_{testname}/anonymous_latency/version{args.version}_fast/{design_out}_{args.l2size}/c{args.core}/{args.size}/{args.benchmark}"
else: 
    path = f"m5out/m5out_{testname}/version{args.version}/{design_out}_{args.l2size}/c{args.core}/{args.size}/{args.benchmark}"
    if args.fast == True:
        path = f"m5out/m5out_{testname}/version{args.version}_fast/{design_out}_{args.l2size}/c{args.core}/{args.size}/{args.benchmark}"

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

if args.condor:
        cmd_list = [f"nohup {gem5_binary} -d {path} " + \
            f"{debug_flag} {debug_interval} configs/my_configs/fs/ruby/parsec/x86-parsec-noKVM.py"
                ]
else:
    cmd_list = [f"nohup time {gem5_binary} -d {path} " + \
        f"{debug_flag} {debug_interval} configs/my_configs/fs/ruby/parsec/x86-parsec.py"
            ]
cmd_list[0] += f" --protocol {args.protocol}"
if args.core:
    cmd_list[0] += f" --core {args.core}"
# if args.cache_level:
    # cmd_list[0] += f" --cache_level {args.cache_level}"
if args.l2size:
    cmd_list[0] += f" --l2size {args.l2size}"
if args.ooo:
    cmd_list[0] += f" --ooo 1"
if args.use_anonymous_latency:
    cmd_list[0] += f" --anonymous_latency 1"

cmd_list[0] += f" --benchmark {args.benchmark} --size {args.size}"

if args.no_use_local == False:
    if args.home == True:
        default_dir = f"/mnt/disk2/parsec-img-copy"
    else:
        default_dir = f"{os.path.expanduser('~')}/data/parsec-img-copy"
        
    default_download_path = f"{default_dir}/x86-parsec"
    mnt_path = f"{default_dir}/x86-parsec-{args.protocol}{args.cache_level}_{args.benchmark}_{args.size}_c{args.core}_{args.l2size}_ver{args.version}"
    if args.fast == True:
        mnt_path += "_fast"
    cmd_list[0] += f" --path {mnt_path}"
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

if args.condor:
    condor_path = "../"
    if not os.path.exists(f"{condor_path}"):
        logger.error(f"{condor_path} does not exist!")
        exit(1)
    cmd_list[0] += f" --path {condor_path}"

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
