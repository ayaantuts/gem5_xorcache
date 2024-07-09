# Author: Zhewen
# Adapted from configs/learning_gem5/part3/simple_ruby.py

# import the m5 (gem5) library created when gem5 is built
import m5

# import all of the SimObjects
from m5.objects import *

# Needed for running C++ threads
m5.util.addToPath("../../../../")
from common.FileSystemConfig import config_filesystem

import argparse
parser = argparse.ArgumentParser(description="config.")
parser.add_argument(
    "--protocol",
    type=str,
    help="which protocol to run",
    choices=["baseline", "noisy", "decoupled", "compress","bdixor", "xor",
             "msi","msi_nine", "msi_nine_xor", "msi_nine_noxor",
             "msi_nine_xor_bdi_map", "msi_nine_noxor_bdi_map",
             "msi_nine_xor_nobdi_map", "msi_nine_noxor_nobdi_map",],
    required=True,
)
parser.add_argument(
    "--search_in_bank",
    action='store_true',
    required=False,
    help="search xor candidates in a bank",
)
parser.add_argument(
    "--ignore_proactive_eviction",
    action='store_true',
    required=False,
    help="ignore proactive evictions",
)
parser.add_argument(
    "--path",
    type=str,
    help="path to binary",
)
parser.add_argument(
    "--arg",
    type=str,
    help="extra args",
)
parser.add_argument(
    "--core",
    type=int,
    required=False,
    help="number of cores. Note if pthread_create, num core = thread+1",
)
parser.add_argument(
    "--xor_policy",
    type=int,
    required=False,
    default=1,
    help="xor policy id, default=1",
)
parser.add_argument(
    "--o3",
    action='store_true',
    required=False,
    help="use o3 cpu",
)
args = parser.parse_args()

if args.path:
    assert(args.core)

# create the system we are going to simulate
system = System()

# Set the clock frequency of the system (and all of its children)
system.clk_domain = SrcClockDomain()
system.clk_domain.clock = "1GHz"
system.clk_domain.voltage_domain = VoltageDomain()

# Set up the system
system.mem_mode = "timing"  # Use timing accesses
system.mem_ranges = [AddrRange("512MB")]  # Create an address range

# Create a pair of simple CPUs
if args.path:
    if args.o3:
        system.cpu = [X86O3CPU() for i in range(args.core)]
    else:
        system.cpu = [X86TimingSimpleCPU() for i in range(args.core)]
else:
    if args.o3:
        system.cpu = [X86O3CPU() for i in range(2)]
    else:
        system.cpu = [X86TimingSimpleCPU() for i in range(2)]
# system.cpu = SimpleProcessor(cpu_type=CPUTypes.TIMING, 
#             isa=ISA.X86, num_cores=1).get_cores() # for send eviction

# Create a DDR3 memory controller and connect it to the membus
system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]

# create the interrupt controller for the CPU and connect to the membus
for cpu in system.cpu:
    cpu.createInterruptController()

# set me
include_proactive_eviction = True
if args.ignore_proactive_eviction == True:
    include_proactive_eviction = False
search_in_set = True
if args.search_in_bank == True:
    search_in_set = False

# Create the Ruby System
if args.protocol == "baseline":
    from mesi_caches import MyCacheSystem
    system.caches = MyCacheSystem()
elif args.protocol == "noisy":
    from my_mesi_caches import MyCacheSystem_my
    system.caches = MyCacheSystem_my()
elif args.protocol == "decoupled":
    from my_mesi_caches_decoupled import MyCacheSystem_decoupled
    system.caches = MyCacheSystem_decoupled()
elif args.protocol == "compress":
    from my_mesi_caches_compress import MyCacheSystem_compress
    system.caches = MyCacheSystem_compress()
