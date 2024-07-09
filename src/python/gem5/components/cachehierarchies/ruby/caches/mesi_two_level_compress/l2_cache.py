from ..abstract_l2_cache import AbstractL2Cache
from ......utils.override import *

from m5.objects import MessageBuffer, RubyCacheDecoupled, RubyCompressor

import math


class L2Cache(AbstractL2Cache):
    def __init__(
        self, l2_size, l2_assoc, network, num_l2Caches, num_seg_per_blk, cache_line_size, data_lat, tag_lat,
        print_util_interval_tick
    ):
        super().__init__(network, cache_line_size)

        # This is the cache memory object that stores the cache data and tags
        # data array always has half associativity than the tag array
        self.L2cache = RubyCacheDecoupled(
            size=l2_size,
            assoc=l2_assoc,
            start_index_bit=self.getIndexBit(num_l2Caches),
            dataArrayAssoc=l2_assoc/2,
            dataArraySet=0,
            numSegPerBlk = num_seg_per_blk,
            dataAccessLatency = data_lat,
            tagAccessLatency = tag_lat,
            print_util_interval_tick = print_util_interval_tick,
        )
        self.L2compressor = RubyCompressor(
            CompressLatency=1,
        )

        self.transitions_per_cycle = "4"

    def getIndexBit(self, num_l2caches):
        l2_bits = int(math.log(num_l2caches, 2))
        bits = int(math.log(self._cache_line_size, 2)) + l2_bits
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
