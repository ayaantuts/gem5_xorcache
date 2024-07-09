# Author: Zhewen
# Adapted from configs/learning_gem5/part3/msi_caches.py

import math

from m5.defines import buildEnv
from m5.util import fatal, panic

from m5.objects import *

from gem5.components.cachehierarchies.ruby.topologies.simple_pt2pt import SimplePt2Pt
from gem5.components.cachehierarchies.ruby.caches.msi_two_level_nine_xor_map.l1_cache_sendeviction import L1Cache_sendEviction
from gem5.components.cachehierarchies.ruby.caches.msi_two_level_nine_xor_map.l2_cache import L2Cache
from gem5.components.cachehierarchies.ruby.caches.msi_two_level_nine_xor_map.directory import Directory
from gem5.components.cachehierarchies.ruby.caches.msi_two_level_nine_xor_map.dma_controller import DMAController
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.components.processors.cpu_types import CPUTypes
from gem5.isas import ISA

class MyCacheSystem_msi_nine_xor_map(RubySystem):
    def __init__(self,
                 l2_compression="no_compress",
                 half_data=False,
                 ):
        if buildEnv["PROTOCOL"] != "MSI_Two_Level_NINE_XOR_MAP":
            fatal("This system assumes MSI_Two_Level_NINE_XOR_MAP!")

        super(MyCacheSystem_msi_nine_xor_map, self).__init__()
        self._l2_compression = l2_compression
        self._half_data = half_data

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
                l1i_size="32kB",#self._l1i_size,
                l1i_assoc=4, #self._l1i_assoc,
                l1d_size="32kB",#self._l1d_size,
                l1d_assoc=4, #self._l1d_assoc,
                network=self.network,
                core=cpu,
                num_l2Caches=2,
                cache_line_size=system.cache_line_size,
                target_isa=ISA.X86,
                clk_domain=self.clk_domain,
            )

            cache.ruby_system = self

            _l1_controllers.append(cache)
        
        l2_data_size = 128 # in KB
        l2_sector_number = 64*l2_data_size

        if self._half_data:
            l2_sector_number = l2_sector_number // 2

        _l2_controllers = [
            L2Cache(
                l2_tag_size="128kB",
                l2_tag_assoc=8,
                l2_data_size=f"{l2_sector_number}kB",
                dir_cache_size="128kB",
                dir_cache_assoc=0,
                total_size="256kB", # l2_tag_size + dir_cache_size
                network=self.network,
                num_l2Caches=2,
                cache_line_size=64,
                l2_data_lat=4,
                l2_tag_lat=2,
                dir_data_lat=1,
                dir_tag_lat=1,
                # valid_candidate_ct_threshold=100000,
                valid_candidate_ct_threshold=0,
                map_bits=8,
                list_capacity=128,
                data_full_percentage=0,
                compression=self._l2_compression,
                data_array_rp_policy="random",
                record_line_level_entropy = True,
                data_array_segment_size_in_byte=8,
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

