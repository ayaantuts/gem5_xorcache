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
    choices=["baseline", "noisy", "decoupled", "compress", "bdixor","xor",
             "msi","msi_nine", 
             "msi_nine_xor_bdi_map", "msi_nine_noxor_bdi_map",
             "msi_nine_xor_nobdi_map", "msi_nine_noxor_nobdi_map",
             ],
    required=True,
)
parser.add_argument(
    "--run",
    type=int,
    required=True,
    help="ver",
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
    "--path",
    type=str,
    required=False,
    help="path to binary",
)
parser.add_argument(
    "--arg",
    type=str,
    required=False,
    help="extra args",
)
parser.add_argument(
    "--core",
    type=int,
    required=False,
    help="core ct",
)
parser.add_argument(
    "--ignore_proactive_eviction",
    action='store_true',
    required=False,
    help="ignore proactive evictions",
)

parser.add_argument(
    "--search_in_bank",
    action='store_true',
    required=False,
    help="search xor candidates in bank",
)
parser.add_argument(
    "--xor_policy",
    type=int,
    required=False,
    default=1,
    help="xor policy id, default=1",
)
parser.add_argument(
    "--non_blocking",
    action='store_true',
    help="do not block",
)
parser.add_argument(
    "--o3",
    action='store_true',
    required=False,
    help="use o3 cpu",
)

args = parser.parse_args()
assert(args.run>0)
if args.path:
    assert(args.core)

if args.protocol == "baseline":
    design = "test"
    design_out = design
elif args.protocol == "noisy":
    design = "MyMESI2"
    design_out = design
elif args.protocol == "decoupled":
    design = "MyMESI2_Decoupled"
    design_out = design
elif args.protocol == "compress":
    design = "MyMESI2_Compress"
    design_out = design
elif args.protocol == "bdixor":
    design = "MyMESI2_BDI_XOR"
    design_out = design
    if args.search_in_bank: design_out+="_bank"
    if args.ignore_proactive_eviction: design_out+="_noProactive"
    if args.xor_policy > 1:
        if args.xor_policy == 2 or args.xor_policy == 4 or args.xor_policy == 6: design_out+="_nongreedy"
        if args.xor_policy == 3 or args.xor_policy == 4: design_out+= "_mru"
        if args.xor_policy == 5 or args.xor_policy == 6: design_out+= "_lru"
        # else: assert False

elif args.protocol == "xor":
    design = "MyMESI2_BDI_XOR"
    design_out = "MyMESI2_XOR"
    if args.search_in_bank: design_out+="_bank"
    if args.ignore_proactive_eviction: design_out+="_noProactive"
    if args.xor_policy > 1:
        if args.xor_policy == 2 or args.xor_policy == 4 or args.xor_policy == 6: design_out+="_nongreedy"
        if args.xor_policy == 3 or args.xor_policy == 4: design_out+= "_mru"
        if args.xor_policy == 5 or args.xor_policy == 6: design_out+= "_lru"
        # else: 
        #     print(args.xor_policy)
        #     assert False
elif args.protocol == "msi":
    design = "MyMSI"
    design_out = design
elif args.protocol == "msi_nine":
    design = "MyMSI_NINE"
    design_out = design
elif args.protocol == "msi_nine_xor":
    design = "MyMSI_NINE_XOR"
    design_out = design
elif args.protocol == "msi_nine_noxor":
    design = "MyMSI_NINE_XOR"
    design_out = "MyMSI_NINE_NOXOR"
elif args.protocol == "msi_nine_xor_bdi_map":
    design = "MyMSI_NINE_XOR_MAP"
    design_out = "MyMSI_NINE_XOR_BDI_MAP"
elif args.protocol == "msi_nine_noxor_bdi_map":
    design = "MyMSI_NINE_XOR_MAP"
    design_out = "MyMSI_NINE_NOXOR_BDI_MAP"
elif args.protocol == "msi_nine_xor_nobdi_map":
    design = "MyMSI_NINE_XOR_MAP"
    design_out = "MyMSI_NINE_XOR_NOBDI_MAP"
elif args.protocol == "msi_nine_noxor_nobdi_map":
    design = "MyMSI_NINE_XOR_MAP"
    design_out = "MyMSI_NINE_NOXOR_NOBDI_MAP"
else: assert False

testname= "simpleruby"

# defaults
test_prog_name = "threads"
core_num = 2
numvals = 100
bm_size = f"{int(int(numvals)/int(core_num))}val"

if args.path:
    test_prog_name = args.path.split("/")[-1]
    core_num = args.core
    if args.arg: numvals=args.arg
    bm_size = f"{int(int(numvals)/int(core_num))}val"

path = f"m5out/m5out_{testname}/{design_out}/run{args.run}/c{core_num}/{bm_size}/{test_prog_name}"
print(path)
isExist = os.path.exists(path)
if not isExist:
   os.makedirs(path)

if not os.path.isfile(f"build/X86_{design}/gem5.opt"): 
    print(f"gem5 binary file not exist!")
    exit(1)

debug_interval = ""
if args.end:
    interval = (args.begin, args.end)
    debug_interval = f'--debug-start={interval[0]} --debug-end={interval[1]}'

debug_flag = ""
if args.flags:
    debug_flag = "--debug-flags="
    debug_flag += ",".join(args.flags)
    

cmd_list = [f"nohup time build/X86_{design}/gem5.opt -d {path} " + \
f"{debug_flag} {debug_interval} configs/my_configs/se/ruby/simpleRuby/my_simple_ruby.py"
    ]

cmd_list[0] += f" --protocol {args.protocol}"
if args.path:
    cmd_list[0] += f" --path {args.path} --core {args.core}"
    
if args.arg:
    cmd_list[0] += f" --arg {args.arg}"

if args.ignore_proactive_eviction:
    cmd_list[0] += f" --ignore_proactive_eviction"
if args.search_in_bank:
    cmd_list[0] += f" --search_in_bank"
if args.xor_policy:
    cmd_list[0] += f" --xor_policy {args.xor_policy}"
    
if args.o3 == True:
    cmd_list[0] += f" --o3"

if not args.non_blocking:
    p = subprocess.Popen(cmd_list, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(f'Launched:  ')
    print(f'{p.args}')
    out,err = p.communicate()
    # ignore error
    out = out.decode('utf-8', errors='ignore')
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
    tick = int(out.split("Exiting @ tick ")[-1].split(" because")[0])
    print(f"tick={tick}")
else:
    # nonblocking
    print(f"nonblocking enabled")
    with open(f"{path}/err.txt","w") as err, open(f"{path}/out.txt","w") as out:
        p = subprocess.Popen(cmd_list, shell=True, stdout=out, stderr=err)
        print(f'Launched:  ')
        print(f'{p.args}')
