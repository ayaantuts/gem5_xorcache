# Copyright (c) 2021 The Regents of the University of California
# All Rights Reserved.
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

from .....processors.abstract_core import AbstractCore
from ......isas import ISA
from ..abstract_l0_cache import AbstractL0Cache
from ......utils.override import *

from m5.objects import MessageBuffer, RubyCache, ClockDomain,LRURP

import math


class L1Cache(AbstractL0Cache):
    def __init__(
        self,
        l1i_size,
        l1i_assoc,
        l1d_size,
        l1d_assoc,
        network,
        core: AbstractCore,
        cache_line_size,
        target_isa: ISA,
        clk_domain: ClockDomain,
        l1_data_lat,
        l1_tag_lat,
    ):
        """Creating L1 cache controller. Consist of both instruction
        and data cache.
        """
        super().__init__(network, cache_line_size)

        # This is the cache memory object that stores the cache data and tags
        self.Icache = RubyCache(
            size=l1i_size,
            assoc=l1i_assoc,
            start_index_bit=self.getBlockSizeBits(cache_line_size),
            is_icache=True,
            replacement_policy=LRURP(),
            dataAccessLatency = l1_data_lat,
            tagAccessLatency = l1_tag_lat,
        )
        self.Dcache = RubyCache(
            size=l1d_size,
            assoc=l1d_assoc,
            start_index_bit=self.getBlockSizeBits(cache_line_size),
            is_icache=False,
            replacement_policy=LRURP(),
            dataAccessLatency = l1_data_lat,
            tagAccessLatency = l1_tag_lat,
        )
        self.clk_domain = clk_domain
        self.send_evictions = True
        self.transitions_per_cycle = 32

    @overrides(AbstractL0Cache)
    def connectQueues(self, network):
        self.mandatoryQueue = MessageBuffer()

        # bufferToL1 and bufferFromL1 are ruby backend terminology.
        # In stdlib terms, they are bufferToL2 and bufferFromL2 respectively.
        # These buffers are connections between L1 cache and L2 cache.
        # Later on, we'll need to connect those buffers to L2.
        self.bufferToL1 = MessageBuffer(ordered=True)
        self.bufferFromL1 = MessageBuffer(ordered=True)

