
# Author: Zhewen
# This file is adapted from configs/learning_gem5/part3/test_caches.py
# Reference: src/python/gem5/components/cachehierarchies/ruby/mesi_two_level_cache_hierarchy.py
# Use together with: configs/my_configs/se/ruby/my_ruby_rand_test.py

from m5.defines import buildEnv
from m5.util import fatal

from m5.objects import *

# from mymesi_caches import L1Cache, DirController

from gem5.components.cachehierarchies.ruby.topologies.simple_pt2pt import SimplePt2Pt
from gem5.components.cachehierarchies.ruby.caches.msi_three_level_exc.l1_cache import L1Cache
from gem5.components.cachehierarchies.ruby.caches.msi_three_level_exc.l2_cache import L2Cache
from gem5.components.cachehierarchies.ruby.caches.msi_three_level_exc.l3_cache import L3Cache
from gem5.components.cachehierarchies.ruby.caches.msi_three_level_exc.directory import Directory
from gem5.components.cachehierarchies.ruby.caches.msi_three_level_exc.dma_controller import DMAController
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.components.processors.cpu_types import CPUTypes
from gem5.isas import ISA
import math

class TestCacheSystem_msi_nine_exc3(RubySystem):
    def __init__(self):
        if buildEnv["PROTOCOL"] != "MSI_Three_Level_EXC":
            fatal("This system assumes MSI_Three_Level_EXC!")

        super(TestCacheSystem_msi_nine_exc3, self).__init__()
    def setup(self, system, tester, mem_ctrls):
        """Set up the Ruby cache subsystem. Note: This can't be done in the
        constructor because many of these items require a pointer to the
        ruby system (self). This causes infinite recursion in initialize()
        if we do this in the __init__.
        Setting up for running the RubyRandomTester is a little different
        than when we're using CPUs.
        """
        num_testers = tester.num_cpus
        numl3 = num_testers

        # Ruby's global network.
        self.network = SimplePt2Pt(self)

        # MSI uses 3 virtual networks
        self.number_of_virtual_networks = 6
        self.network.number_of_virtual_networks = 6

        ####
        dummy_cores = SimpleProcessor(cpu_type=CPUTypes.TIMING, 
            isa=ISA.X86, num_cores=1).get_cores() # for send eviction
        
        _l1_controllers = []
        _l2_controllers = []
        for i in range(num_testers):
            cache = L1Cache(
                l1i_size="1kB",#self._l1i_size, # as there wornt be ifetch
                l1i_assoc=4, #self._l1i_assoc,
                l1d_size="1kB",#self._l1d_size, #16blocks
                l1d_assoc=4, #self._l1d_assoc,
                network=self.network,
                core=dummy_cores[0],
                cache_line_size=system.cache_line_size,
                target_isa=ISA.X86,
                clk_domain=self.clk_domain,
                l1_data_lat=2,
                l1_tag_lat=2,
            )

            cache.ruby_system = self

            _l1_controllers.append(cache)

            l2_cache = L2Cache(
                    l2_size="4kB",
                    l2_assoc=8,
                    network=self.network,
                    num_l3Caches=numl3,
                    cache_line_size=system.cache_line_size,
                    clk_domain=self.clk_domain,
                    l2_data_lat=2,
                    l2_tag_lat=2,
            )

            l2_cache.ruby_system = self
            l2_cache.bufferFromL0 = cache.bufferToL1
            l2_cache.bufferToL0 = cache.bufferFromL1

            _l2_controllers.append(l2_cache)
            


        l3_data_size = 8 # in KB
        l3_sector_number = 64*l3_data_size

        _l3_controllers = [
            L3Cache(
                l3_tag_size="8kB",
                l3_tag_assoc=16,
                l3_data_size=f"{l3_sector_number}kB",
                dir_cache_size="8kB",
                dir_cache_assoc=8,
                total_size="16kB", # l3_tag_size + dir_cache_size
                network=self.network,
                num_l3Caches=numl3,
                cache_line_size=64,
                l3_data_lat=4,
                l3_tag_lat=2,
                dir_data_lat=1,
                dir_tag_lat=1,
                data_array_segment_size_in_byte=64,
                data_array_regions=1,
                transitions_per_cycle=1024,
                data_array_rp_policy="random",
            )
            for _ in range(numl3)
        ]

        for cache in _l3_controllers:
            cache.ruby_system = self
        _directory_controllers = [
            Directory(self.network, 64, system.mem_ranges[0], mem_ctrls[0].port)
            # for range, port in zip(system.mem_ranges, mem_ctrls[0].port)
        ]

        for dir in _directory_controllers:
            dir.ruby_system = self
        self.controllers = _l1_controllers + _l2_controllers + _l3_controllers + _directory_controllers

        self.sequencers = [
            RubySequencer(
                version=i,
                # I/D cache is combined and grab from ctrl
                dcache=self.controllers[i].Dcache,
                clk_domain=self.clk_domain,
            )
            for i in range(num_testers)
        ]
        for i, c in enumerate(self.controllers[0 : len(self.sequencers)]):
            c.sequencer = self.sequencers[i]
        ####

        self.num_of_sequencers = len(self.sequencers)

        # Create the network and connect the controllers.
        # NOTE: This is quite different if using Garnet!
        self.network.connectControllers(self.controllers)
        self.network.setup_buffers()

        # Set up a proxy port for the system_port. Used for load binaries and
        # other functional-only things.
        self.sys_port_proxy = RubyPortProxy()
        system.system_port = self.sys_port_proxy.in_ports

        # Connect up the sequencers to the random tester
        for seq in self.sequencers:
            if seq.support_data_reqs and seq.support_inst_reqs:
                tester.cpuInstDataPort = seq.in_ports
            elif seq.support_data_reqs:
                tester.cpuDataPort = seq.in_ports
            elif seq.support_inst_reqs:
                tester.cpuInstDataPort = seq.in_ports

            # Do not automatically retry stalled Ruby requests
            seq.no_retry_on_stall = True

            # Tell each sequencer this is the ruby tester so that it
            # copies the subblock back to the checker
            seq.using_ruby_tester = True
