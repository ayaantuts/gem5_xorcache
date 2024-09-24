# Author: 
# Use together with: configs/my_configs/se/ruby/direct_test/test_caches.py
# reference: configs/example/ruby_direct_test.py

# import the m5 (gem5) library created when gem5 is built
import m5

# import all of the SimObjects
from m5.objects import *
import sys



# create the system we are going to simulate
system = System()

# Set the clock frequency of the system (and all of its children)
system.clk_domain = SrcClockDomain()
system.clk_domain.clock = "1GHz"
system.clk_domain.voltage_domain = VoltageDomain()

# Set up the system
system.mem_mode = "timing"  # Use timing accesses
system.mem_ranges = [AddrRange("3GB")]  # Create an address range

import argparse
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
             "msi_nine_xor", "msi_nine_noxor", 

             "msi_nine_xor_bdi_map", "msi_nine_noxor_bdi_map",
             "msi_nine_xor_nobdi_map", "msi_nine_noxor_nobdi_map",

             "msi_nine_xor_bdi_map3", "msi_nine_noxor_bdi_map3",
             "msi_nine_xor_nobdi_map3", "msi_nine_noxor_nobdi_map3",

             "msi_nine_noxor_thesaurus_map",
             ],
    required=True,
)
args = parser.parse_args()

#
# Select the direct test generator
#
if args.test_type == "SeriesGetx":
    generator = SeriesRequestGenerator(
        num_cpus=args.core, percent_writes=100
    )
elif args.test_type == "SeriesGets":
    generator = SeriesRequestGenerator(
        num_cpus=args.core, percent_writes=0
    )
elif args.test_type == "SeriesGetMixed":
    generator = SeriesRequestGenerator(
        num_cpus=args.core, percent_writes=args.percent_writes
    )
elif args.test_type == "Invalidate":
    generator = InvalidateGenerator(num_cpus=args.core)
else:
    print("Error: unknown direct test generator")
    sys.exit(1)
# Create the tester
system.tester = RubyDirectedTester(
    requests_to_complete=args.requests, generator=generator
)

# Create a simple memory controller and connect it to the membus
system.mem_ctrl = SimpleMemory(latency="50ns", bandwidth="0GB/s")
system.mem_ctrl.range = system.mem_ranges[0]

# Create the Ruby System
if args.protocol == "baseline":
    from test_caches import TestCacheSystem as TestCacheSystem_baseline
    system.caches = TestCacheSystem_baseline()
elif args.protocol == "noisy":
    from test_caches_my import TestCacheSystem_my as TestCacheSystem_my
    system.caches = TestCacheSystem_my()
elif args.protocol == "decoupled":
    from test_caches_decoupled import TestCacheSystem_decoupled as TestCacheSystem_decoupled
    system.caches = TestCacheSystem_decoupled()
elif args.protocol == "compress":
    from test_caches_compress import TestCacheSystem_compress as TestCacheSystem_compress
    system.caches = TestCacheSystem_compress()
elif args.protocol == "dedup":
    from test_caches_dedup import TestCacheSystem_dedup as TestCacheSystem_dedup
    system.caches = TestCacheSystem_dedup()
elif args.protocol == "bdixor":
    from test_caches_bdixor import TestCacheSystem_bdixor as TestCacheSystem_bdixor
    system.caches = TestCacheSystem_bdixor()
elif args.protocol == "msi":
    from test_caches_msi import TestCacheSystem_msi as TestCacheSystem_msi
    system.caches = TestCacheSystem_msi()
elif args.protocol == "msi_nine":
    from test_caches_msi_nine import TestCacheSystem_msi_nine as TestCacheSystem_msi_nine
    system.caches = TestCacheSystem_msi_nine()
elif args.protocol == "msi_exc":
    from test_caches_msi_exc import TestCacheSystem_msi_exc as TestCacheSystem_msi_exc
    system.caches = TestCacheSystem_msi_exc()
elif args.protocol == "msi_nine_xor":
    from test_caches_msi_nine_xor import TestCacheSystem_msi_nine_xor as TestCacheSystem_msi_nine_xor
    system.caches = TestCacheSystem_msi_nine_xor()