elif args.protocol == "bdixor":
    if args.xor_policy == 1:
        if include_proactive_eviction and search_in_set: from my_mesi_caches_bdi_xor import MyCacheSystem_bdixor
        elif include_proactive_eviction and not search_in_set: from my_mesi_caches_bdi_xor_searchBank import MyCacheSystem_bdixor
        elif not include_proactive_eviction and search_in_set: from my_mesi_caches_bdi_xor_no_proactive_eviction import MyCacheSystem_bdixor
        elif not include_proactive_eviction and not search_in_set: from my_mesi_caches_bdi_xor_searchBank_no_proactive_eviction import MyCacheSystem_bdixor
        else: assert False
    elif args.xor_policy == 2:
        if include_proactive_eviction and search_in_set: from my_mesi_caches_bdi_xor_nongreedy import MyCacheSystem_bdixor
        elif include_proactive_eviction and not search_in_set: from my_mesi_caches_bdi_xor_searchBank_nongreedy import MyCacheSystem_bdixor
        elif not include_proactive_eviction and search_in_set: from my_mesi_caches_bdi_xor_no_proactive_eviction_nongreedy import MyCacheSystem_bdixor
        elif not include_proactive_eviction and not search_in_set: from my_mesi_caches_bdi_xor_searchBank_no_proactive_eviction_nongreedy import MyCacheSystem_bdixor
        else: assert False
    elif args.xor_policy == 3:
        if include_proactive_eviction and search_in_set: from my_mesi_caches_bdi_xor_mru import MyCacheSystem_bdixor
        elif include_proactive_eviction and not search_in_set: from my_mesi_caches_bdi_xor_searchBank_mru import MyCacheSystem_bdixor
        elif not include_proactive_eviction and search_in_set: from my_mesi_caches_bdi_xor_no_proactive_eviction_mru import MyCacheSystem_bdixor
        elif not include_proactive_eviction and not search_in_set: from my_mesi_caches_bdi_xor_searchBank_no_proactive_eviction_mru import MyCacheSystem_bdixor
        else: assert False
    elif args.xor_policy == 4:
        if include_proactive_eviction and search_in_set: from my_mesi_caches_bdi_xor_nongreedy_mru import MyCacheSystem_bdixor
        elif include_proactive_eviction and not search_in_set: from my_mesi_caches_bdi_xor_searchBank_nongreedy_mru import MyCacheSystem_bdixor
        elif not include_proactive_eviction and search_in_set: from my_mesi_caches_bdi_xor_no_proactive_eviction_nongreedy_mru import MyCacheSystem_bdixor
        elif not include_proactive_eviction and not search_in_set: from my_mesi_caches_bdi_xor_searchBank_no_proactive_eviction_nongreedy_mru import MyCacheSystem_bdixor
        else: assert False
    elif args.xor_policy == 5:
        if include_proactive_eviction and search_in_set: from my_mesi_caches_bdi_xor_lru import MyCacheSystem_bdixor
        elif include_proactive_eviction and not search_in_set: from my_mesi_caches_bdi_xor_searchBank_lru import MyCacheSystem_bdixor
        elif not include_proactive_eviction and search_in_set: from my_mesi_caches_bdi_xor_no_proactive_eviction_lru import MyCacheSystem_bdixor
        elif not include_proactive_eviction and not search_in_set: from my_mesi_caches_bdi_xor_searchBank_no_proactive_eviction_lru import MyCacheSystem_bdixor
        else: assert False
    elif args.xor_policy == 6:
        if include_proactive_eviction and search_in_set: from my_mesi_caches_bdi_xor_nongreedy_lru import MyCacheSystem_bdixor
        elif include_proactive_eviction and not search_in_set: from my_mesi_caches_bdi_xor_searchBank_nongreedy_lru import MyCacheSystem_bdixor
        elif not include_proactive_eviction and search_in_set: from my_mesi_caches_bdi_xor_no_proactive_eviction_nongreedy_lru import MyCacheSystem_bdixor
        elif not include_proactive_eviction and not search_in_set: from my_mesi_caches_bdi_xor_searchBank_no_proactive_eviction_nongreedy_lru import MyCacheSystem_bdixor
        else: assert False
    else: assert False

    system.caches = MyCacheSystem_bdixor()
elif args.protocol == "xor":
    if args.xor_policy == 1:
        if include_proactive_eviction and search_in_set: from my_mesi_caches_xor import MyCacheSystem_xor
        elif include_proactive_eviction and not search_in_set: from my_mesi_caches_xor_searchBank import MyCacheSystem_xor
        elif not include_proactive_eviction and search_in_set: from my_mesi_caches_xor_no_proactive_eviction import MyCacheSystem_xor
        elif not include_proactive_eviction and not search_in_set: from my_mesi_caches_xor_searchBank_no_proactive_eviction import MyCacheSystem_xor
        else: assert False
    elif args.xor_policy == 2:
        if include_proactive_eviction and search_in_set: from my_mesi_caches_xor_nongreedy import MyCacheSystem_xor
        elif include_proactive_eviction and not search_in_set: from my_mesi_caches_xor_searchBank_nongreedy import MyCacheSystem_xor
        elif not include_proactive_eviction and search_in_set: from my_mesi_caches_xor_no_proactive_eviction_nongreedy import MyCacheSystem_xor
        elif not include_proactive_eviction and not search_in_set: from my_mesi_caches_xor_searchBank_no_proactive_eviction_nongreedy import MyCacheSystem_xor
        else: assert False
    elif args.xor_policy == 3:
        if include_proactive_eviction and search_in_set: from my_mesi_caches_xor_mru import MyCacheSystem_xor
        elif include_proactive_eviction and not search_in_set: from my_mesi_caches_xor_searchBank_mru import MyCacheSystem_xor
        elif not include_proactive_eviction and search_in_set: from my_mesi_caches_xor_no_proactive_eviction_mru import MyCacheSystem_xor
        elif not include_proactive_eviction and not search_in_set: from my_mesi_caches_xor_searchBank_no_proactive_eviction_mru import MyCacheSystem_xor
        else: assert False
    elif args.xor_policy == 4:
        if include_proactive_eviction and search_in_set: from my_mesi_caches_xor_nongreedy_mru import MyCacheSystem_xor
        elif include_proactive_eviction and not search_in_set: from my_mesi_caches_xor_searchBank_nongreedy_mru import MyCacheSystem_xor
        elif not include_proactive_eviction and search_in_set: from my_mesi_caches_xor_no_proactive_eviction_nongreedy_mru import MyCacheSystem_xor
        elif not include_proactive_eviction and not search_in_set: from my_mesi_caches_xor_searchBank_no_proactive_eviction_nongreedy_mru import MyCacheSystem_xor
        else: assert False
    elif args.xor_policy == 5:
        if include_proactive_eviction and search_in_set: from my_mesi_caches_xor_lru import MyCacheSystem_xor
        elif include_proactive_eviction and not search_in_set: from my_mesi_caches_xor_searchBank_lru import MyCacheSystem_xor
        elif not include_proactive_eviction and search_in_set: from my_mesi_caches_xor_no_proactive_eviction_lru import MyCacheSystem_xor
        elif not include_proactive_eviction and not search_in_set: from my_mesi_caches_xor_searchBank_no_proactive_eviction_lru import MyCacheSystem_xor
        else: assert False
    elif args.xor_policy == 6:
        if include_proactive_eviction and search_in_set: from my_mesi_caches_xor_nongreedy_lru import MyCacheSystem_xor
        elif include_proactive_eviction and not search_in_set: from my_mesi_caches_xor_searchBank_nongreedy_lru import MyCacheSystem_xor
        elif not include_proactive_eviction and search_in_set: from my_mesi_caches_xor_no_proactive_eviction_nongreedy_lru import MyCacheSystem_xor
        elif not include_proactive_eviction and not search_in_set: from my_mesi_caches_xor_searchBank_no_proactive_eviction_nongreedy_lru import MyCacheSystem_xor
        else: assert False
    else: assert False

    system.caches = MyCacheSystem_xor()
