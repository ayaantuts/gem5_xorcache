
# Author: Zhewen
# This file is adapted from configs/learning_gem5/part3/test_caches.py
# Reference: src/python/gem5/components/cachehierarchies/ruby/mesi_two_level_cache_hierarchy.py
# Use together with: configs/my_configs/se/ruby/my_ruby_rand_test.py

from m5.defines import buildEnv
from m5.util import fatal

from m5.objects import *

# from mymesi_caches import L1Cache, DirController

from gem5.components.cachehierarchies.ruby.topologies.simple_pt2pt import SimplePt2Pt
from gem5.components.cachehierarchies.ruby.caches.mesi_two_level_dedup.l1_cache import L1Cache
from gem5.components.cachehierarchies.ruby.caches.mesi_two_level_dedup.l2_cache import L2Cache
from gem5.components.cachehierarchies.ruby.caches.mesi_two_level_dedup.directory import Directory
from gem5.components.cachehierarchies.ruby.caches.mesi_two_level_dedup.dma_controller import DMAController
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.components.processors.cpu_types import CPUTypes
from gem5.isas import ISA
import math

class TestCacheSystem_dedup(RubySystem):
    def __init__(self):
        if buildEnv["PROTOCOL"] != "MESI_Two_Level_Dedup":
            fatal("This system assumes mesi2dedup!")

        super(TestCacheSystem_dedup, self).__init__()

    def setup(self, system, tester, mem_ctrls):
        """Set up the Ruby cache subsystem. Note: This can't be done in the
        constructor because many of these items require a pointer to the
        ruby system (self). This causes infinite recursion in initialize()
        if we do this in the __init__.
        Setting up for running the RubyRandomTester is a little different
        than when we're using CPUs.
        """
        num_testers = tester.num_cpus

        # Ruby's global network.
        self.network = SimplePt2Pt(self)

        # MSI uses 3 virtual networks
        self.number_of_virtual_networks = 5
        self.network.number_of_virtual_networks = 5

        ####
        dummy_cores = SimpleProcessor(cpu_type=CPUTypes.TIMING, 
            isa=ISA.X86, num_cores=1).get_cores() # for send eviction
        
        _l1_controllers = []
        for i in range(num_testers):
            cache = L1Cache(
                l1i_size="16kB",#self._l1i_size,
                l1i_assoc=8, #self._l1i_assoc,
                l1d_size="16kB",#self._l1d_size,
                l1d_assoc=8, #self._l1d_assoc,
                network=self.network,
                core=dummy_cores[0],
                num_l2Caches=2,
                cache_line_size=system.cache_line_size,
                target_isa=ISA.X86,
                clk_domain=self.clk_domain,
            )

            cache.ruby_system = self

            _l1_controllers.append(cache)
        
        _l2_controllers = [
            L2Cache(
                l2_size="128kB",
                l2_assoc=16, # assoc
                network=self.network,
                num_l2Caches=2, # banks
                num_seg_per_blk=8, # 1 segs per blk
                cache_line_size=64, # block size
                data_lat=7, # data lat
                tag_lat=2, # tag lat
                l2_dataArraySet=1024,
            )
            for _ in range(2)
        ]

        for cache in _l2_controllers:
            cache.ruby_system = self
        _directory_controllers = [
            Directory(self.network, 64, system.mem_ranges[0], mem_ctrls[0].port)
            # for range, port in zip(system.mem_ranges, mem_ctrls[0].port)
        ]

        for dir in _directory_controllers:
            dir.ruby_system = self
        self.controllers = _l1_controllers + _l2_controllers + _directory_controllers
        
        self.sequencers = [
            RubySequencer(
                version=i,
                # I/D cache is combined and grab from ctrl
                dcache=self.controllers[i].L1Dcache,
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