elif args.protocol == "msi_nine_noxor_nobdi_map":
    from test_caches_msi_nine_xor_map import TestCacheSystem_msi_nine_xor_map as TestCacheSystem_msi_nine_xor_map
    system.caches = TestCacheSystem_msi_nine_xor_map(
        half_data=False,
        valid_candidate_ct_threshold=10000000,
    )
elif args.protocol == "msi_nine_xor_bdi_map":
    from test_caches_msi_nine_xor_map import TestCacheSystem_msi_nine_xor_map as TestCacheSystem_msi_nine_xor_map
    system.caches = TestCacheSystem_msi_nine_xor_map(
        l2_compression="bdi",
        half_data=True,
        valid_candidate_ct_threshold=0,
    )
elif args.protocol == "msi_nine_noxor_bdi_map":
    from test_caches_msi_nine_xor_map import TestCacheSystem_msi_nine_xor_map as TestCacheSystem_msi_nine_xor_map
    system.caches = TestCacheSystem_msi_nine_xor_map(
        l2_compression="bdi",
        half_data=True,
        valid_candidate_ct_threshold=10000000,
    )
elif args.protocol == "msi_nine_xor_nobdi_map":
    from test_caches_msi_nine_xor_map import TestCacheSystem_msi_nine_xor_map as TestCacheSystem_msi_nine_xor_map
    system.caches = TestCacheSystem_msi_nine_xor_map(
        half_data=False,
        valid_candidate_ct_threshold=0,
    )

elif args.protocol == "msi_nine_noxor_nobdi_map3":
    from test_caches_msi_nine_3_xor_map import TestCacheSystem_msi_nine_3_xor_map as TestCacheSystem_msi_nine_xor_map
    system.caches = TestCacheSystem_msi_nine_xor_map(
        half_data=False,
        valid_candidate_ct_threshold=10000000,
    )
elif args.protocol == "msi_nine_xor_bdi_map3":
    from test_caches_msi_nine_3_xor_map import TestCacheSystem_msi_nine_3_xor_map as TestCacheSystem_msi_nine_xor_map
    system.caches = TestCacheSystem_msi_nine_xor_map(
        l3_compression="bdi",
        half_data=True,
        valid_candidate_ct_threshold=0,
    )
elif args.protocol == "msi_nine_noxor_bdi_map3":
    from test_caches_msi_nine_3_xor_map import TestCacheSystem_msi_nine_3_xor_map as TestCacheSystem_msi_nine_xor_map
    system.caches = TestCacheSystem_msi_nine_xor_map(
        l3_compression="bdi",
        half_data=True,
        valid_candidate_ct_threshold=10000000,
    )
elif args.protocol == "msi_nine_xor_nobdi_map3":
    from test_caches_msi_nine_3_xor_map import TestCacheSystem_msi_nine_3_xor_map as TestCacheSystem_msi_nine_xor_map
    system.caches = TestCacheSystem_msi_nine_xor_map(
        half_data=False,
        valid_candidate_ct_threshold=0,
    )

elif args.protocol == "msi_nine_noxor_thesaurus_map":
    from test_caches_msi_nine_xor_map_thesaurus import TestCacheSystem_msi_nine_xor_map_thesaurus as TestCacheSystem_msi_nine_xor_map_thesaurus
    system.caches = TestCacheSystem_msi_nine_xor_map_thesaurus(
        l2_compression="thesaurus",
        half_data=True,
        valid_candidate_ct_threshold=10000000,
    )
else:
    print("Error: unknown protocol")
    sys.exit(1)
system.caches.setup(system, system.tester, [system.mem_ctrl])

# set up the root SimObject and start the simulation
root = Root(full_system=False, system=system)
root.system.mem_mode = "timing"

# Not much point in this being higher than the L1 latency
m5.ticks.setGlobalFrequency("1ns")

# instantiate all of the objects we've created above
m5.instantiate()

print("Beginning simulation!")
exit_event = m5.simulate()
print(
    "Exiting @ tick {} because {}".format(m5.curTick(), exit_event.getCause())
)