elif args.protocol == "msi":
    from msi_caches import MyCacheSystem_msi
    system.caches = MyCacheSystem_msi()
elif args.protocol == "msi_nine":
    from msi_caches_nine import MyCacheSystem_msi_nine
    system.caches = MyCacheSystem_msi_nine()  
elif args.protocol == "msi_nine_xor":
    from msi_caches_nine_xor import MyCacheSystem_msi_nine_xor
    system.caches = MyCacheSystem_msi_nine_xor()  
elif args.protocol == "msi_nine_noxor":
    from msi_caches_nine_noxor import MyCacheSystem_msi_nine_noxor
    system.caches = MyCacheSystem_msi_nine_noxor()  
elif args.protocol == "msi_nine_xor_nobdi_map":
    from msi_caches_nine_xor_map import MyCacheSystem_msi_nine_xor_map as MyCacheSystem_msi_nine_xor_map
    system.caches = MyCacheSystem_msi_nine_xor_map(
        half_data=True,
    )
elif args.protocol == "msi_nine_xor_bdi_map":
    from msi_caches_nine_xor_map import MyCacheSystem_msi_nine_xor_map as MyCacheSystem_msi_nine_xor_map
    system.caches = MyCacheSystem_msi_nine_xor_map(
        l2_compression="bdi",
        half_data=True,
    )
elif args.protocol == "msi_nine_noxor_nobdi_map":
    from msi_caches_nine_noxor_map import MyCacheSystem_msi_nine_noxor_map as MyCacheSystem_msi_nine_noxor_map
    system.caches = MyCacheSystem_msi_nine_noxor_map()
elif args.protocol == "msi_nine_noxor_bdi_map":
    from msi_caches_nine_noxor_map import MyCacheSystem_msi_nine_noxor_map as MyCacheSystem_msi_nine_noxor_map
    system.caches = MyCacheSystem_msi_nine_noxor_map(
        l2_compression="bdi",
        half_data=True,
    )

system.caches.setup(system, system.cpu, [system.mem_ctrl])

# Run application and use the compiled ISA to find the binary
# grab the specific path to the binary
thispath = os.path.dirname(os.path.realpath(__file__))
binary = os.path.join(
    thispath,
    "../../../../../",
    "tests/test-progs/threads/bin/x86/linux/threads",
)

if args.path:
    binary = os.path.abspath(args.path)

# Create a process for a simple "multi-threaded" application
process = Process()
# Set the command
# cmd is a list which begins with the executable (like argv)
process.cmd = [binary]
if args.arg:
    process.cmd = [binary,args.arg]

# Set the cpu to use the process as its workload and create thread contexts
for cpu in system.cpu:
    cpu.workload = process
    cpu.createThreads()

system.workload = SEWorkload.init_compatible(binary)

# Set up the pseudo file system for the threads function above
config_filesystem(system)

# set up the root SimObject and start the simulation
root = Root(full_system=False, system=system)
# instantiate all of the objects we've created above
m5.instantiate()

print("Beginning simulation!")
exit_event = m5.simulate()
print(
    "Exiting @ tick {} because {}".format(m5.curTick(), exit_event.getCause())
)
