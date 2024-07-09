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
from ..abstract_two_level_cache_hierarchy import AbstractTwoLevelCacheHierarchy
from ....coherence_protocol import CoherenceProtocol
from ....isas import ISA
from ...boards.abstract_board import AbstractBoard
from ....utils.requires import requires

from .topologies.simple_pt2pt import SimplePt2Pt
from .caches.msi_two_level_nine_xor_map.l1_cache import L1Cache
from .caches.msi_two_level_nine_xor_map.l2_cache import L2Cache
from .caches.msi_two_level_nine_xor_map.directory import Directory
from .caches.msi_two_level_nine_xor_map.dma_controller import DMAController

from m5.objects import RubySystem, RubySequencer, DMASequencer, RubyPortProxy


class MSITwoLevelNineNoXORMAPCacheHierarchy(
    AbstractRubyCacheHierarchy, AbstractTwoLevelCacheHierarchy
):
    """A two level private L1 shared L2 MSI hierarchy.

    In addition to the normal two level parameters, you can also change the
    number of L2 banks in this protocol.

    The on-chip network is a point-to-point all-to-all simple network.
    """

    def __init__(
        self,
        l1i_size: str,
        l1i_assoc: str,
        l1d_size: str,
        l1d_assoc: str,
        l2_tag_size: str,
        l2_tag_assoc: str,
        l2_data_size: str,
        dir_cache_size: str,
        dir_cache_assoc: str,
        dir_l2_total_size: str,
        num_l2_banks: int,
        # num_seg_per_blk: int,
        l2_data_lat: int,
        l2_tag_lat: int,
        dir_data_lat: int,
        dir_tag_lat: int,
        # l2_dataArraySet: int,
        # l2_dataArrayWay: int,
        l2_transitions_per_cycle:str,
        l2_data_array_segment_size_in_byte,
        l2_data_array_regions,
        l2_data_array_rp_policy: str="random",
        l2_xor_search_scope: str="bank", 
        l2_xor_rank_criteria: str="random",
        l2_map_bits: int=8,
        l2_list_capacity: int=128,
        l2_num_maptable_set: int=64,
        l2_compression: str="no_compress",
        l2_preproc: str="no_preproc",
        record_line_level_entropy: bool=False,
        xor_folding_scheme: int=0,#dense byte labeling
        index_bits_shift: int=0,
    ):
        AbstractRubyCacheHierarchy.__init__(self=self)
        AbstractTwoLevelCacheHierarchy.__init__(
            self,
            l1i_size=l1i_size,
            l1i_assoc=l1i_assoc,
            l1d_size=l1d_size,
            l1d_assoc=l1d_assoc,
            l2_size=l2_tag_size,
            l2_assoc=l2_tag_assoc,
        )

        self._num_l2_banks = num_l2_banks
        self._l2_data_size = l2_data_size
        # self._num_seg_per_blk = num_seg_per_blk
        self._l2_data_lat = l2_data_lat
        self._l2_tag_lat = l2_tag_lat
        self._dir_data_lat = dir_data_lat
        self._dir_tag_lat = dir_tag_lat
        self._dir_cache_size = dir_cache_size
        self._dir_cache_assoc = dir_cache_assoc
        self._dir_l2_total_size = dir_l2_total_size
        # self._l2_dataArraySet = l2_dataArraySet
        # self._l2_dataArrayWay = l2_dataArrayWay
        self._l2_xor_search_scope = l2_xor_search_scope
        self._l2_xor_rank_criteria = l2_xor_rank_criteria
        self._l2_map_bits = l2_map_bits
        self._l2_list_capacity = l2_list_capacity
        self._l2_num_maptable_set = l2_num_maptable_set
        self._l2_compression = l2_compression
        self._l2_preproc = l2_preproc
        self._l2_data_array_rp_policy = l2_data_array_rp_policy
        self._l2_data_array_segment_size_in_byte = l2_data_array_segment_size_in_byte
        self._l2_data_array_regions = l2_data_array_regions
        self._record_line_level_entropy = record_line_level_entropy
        self._xor_folding_scheme = xor_folding_scheme
        self._l2_transitions_per_cycle = l2_transitions_per_cycle

        self._index_bits_shift = index_bits_shift

    def incorporate_cache(self, board: AbstractBoard) -> None:

        requires(coherence_protocol_required=CoherenceProtocol.MSI_TWO_LEVEL_NINE_XOR_MAP)

        cache_line_size = board.get_cache_line_size()

        self.ruby_system = RubySystem()

        # MSI_Two_Level needs 5 virtual networks
        self.ruby_system.number_of_virtual_networks = 6

        self.ruby_system.network = SimplePt2Pt(self.ruby_system)
        self.ruby_system.network.number_of_virtual_networks = 6

        self._l1_controllers = []
        for i, core in enumerate(board.get_processor().get_cores()):
            cache = L1Cache(
                self._l1i_size,
                self._l1i_assoc,
                self._l1d_size,
                self._l1d_assoc,
                self.ruby_system.network,
                core,
                self._num_l2_banks,
                cache_line_size,
                board.processor.get_isa(),
                board.get_clock_domain(),
            )

            cache.sequencer = RubySequencer(
                version=i, dcache=cache.L1Dcache, clk_domain=cache.clk_domain
            )

            if board.has_io_bus():
                cache.sequencer.connectIOPorts(board.get_io_bus())

            cache.ruby_system = self.ruby_system

            core.connect_icache(cache.sequencer.in_ports)
            core.connect_dcache(cache.sequencer.in_ports)

            core.connect_walker_ports(
                cache.sequencer.in_ports, cache.sequencer.in_ports
            )

            # Connect the interrupt ports
            if board.get_processor().get_isa() == ISA.X86:
                int_req_port = cache.sequencer.interrupt_out_port
                int_resp_port = cache.sequencer.in_ports
                core.connect_interrupt(int_req_port, int_resp_port)
            else:
                core.connect_interrupt()

            self._l1_controllers.append(cache)

        self._l2_controllers = [
            L2Cache(
                l2_tag_size=self._l2_size,
                l2_tag_assoc=self._l2_assoc,
                l2_data_size=self._l2_data_size,
                dir_cache_size=self._dir_cache_size,
                dir_cache_assoc=self._dir_cache_assoc,
                total_size=self._dir_l2_total_size,
                network=self.ruby_system.network,
                num_l2Caches=self._num_l2_banks,
                cache_line_size=cache_line_size,
                l2_data_lat=self._l2_data_lat,
                l2_tag_lat=self._l2_tag_lat,
                dir_data_lat=self._dir_data_lat,
                dir_tag_lat=self._dir_tag_lat,
                search_scope=self._l2_xor_search_scope,
                rank_criteria=self._l2_xor_rank_criteria,
                map_bits=self._l2_map_bits,
                list_capacity=self._l2_list_capacity,
                num_maptable_set=self._l2_num_maptable_set,
                compression=self._l2_compression,
                preproc=self._l2_preproc,
                valid_candidate_ct_threshold=9999999,#some large numbers
                data_array_rp_policy=self._l2_data_array_rp_policy,
                data_array_segment_size_in_byte = self._l2_data_array_segment_size_in_byte,
                data_array_regions = self._l2_data_array_regions,
                record_line_level_entropy = self._record_line_level_entropy,
                xor_folding_scheme = self._xor_folding_scheme,
                transitions_per_cycle=self._l2_transitions_per_cycle,
                index_bits_shift=self._index_bits_shift,
            )
            for _ in range(self._num_l2_banks)
        ]
        # TODO: Make this prettier: The problem is not being able to proxy
        # the ruby system correctly
        for cache in self._l2_controllers:
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
        self.ruby_system.directory_controllers = self._directory_controllers

        if len(self._dma_controllers) != 0:
            self.ruby_system.dma_controllers = self._dma_controllers

        # Create the network and connect the controllers.
        self.ruby_system.network.connectControllers(
            self._l1_controllers
            + self._l2_controllers
            + self._directory_controllers
            + self._dma_controllers
        )
        self.ruby_system.network.setup_buffers()

        # Set up a proxy port for the system_port. Used for load binaries and
        # other functional-only things.
        self.ruby_system.sys_port_proxy = RubyPortProxy()
        board.connect_system_port(self.ruby_system.sys_port_proxy.in_ports)
