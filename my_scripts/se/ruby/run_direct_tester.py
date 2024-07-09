# conpile:
#scons build/X86_MyMESI2/gem5.opt --default=X86 PROTOCOL=MESI_Two_Level_my SLICC_HTML=True -j24

import sys
import argparse, subprocess, os, re
from tqdm import tqdm
from scipy.stats import gmean
parser = argparse.ArgumentParser(description="config.")
parser.add_argument(
    "--requests", metavar="N", default=100, help="Stop after N requests"
)
parser.add_argument(
    "--test-type",
    default="SeriesGetx",
    choices=["SeriesGetx", "SeriesGets", "SeriesGetMixed", "Invalidate"],
    help="Type of test",
)
parser.add_argument(
    "--percent-writes",
    type=int,
    default=100,
    help="percentage of accesses that should be writes",
)
parser.add_argument(
    "--core",
    type=int,
    required=False,
    default=2,
    help="num cores",
)
parser.add_argument(
    "--protocol",
    type=str,
    help="which protocol to run",
    choices=["baseline", "noisy", "decoupled", "compress", "dedup", "bdixor",
             "msi", "msi_nine", "msi_exc",
             "msi_nine_xor_bdi_map", "msi_nine_noxor_bdi_map",
             "msi_nine_xor_nobdi_map", "msi_nine_noxor_nobdi_map",
             "msi_nine_noxor_thesaurus_map",
             ],
    required=True,
)
parser.add_argument(
    "--mute",
    action='store_true',
    help="do not print protocol traces",
)
parser.add_argument(
    "--non_blocking",
    action='store_true',
    help="do not block",
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
    "--other_flags",
    type=str,
    required=False,
    help="flag",
    nargs='+',
)
args = parser.parse_args()

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
elif args.protocol == "dedup":
    design = "MyMESI2_Dedup"
    design_out = design
elif args.protocol == "bdixor":
    design = "MyMESI2_BDI_XOR"
    design_out = design
elif args.protocol == "msi":
    design = "MyMSI"
    design_out = design
elif args.protocol == "msi_nine":
    design = "MyMSI_NINE"
    design_out = design
elif args.protocol == "msi_exc":
    design = "MyMSI_EXC"
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
elif args.protocol == "msi_nine_noxor_thesaurus_map":
    design = "MyMSI_NINE_XOR_MAP_THESAURUS"
    design_out = "MyMSI_NINE_NOXOR_THESAURUS_MAP"
else: assert False

if not os.path.isfile(f"build/X86_{design}/gem5.opt"): 
    print(f"gem5 binary file not exist!")
    exit(1)

path = f"m5out/m5out_directtester/{design_out}"
if args.core:
    path += f"/core{args.core}"
else:
    path += f"/core2"

if args.requests:
    path += f"/req{args.requests}"
else:
    path += f"/req100"

if args.test_type == "SeriesGetMixed":
    path += f"/{args.test_type}/{args.percent_writes}percent_writes"
else:
    path += f"/{args.test_type}"

isExist = os.path.exists(path)
if not isExist:
   os.makedirs(path)

debug_interval = ""
if args.begin and args.end:
    interval = (args.begin, args.end)
    debug_interval = f'--debug-start={interval[0]} --debug-end={interval[1]}'

debug_flag = "--debug-flags=ProtocolTrace"
if args.other_flags:
    debug_flag += ","
    debug_flag += ",".join(args.other_flags)
if args.mute:
    debug_flag = ""
    if args.other_flags:
        debug_flag += "--debug-flags="
        debug_flag += ",".join(args.other_flags)

cmd_list = [f"nohup time build/X86_{design}/gem5.opt -d {path} " + \
f"{debug_flag} {debug_interval} configs/my_configs/se/ruby/directTester/my_ruby_direct_test.py"
    ]

if args.requests:
    cmd_list[0] += f" --requests {args.requests}"
if args.core:
    cmd_list[0] += f" --core {args.core}"
if args.test_type:
    cmd_list[0] += f" --test-type {args.test_type}"
if args.percent_writes:
    cmd_list[0] += f" --percent-writes {args.percent_writes}"

cmd_list[0] += f" --protocol {args.protocol}"

if not args.non_blocking:
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
    tick = int(out.split("Exiting @ tick ")[-1].split(" because")[0])
    print(f"tick={tick}")
else:
    # nonblocking
    print(f"nonblocking enabled")
    with open(f"{path}/err.txt","w") as err, open(f"{path}/out.txt","w") as out:
        p = subprocess.Popen(cmd_list, shell=True, stdout=out, stderr=err)
        print(f'Launched:  ')
        print(f'{p.args}')
