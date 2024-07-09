# Author: Zhewen
# Adapted from configs/learning_gem5/part3/msi_caches.py

import math

from m5.defines import buildEnv
from m5.util import fatal, panic

from m5.objects import *

from gem5.components.cachehierarchies.ruby.topologies.simple_pt2pt import SimplePt2Pt
from gem5.components.cachehierarchies.ruby.caches.mesi_two_level_bdixor.l1_cache_sendeviction import L1Cache_sendEviction
from gem5.components.cachehierarchies.ruby.caches.mesi_two_level_bdixor.l2_cache import L2Cache
from gem5.components.cachehierarchies.ruby.caches.mesi_two_level_bdixor.directory import Directory
from gem5.components.cachehierarchies.ruby.caches.mesi_two_level_bdixor.dma_controller import DMAController
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.components.processors.cpu_types import CPUTypes
from gem5.isas import ISA

class MyCacheSystem_xor(RubySystem):
    def __init__(self):
        if buildEnv["PROTOCOL"] != "MESI_Two_Level_BDI_XOR":
            fatal("This system assumes MESI_Two_Level_BDI_XOR!")

        super(MyCacheSystem_xor, self).__init__()

    def setup(self, system, cpus, mem_ctrls):
        """Set up the Ruby cache subsystem. Note: This can't be done in the
        constructor because many of these items require a pointer to the
        ruby system (self). This causes infinite recursion in initialize()
        if we do this in the __init__.
        """
        # Ruby's global network.
        self.network = SimplePt2Pt(self)

        # MSI uses 3 virtual networks. One for requests (lowest priority), one
        # for responses (highest priority), and one for "forwards" or
        # cache-to-cache requests. See *.sm files for details.
        self.number_of_virtual_networks = 5
        self.network.number_of_virtual_networks = 5

        ####
        
        _l1_controllers = []
        for i, cpu in enumerate(cpus):
            cache = L1Cache_sendEviction(
                l1i_size="8kB",#self._l1i_size,
                l1i_assoc=4, #self._l1i_assoc,
                l1d_size="8kB",#self._l1d_size,
                l1d_assoc=4, #self._l1d_assoc,
                network=self.network,
                core=cpu,
                num_l2Caches=len(cpus),
                cache_line_size=system.cache_line_size,
                target_isa=ISA.X86,
                clk_domain=self.clk_domain,
            )

            cache.ruby_system = self

            _l1_controllers.append(cache)
        
        _l2_controllers = [
            L2Cache(
                l2_size="16kB",
                l2_assoc=8,
                network=self.network,
                num_l2Caches=len(cpus),
                num_seg_per_blk=1,
                cache_line_size=64,
                data_lat=10,
                tag_lat=2,
                do_proative_eviction=True,
                search_in_set=True,
                xor_policy_id=3,
            )
            for _ in range(len(cpus))
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
        
        # Create one sequencer per CPU. In many systems this is more
        # complicated since you have to create sequencers for DMA controllers
        # and other controllers, too.
        self.sequencers = [
            RubySequencer(
                version=i,
                # I/D cache is combined and grab from ctrl
                dcache=self.controllers[i].L1Dcache,
                clk_domain=self.clk_domain,
            )
            for i in range(len(cpus))
        ]

        # We know that we put the controllers in an order such that the first
        # N of them are the L1 caches which need a sequencer pointer
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

        # Connect the cpu's cache, interrupt, and TLB ports to Ruby
        for i, cpu in enumerate(cpus):
            self.sequencers[i].connectCpuPorts(cpu)

