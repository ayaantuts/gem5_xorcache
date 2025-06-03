# Copyright (c) 2021 The Regents of the University of California
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


from .abstract_ruby_cache_hierarchy import AbstractRubyCacheHierarchy
from ..abstract_three_level_cache_hierarchy import AbstractThreeLevelCacheHierarchy
from ....coherence_protocol import CoherenceProtocol
from ....isas import ISA
from ...boards.abstract_board import AbstractBoard
from ....utils.requires import requires

from .topologies.simple_pt2pt import SimplePt2Pt
from .caches.msi_three_level_exc.l1_cache import L1Cache
from .caches.msi_three_level_exc.l2_cache import L2Cache
from .caches.msi_three_level_exc.l3_cache import L3Cache
from .caches.msi_three_level_exc.directory import Directory
from .caches.msi_three_level_exc.dma_controller import DMAController

from m5.objects import RubySystem, RubySequencer, DMASequencer, RubyPortProxy


class MSIThreeLevelExcCacheHierarchy(
    AbstractRubyCacheHierarchy, AbstractThreeLevelCacheHierarchy
):
    """A three-level private-L1-private-L2-shared-L3 MSI hierarchy.

    In addition to the normal three level parameters, you can also change the
    number of L3 banks in this protocol.

    The on-chip network is a point-to-point all-to-all simple network.
    """

    def __init__(
        self,
        l1i_size: str,
        l1i_assoc: str,
        l1d_size: str,
        l1d_assoc: str,

        l2_size: str,
        l2_assoc: str,

        l3_tag_size: str,
        l3_tag_assoc: str,
        l3_data_size: str,
        dir_cache_size: str,
        dir_cache_assoc: str,
        dir_l3_total_size: str,
        num_l3_banks: int,
        l3_data_lat: int,
        l3_tag_lat: int,
        dir_data_lat: int,
        dir_tag_lat: int,
        l3_transitions_per_cycle:str,
        l3_data_array_segment_size_in_byte,
        l3_data_array_regions,
        l3_data_array_rp_policy: str="random",
        l3_compression: str="no_compress",
        index_bits_shift: int=0,
    ):
        AbstractRubyCacheHierarchy.__init__(self=self)
        AbstractThreeLevelCacheHierarchy.__init__(
            self,
            l1i_size=l1i_size,
            l1i_assoc=l1i_assoc,
            l1d_size=l1d_size,
            l1d_assoc=l1d_assoc,
            l2_size=l2_size,
            l2_assoc=l2_assoc,
            l3_size=l3_tag_size,
            l3_assoc=l3_tag_assoc,
        )

        self._num_l2_banks = num_l3_banks
        self._l3_data_size = l3_data_size
        self._l3_data_lat = l3_data_lat
        self._l3_tag_lat = l3_tag_lat
        self._dir_data_lat = dir_data_lat
        self._dir_tag_lat = dir_tag_lat
        self._dir_cache_size = dir_cache_size
        self._dir_cache_assoc = dir_cache_assoc
        self._dir_l3_total_size = dir_l3_total_size
        self._l3_compression = l3_compression
        self._l3_data_array_rp_policy = l3_data_array_rp_policy
        self._l3_data_array_segment_size_in_byte = l3_data_array_segment_size_in_byte
        self._l3_data_array_regions = l3_data_array_regions
        self._l3_transitions_per_cycle = l3_transitions_per_cycle

        self._index_bits_shift = index_bits_shift

    def incorporate_cache(self, board: AbstractBoard) -> None:

        requires(coherence_protocol_required=CoherenceProtocol.MSI_THREE_LEVEL_EXC)

        cache_line_size = board.get_cache_line_size()

        self.ruby_system = RubySystem()

        # MSI_Two_Level needs 5 virtual networks
        self.ruby_system.number_of_virtual_networks = 5

        self.ruby_system.network = SimplePt2Pt(self.ruby_system)
        self.ruby_system.network.number_of_virtual_networks = 5

        self._l1_controllers = []
        self._l2_controllers = []
        for i, core in enumerate(board.get_processor().get_cores()):
            l1_cache = L1Cache(
                l1i_size=self._l1i_size,
                l1i_assoc=self._l1i_assoc,
                l1d_size=self._l1d_size,
                l1d_assoc=self._l1d_assoc,
                network=self.ruby_system.network,
                core=core,
                cache_line_size=cache_line_size,
                target_isa=board.processor.get_isa(),
                clk_domain=board.get_clock_domain(),
                l1_data_lat=4,
                l1_tag_lat=2,
            )

            l1_cache.sequencer = RubySequencer(
                version=i, dcache=l1_cache.Dcache, clk_domain=l1_cache.clk_domain
            )

            if board.has_io_bus():
                l1_cache.sequencer.connectIOPorts(board.get_io_bus())

            l1_cache.ruby_system = self.ruby_system

            core.connect_icache(l1_cache.sequencer.in_ports)
            core.connect_dcache(l1_cache.sequencer.in_ports)

            core.connect_walker_ports(
                l1_cache.sequencer.in_ports, l1_cache.sequencer.in_ports
            )

            # Connect the interrupt ports
            if board.get_processor().get_isa() == ISA.X86:
                int_req_port = l1_cache.sequencer.interrupt_out_port
                int_resp_port = l1_cache.sequencer.in_ports
                core.connect_interrupt(int_req_port, int_resp_port)
            else:
                core.connect_interrupt()

            self._l1_controllers.append(l1_cache)

            l2_cache = L2Cache(
                    l2_size=self._l2_size,
                    l2_assoc=self._l2_assoc,
                    network=self.ruby_system.network,
                    num_l3Caches=self._num_l2_banks,
                    cache_line_size=cache_line_size,
                    clk_domain=board.get_clock_domain(),
                    l2_data_lat=9,
                    l2_tag_lat=2,
            )

            l2_cache.ruby_system = self.ruby_system
            l2_cache.bufferFromL0 = l1_cache.bufferToL1
            l2_cache.bufferToL0 = l1_cache.bufferFromL1

            self._l2_controllers.append(l2_cache)

        self._l3_controllers = [
            L3Cache(
                l3_tag_size=self._l3_size,
                l3_tag_assoc=self._l3_assoc,
                l3_data_size=self._l3_data_size,
                dir_cache_size=self._dir_cache_size,
                dir_cache_assoc=self._dir_cache_assoc,
                total_size=self._dir_l3_total_size,
                network=self.ruby_system.network,
                num_l3Caches=self._num_l2_banks,
                cache_line_size=cache_line_size,
                l3_data_lat=self._l3_data_lat,
                l3_tag_lat=self._l3_tag_lat,
                dir_data_lat=self._dir_data_lat,
                dir_tag_lat=self._dir_tag_lat,
                compression=self._l3_compression,
                data_array_rp_policy=self._l3_data_array_rp_policy,
                data_array_segment_size_in_byte = self._l3_data_array_segment_size_in_byte,
                data_array_regions = self._l3_data_array_regions,
                transitions_per_cycle=self._l3_transitions_per_cycle,
                index_bits_shift=self._index_bits_shift,
            )
            for _ in range(self._num_l2_banks)
        ]
        # TODO: Make this prettier: The problem is not being able to proxy
        # the ruby system correctly
        for cache in self._l3_controllers:
            cache.ruby_system = self.ruby_system

        self._directory_controllers = [
            Directory(self.ruby_system.network, cache_line_size, range, port)
            for range, port in board.get_mem_ports()
        ]
        # TODO: Make this prettier: The problem is not being able to proxy
        # the ruby system correctly
        for dir in self._directory_controllers:
            dir.ruby_system = self.ruby_system

        self._dma_controllers = []
        if board.has_dma_ports():
            dma_ports = board.get_dma_ports()
            for i, port in enumerate(dma_ports):
                ctrl = DMAController(self.ruby_system.network, cache_line_size)
                ctrl.dma_sequencer = DMASequencer(version=i, in_ports=port)
                self._dma_controllers.append(ctrl)
                ctrl.ruby_system = self.ruby_system

        self.ruby_system.num_of_sequencers = len(self._l1_controllers) + len(
            self._dma_controllers
        )
        self.ruby_system.l1_controllers = self._l1_controllers
        self.ruby_system.l2_controllers = self._l2_controllers
        self.ruby_system.l3_controllers = self._l3_controllers
        self.ruby_system.directory_controllers = self._directory_controllers

        if len(self._dma_controllers) != 0:
            self.ruby_system.dma_controllers = self._dma_controllers

        # Create the network and connect the controllers.
        self.ruby_system.network.connectControllers(
            self._l1_controllers
            + self._l2_controllers
            + self._l3_controllers
            + self._directory_controllers
            + self._dma_controllers
        )
        self.ruby_system.network.setup_buffers()

        # Set up a proxy port for the system_port. Used for load binaries and
        # other functional-only things.
        self.ruby_system.sys_port_proxy = RubyPortProxy()
        board.connect_system_port(self.ruby_system.sys_port_proxy.in_ports)
