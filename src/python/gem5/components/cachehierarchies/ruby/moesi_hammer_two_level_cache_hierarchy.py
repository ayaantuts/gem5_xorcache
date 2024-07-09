# Zhewen
# reference: configs/ruby/MOESI_hammer.py

import math
from .abstract_ruby_cache_hierarchy import AbstractRubyCacheHierarchy
from ..abstract_two_level_cache_hierarchy import AbstractTwoLevelCacheHierarchy
from ....coherence_protocol import CoherenceProtocol
from ....isas import ISA
from ...boards.abstract_board import AbstractBoard
from ....utils.requires import requires

from .topologies.simple_pt2pt import SimplePt2Pt
from .caches.moesi_hammer.l1_cache import L1and2Cache
from .caches.moesi_hammer.directory import Directory
from .caches.moesi_hammer.dma_controller import DMAController
# from m5.objects import RubySystem, RubySequencer, DMASequencer, RubyPortProxy, \
#     RubyCache,L1Cache_Controller,MessageBuffer,MemorySize
from m5.objects import MemorySize, RubySystem, RubySequencer, DMASequencer, RubyPortProxy


class MOESIHammerTwoLevelCacheHierarchy(
    AbstractRubyCacheHierarchy, AbstractTwoLevelCacheHierarchy
):
    """A two level private L1 shared L2 MESI hierarchy.

    In addition to the normal two level parameters, you can also change the
    number of L2 banks in this protocol.

    The on-chip network is a point-to-point all-to-all simple network.
    """

    def __init__(
        self,
        l1i_size: str,
        l1i_assoc: int,
        l1d_size: str,
        l1d_assoc: int,
        l2_size: str,
        l2_assoc: int,
        num_dirs:int,
    ):
        AbstractRubyCacheHierarchy.__init__(self=self)
        AbstractTwoLevelCacheHierarchy.__init__(
            self,
            l1i_size=l1i_size,
            l1i_assoc=l1i_assoc,
            l1d_size=l1d_size,
            l1d_assoc=l1d_assoc,
            l2_size=l2_size,
            l2_assoc=l2_assoc,
        )
        self._num_dirs = num_dirs


    def incorporate_cache(self, board: AbstractBoard) -> None:

        requires(coherence_protocol_required=CoherenceProtocol.ARM_MOESI_HAMMER)

        cache_line_size = board.get_cache_line_size()

        self.ruby_system = RubySystem()

        # MESI_Two_Level needs 5 virtual networks
        self.ruby_system.number_of_virtual_networks = 6

        self.ruby_system.network = SimplePt2Pt(self.ruby_system)
        self.ruby_system.network.number_of_virtual_networks = 6

        self._l1_controllers = []
        cache_line_size_bits = int(math.log(cache_line_size, 2))
        for i, core in enumerate(board.get_processor().get_cores()):
            cache = L1and2Cache(
                l1i_size=self._l1i_size,
                l1i_assoc=self._l1i_assoc,
                l1d_size=self._l1d_size,
                l1d_assoc=self._l1d_assoc,
                l2_size=self._l2_size, 
                l2_assoc=self._l2_assoc, 
                network=self.ruby_system.network,
                core=core,
                cache_line_size=cache_line_size,
                target_isa=board.get_processor().get_isa(),
                clk_domain=board.get_clock_domain(),
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

        # determine size and index bits for probe filter
        # By default, the probe filter size is configured to be twice the
        # size of the L2 cache.
        #
        pf_size = MemorySize(self._l2_size)
        pf_size.value = pf_size.value * 2
        print(self._num_dirs)
        dir_bits = int(math.log(self._num_dirs, 2))
        pf_bits = int(math.log(pf_size.value, 2))
        if dir_bits > 0:
            pf_start_bit = dir_bits + cache_line_size_bits - 1
        else:
            pf_start_bit = cache_line_size_bits

        self._directory_controllers = [
            Directory(self.ruby_system.network, cache_line_size,
                      pf_size, pf_start_bit, False,False,10, 
                      range, port)
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

        self.ruby_system.num_of_sequencers = len(self._l1_controllers) + len(self._dma_controllers)
        self.ruby_system.l1_controllers = self._l1_controllers
        self.ruby_system.directory_controllers = self._directory_controllers

        if len(self._dma_controllers) != 0:
            self.ruby_system.dma_controllers = self._dma_controllers

        # Create the network and connect the controllers.
        self.ruby_system.network.connectControllers(
            self._l1_controllers
            + self._directory_controllers
            + self._dma_controllers
        )
        self.ruby_system.network.setup_buffers()

        # Set up a proxy port for the system_port. Used for load binaries and
        # other functional-only things.
        self.ruby_system.sys_port_proxy = RubyPortProxy()
        board.connect_system_port(self.ruby_system.sys_port_proxy.in_ports)
