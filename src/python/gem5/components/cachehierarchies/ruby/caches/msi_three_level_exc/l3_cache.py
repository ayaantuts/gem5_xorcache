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

from ..abstract_l2_cache import AbstractL2Cache
from ......utils.override import *

from m5.objects import MessageBuffer, RubyCache,RubyDataProc,RubyCacheRegionSector

from m5.objects.ReplacementPolicies import *

import math


class L3Cache(AbstractL2Cache):
    def __init__(
        self, l3_tag_size, l3_tag_assoc, l3_data_size, 
        dir_cache_size, dir_cache_assoc, total_size,
        network, num_l3Caches, cache_line_size, 
        l3_data_lat, l3_tag_lat, dir_data_lat, dir_tag_lat, 
        data_array_segment_size_in_byte,
        data_array_regions,
        data_array_rp_policy,
        transitions_per_cycle="4",
        compression="no_compress",
        index_bits_shift=0
    ):
        super().__init__(network, cache_line_size)

        # This is the cache memory object that stores the cache data and tags
        self.L2cache = RubyCache( #logical
            size=total_size,
            assoc=0,
            start_index_bit=self.getIndexBit(num_l3Caches)+index_bits_shift,
            dataAccessLatency = l3_data_lat,
            tagAccessLatency = l3_tag_lat,
        )
        self.dir = RubyCache(
            size=dir_cache_size,
            assoc=dir_cache_assoc,
            start_index_bit=self.getIndexBit(num_l3Caches)+index_bits_shift,
            dataAccessLatency = dir_data_lat,
            tagAccessLatency = dir_tag_lat,
        )
        self.tag = RubyCache(
            size=l3_tag_size,
            assoc=l3_tag_assoc,
            start_index_bit=self.getIndexBit(num_l3Caches)+index_bits_shift,
        )
        if data_array_rp_policy == "lru":
            data_array_rp_policy_ins = LRURP()
        elif data_array_rp_policy == "random":
            data_array_rp_policy_ins = RandomRP()
        else: assert False, "data_array_rp_policy must be either 'lru' or 'random'"

        self.data = RubyCacheRegionSector(
            size=l3_data_size, # 1:1 mapping
            assoc=0,
            start_index_bit=self.getIndexBit(num_l3Caches)+index_bits_shift,
            replacement_policy=data_array_rp_policy_ins,
            # full_percentage=data_full_percentage,
            num_regions=data_array_regions,
        )

        self.dataProc = RubyDataProc(
            preprocessing="no_preproc",
            compress=compression,
            segment_size_in_byte=data_array_segment_size_in_byte,
        )

        self.transitions_per_cycle = transitions_per_cycle

    def getIndexBit(self, num_l3caches):
        l3_bits = int(math.log(num_l3caches, 2))
        bits = int(math.log(self._cache_line_size, 2)) + l3_bits
        return bits

    @overrides(AbstractL2Cache)
    def connectQueues(self, network):
        self.DirRequestFromL2Cache = MessageBuffer()
        self.DirRequestFromL2Cache.out_port = network.in_port
        self.L1RequestFromL2Cache = MessageBuffer()
        self.L1RequestFromL2Cache.out_port = network.in_port
        self.responseFromL2Cache = MessageBuffer()
        self.responseFromL2Cache.out_port = network.in_port
        self.unblockToL2Cache = MessageBuffer()
        self.unblockToL2Cache.in_port = network.out_port
        self.L1RequestToL2Cache = MessageBuffer()
        self.L1RequestToL2Cache.in_port = network.out_port
        self.responseToL2Cache = MessageBuffer()
        self.responseToL2Cache.in_port = network.out_port
