import subprocess, os, time
import sys
from pathlib import Path

sys.path.append("/home/zhewen/repo/gem5-dev/gem5/util/")
from spec2017_util import bcolors, create_folder, yaml_load, yaml_overwrite
import argparse
import copy


def rank_simpoint_weight(
    weight_file, simpoint_file, take, currently_avail=None
):
    """
    param take: number of simpoint to take (i.e. min number across all bench)
    param currently_avail: if set, only rank currently available simpoints
    return simpoint_index_arr: index of simpoint to take, ranked by weight
    return acc_weight: accumulated weight
    """
    simpoint_index_arr = []

    file1 = open(weight_file, "r")
    Lines = file1.readlines()
    num_weight = []
    for line in Lines:
        line = line.strip()
        num = int(line.split(" ")[-1])
        weight = float(line.split(" ")[0])
        tuple_ = (num, weight)
        num_weight.append(tuple_)
    # num_weight.sort(key=lambda y: y[1], reverse=True)

    file2 = open(simpoint_file, "r")
    Lines = file2.readlines()
    num_ins = []
    for line in Lines:
        line = line.strip()
        num = int(line.split(" ")[-1])
        ins = int(line.split(" ")[0])
        tuple_ = (num, ins)
        num_ins.append(tuple_)
    # num_ins.sort(key=lambda y: y[1])

    ins_weight = []
    for (nw, ni) in zip(num_weight, num_ins):
        iw = (ni[1], nw[1])
        ins_weight.append(iw)
    ins_weight.sort(key=lambda y: y[0])
    ins_weight_orig_order = copy.deepcopy(ins_weight)
    # print(ins_weight)
    if currently_avail:
        ins_weight = ins_weight[0:currently_avail]
    # print(ins_weight)
    ins_weight.sort(key=lambda y: y[1], reverse=True)
    ins_weight = ins_weight[0:take]
    # print(ins_weight)
    simpoint_index_arr = [
        [i for i, v in enumerate(ins_weight_orig_order) if v[0] == tuple_[0]][
            0
        ]
        for tuple_ in ins_weight
    ]
    # print(simpoint_index_arr)
    weight_selected = [ins_weight_orig_order[i][1] for i in simpoint_index_arr]
    acc_weight = sum(weight_selected)

    return simpoint_index_arr, acc_weight


parser = argparse.ArgumentParser(description="agg config.")

parser.add_argument(
    "--bench_nums",
    type=int,
    nargs="+",
    required=False,
    default=[502, 557, 527, 520],
    help="list of bench mark number to aggregate",
)
args = parser.parse_args()

# parse spec2017
yml_file = "util/spec2017_default.yml"
spec2017 = yaml_load(yml_file)
simpoint_num_arr = []
name_arr = []
# specify simpoint, weight files
simpoint_dir = f"/home/zhewen/repo/Simpoint.3.2/output/spec2017"
print_string = ""
# first round: parse number of simpoints
for i in args.bench_nums:
    bench_name = spec2017[i]["name"]
    fused_name = f"{i}.{bench_name}"
    name_arr.append(fused_name)
    ckpt_dir = Path(f"ckpt/spec2017/1c-2GB-valgrind/{fused_name}/")
    ckpts = sorted(ckpt_dir.glob("cpt.*"))
    num = sum(1 for dir in ckpts)
    simpoint_num_arr.append(num)

str_ = bcolors.PURPLE + "round1: parse number of simpoints" + bcolors.ENDC
print(str_)
print_string += str_

str_ = bcolors.SKY + "selected benchmarks: " + bcolors.ENDC + f"{name_arr}"
print(str_)
print_string += str_

str_ = bcolors.SKY + "num simpoint: " + bcolors.ENDC + f"{simpoint_num_arr}"
print(str_)
print_string += str_

num_agg_ckpt = min(simpoint_num_arr)

# second round: rank simpoints
str_ = bcolors.PURPLE + "round2: rank simpoints" + bcolors.ENDC
print(str_)
print_string += str_
for i in args.bench_nums:
    bench_name = spec2017[i]["name"]
    fused_name = f"{i}.{bench_name}"
    weight_file = Path(f"{simpoint_dir}/{i}_{bench_name}_weight.txt")
    simpoint_file = Path(f"{simpoint_dir}/{i}_{bench_name}_simpoint.txt")

    ckpt_dir = Path(f"ckpt/spec2017/1c-2GB-valgrind/{fused_name}/")
    ckpts = sorted(ckpt_dir.glob("cpt.*"))

    str_ = f"{fused_name}: currently available simpoints = {len(ckpts)}"
    print(str_)
    print_string += str_

    simpoint_index_arr, acc_weight = rank_simpoint_weight(
        weight_file, simpoint_file, num_agg_ckpt, len(ckpts)
    )

    str_ = (
        bcolors.SKY
        + "index="
        + bcolors.ENDC
        + simpoint_index_arr
        + bcolors.SKY
        + "acc weight="
        + bcolors.ENDC
        + acc_weight,
    )
    print(str_)
    print_string += str_
    print()

    dir_list = []
    for ind in simpoint_index_arr:
        dir_list.append(str(ckpts[ind]))
    spec2017[i]["ckpt_dirs"] = dir_list

bench_nums_str = [str(i) for i in args.bench_nums]
bench_nums_str = "_".join(bench_nums_str)
# run_file = f'spec2017_{all_bench}.yml'
# yaml_overwrite(f'./{run_file}', spec2017)
byte_2G = (
    2 * 1024 * 1024 * 1024
)  # by default, the ckpts are generated using 2GB memory
mem_size = len(args.bench_nums) * byte_2G
name_out = f"c{len(args.bench_nums)}_{bench_nums_str}"

os.makedirs("log", exist_ok=True)

for j in range(num_agg_ckpt):
    out_dir = f"agg/{name_out}/set{j}"
    os.makedirs(out_dir, exist_ok=True)
    cmd_list = [
        "python3",
        "util/checkpoint_aggregator.py",
        f"--memory-size={mem_size}",
        f"--root-name=board",
        f"--cpu-name=processor",
        f"--output-dir={out_dir}",
        "--cpts",
    ]
    cmd_list += [spec2017[i]["ckpt_dirs"][j] for i in args.bench_nums]
    cmd_list += ["--rel"]
    cmd_list += [spec2017[i]["cwd"] for i in args.bench_nums]
    cmd_list = " ".join(cmd_list)

    print(cmd_list)

    with open(f"log/agg_{name_out}_set{j}.log", "wb") as out, open(
        f"log/agg_{name_out}_set{j}.err", "wb"
    ) as err:
        p = subprocess.Popen(cmd_list, shell=True, stdout=out, stderr=err)
        print(bcolors.OKGREEN + f"Launched:  " + bcolors.ENDC + name_out)
        print(f"{p.args}")
    exit()

f = open(f"log/agg_{name_out}.log", "w")
f.write(print_string)
f.close()
