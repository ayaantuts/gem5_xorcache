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

import math
from m5.objects import MessageBuffer, RubyCache, ClockDomain, RubyDataProc
from ......isas import ISA
from ..abstract_l1_cache import AbstractL1Cache
from ......utils.override import *




class L2Cache(AbstractL1Cache):
    def __init__(
        self,
        l2_size,
        l2_assoc,
        network,
        num_l3Caches,
        cache_line_size,
        clk_domain: ClockDomain,
        preproc="no_preproc",
        l2_data_lat=2,
        l2_tag_lat=2,
    ):
        """Creating L1 cache controller. Consist of both instruction
        and data cache.
        """
        super().__init__(network, cache_line_size)

        # This is the cache memory object that stores the cache data and tags
        self.cache = RubyCache(
            size=l2_size,
            assoc=l2_assoc,
            start_index_bit=self.getBlockSizeBits(),
            is_icache=False,
            dataAccessLatency = l2_data_lat,
            tagAccessLatency = l2_tag_lat,
        )
        self.l2_select_num_bits = int(math.log(num_l3Caches, 2))
        self.clk_domain = clk_domain
        self.transitions_per_cycle = 32

        self.dataProcL1 = RubyDataProc(
            preprocessing=preproc,
            compress="no_compress",
        )

    @overrides(AbstractL1Cache)
    def connectQueues(self, network):
        self.bufferToL0 = MessageBuffer()
        self.bufferToL0.out_port = network.in_port

        self.bufferFromL0 = MessageBuffer()
        self.bufferFromL0.in_port = network.out_port

        self.requestToL2 = MessageBuffer()
        self.requestToL2.out_port = network.in_port
        self.responseToL2 = MessageBuffer()
        self.responseToL2.out_port = network.in_port
        self.unblockToL2 = MessageBuffer()
        self.unblockToL2.out_port = network.in_port

        self.requestFromL2 = MessageBuffer()
        self.requestFromL2.in_port = network.out_port
        self.responseFromL2 = MessageBuffer()
        self.responseFromL2.in_port = network.out_port
        
        self.triggerQueue = MessageBuffer(
            allow_zero_latency=True,
        )
