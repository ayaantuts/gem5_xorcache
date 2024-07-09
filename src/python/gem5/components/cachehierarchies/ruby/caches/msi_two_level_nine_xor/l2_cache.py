from ..abstract_l2_cache import AbstractL2Cache
from ......utils.override import *

from m5.objects import MessageBuffer, RubyCache, RubyCacheDualAddr, RubyCacheProbe, RubyDataProc, Preproc, Compress
from m5.objects.ReplacementPolicies import *

import math


class L2Cache(AbstractL2Cache):
    def __init__(
        self, l2_tag_size, l2_tag_assoc, l2_data_size, 
        dir_cache_size, dir_cache_assoc, total_size,
        network, num_l2Caches, cache_line_size, 
        l2_data_lat, l2_tag_lat, dir_data_lat, dir_tag_lat, 
        search_scope="bank", rank_criteria="random",
        valid_candidate_ct_threshold=0,
        compression="no_compression",
        index_bits_shift=0
    ):
        super().__init__(network, cache_line_size)

        # This is the cache memory object that stores the cache data and tags
        self.L2cache = RubyCacheDualAddr( #logical
            size=total_size,
            assoc=0,
            start_index_bit=self.getIndexBit(num_l2Caches)+index_bits_shift,
            dataAccessLatency = l2_data_lat,
            tagAccessLatency = l2_tag_lat,
        )
        self.dir = RubyCache(
            size=dir_cache_size,
            assoc=dir_cache_assoc,
            start_index_bit=self.getIndexBit(num_l2Caches)+index_bits_shift,
            dataAccessLatency = dir_data_lat,
            tagAccessLatency = dir_tag_lat,
        )
        self.tag = RubyCache(
            size=l2_tag_size,
            assoc=l2_tag_assoc,
            start_index_bit=self.getIndexBit(num_l2Caches)+index_bits_shift,
        )
        self.data = RubyCache(
            size=l2_data_size, # flexible mapping
            assoc=0,
            start_index_bit=self.getIndexBit(num_l2Caches)+index_bits_shift,
        )

        if search_scope == "bank":
            singular_tag_asssoc = 0
        elif search_scope == "set":
            singular_tag_asssoc = l2_tag_assoc
        else: assert False, "search_scope must be either 'bank' or 'set'"

        if rank_criteria == "lru":
            singular_tag_rp_policy = LRURP()
        elif rank_criteria == "mru":
            singular_tag_rp_policy = MRURP()
        elif rank_criteria == "random":
            singular_tag_rp_policy = RandomRP()
        elif rank_criteria == "similarity":
            assert False, "rank_criteria 'similarity' not implemented yet"
        else: assert False, "rank_criteria must be either 'lru', 'mru', 'random', or 'similarity'"
            
        self.singularTag = RubyCacheProbe(
            size=l2_tag_size,
            assoc=singular_tag_asssoc,
            start_index_bit=self.getIndexBit(num_l2Caches)+index_bits_shift,
            replacement_policy=singular_tag_rp_policy,
            valid_candidate_ct_threshold=valid_candidate_ct_threshold,
        )
        self.singularTagShared = RubyCacheProbe(
            size=l2_tag_size,
            assoc=singular_tag_asssoc,
            start_index_bit=self.getIndexBit(num_l2Caches)+index_bits_shift,
            replacement_policy=singular_tag_rp_policy,
            valid_candidate_ct_threshold=valid_candidate_ct_threshold,
        )

        self.dataProc = RubyDataProc(
            compress=compression,
        )
        self.transitions_per_cycle = "4"
        # self.transitions_per_cycle = "8" # 4 for cache plus 4 for directory

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

        # self.triggerQueue = MessageBuffer(
        #     allow_zero_latency=True,
        # )