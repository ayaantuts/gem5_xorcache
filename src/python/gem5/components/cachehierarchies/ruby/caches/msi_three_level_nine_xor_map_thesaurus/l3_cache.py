from ..abstract_l2_cache import AbstractL2Cache
from ......utils.override import *

from m5.objects import MessageBuffer, RubyCache, RubyCacheDualAddr, RubyCacheProbe, RubyDataProc, RubyDirectMapTable,\
    RubyCacheFASector,RubyCacheSASector,RubyCacheRegionSector, RubyEntropyProfiler,\
    RubyCacheCounter
from m5.objects import RubyAssociativeMapTable
from m5.objects.ReplacementPolicies import *

import math


class L3Cache(AbstractL2Cache):
    def __init__(
        self, l3_tag_size, l3_tag_assoc, l3_data_size, 
        dir_cache_size, dir_cache_assoc, total_size,
        network, num_l3Caches, cache_line_size, 
        l3_data_lat, l3_tag_lat, dir_data_lat, dir_tag_lat, 
        data_array_rp_policy,
        data_array_segment_size_in_byte,
        l3_tagptr_size_in_bit,
        data_array_regions,
        search_scope="bank", rank_criteria="random",
        valid_candidate_ct_threshold=0,
        map_bits=8, list_capacity=128, num_maptable_set=64,
        data_full_percentage=85,
        compression="thesaurus",
        preproc="no_preproc",
        record_footprint=True,
        record_line_level_entropy=False,
        xor_folding_scheme=0,
        xor_policy="balanced",
        transitions_per_cycle="4",
        index_bits_shift=0
    ):
        super().__init__(network, cache_line_size)

        # This is the cache memory object that stores the cache data and tags
        self.L2cache = RubyCacheDualAddr( #logical
            size=total_size,
            assoc=0,
            start_index_bit=self.getIndexBit(num_l3Caches)+index_bits_shift,
            dataAccessLatency = l3_data_lat,
            tagAccessLatency = l3_tag_lat,
            record_footprint=record_footprint,
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
        self.tagNS = RubyCacheProbe(
            size=l3_tag_size,
            assoc=l3_tag_assoc,
            start_index_bit=self.getIndexBit(num_l3Caches)+index_bits_shift,
            replacement_policy= LRURP(),
        )

        if data_array_rp_policy == "lru":
            data_array_rp_policy_ins = LRURP()
        elif data_array_rp_policy == "random":
            data_array_rp_policy_ins = RandomRP()
        else: assert False, "data_array_rp_policy must be either 'lru' or 'random'"

        # self.data = RubyCacheFASector(
        #     size=l3_data_size, #1B per sector so this value has to be size * block size in bytes
        #     assoc=0,
        #     full_percentage=data_full_percentage,
        #     start_index_bit=self.getIndexBit(num_l3Caches)+index_bits_shift,
        #     replacement_policy=data_array_rp_policy_ins,
        # )
        self.data = RubyCacheRegionSector(
            size=l3_data_size, #1B per sector so this value has to be size * block size in bytes
            assoc=0,
            full_percentage=data_full_percentage,
            start_index_bit=self.getIndexBit(num_l3Caches)+index_bits_shift,
            replacement_policy=data_array_rp_policy_ins,
            num_regions=data_array_regions,
        )

        # self.dataNS = RubyCacheFASector(
        #     size=l3_data_size, #1B per sector so this value has to be size * block size in bytes
        #     assoc=0,
        #     full_percentage=data_full_percentage,
        #     start_index_bit=self.getIndexBit(num_l3Caches)+index_bits_shift,
        #     replacement_policy=data_array_rp_policy_ins,
        # )
        self.dataNS = RubyCacheRegionSector(
            size=l3_data_size, #1B per sector so this value has to be size * block size in bytes
            assoc=0,
            full_percentage=data_full_percentage,
            start_index_bit=self.getIndexBit(num_l3Caches)+index_bits_shift,
            replacement_policy=data_array_rp_policy_ins,
            num_regions=data_array_regions,
        )

        if search_scope == "bank":
            singular_tag_asssoc = 0
        elif search_scope == "set":
            singular_tag_asssoc = l3_tag_assoc
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
            size=l3_tag_size,
            assoc=singular_tag_asssoc,
            start_index_bit=self.getIndexBit(num_l3Caches)+index_bits_shift,
            replacement_policy=singular_tag_rp_policy,
            valid_candidate_ct_threshold=valid_candidate_ct_threshold,
        )
        self.singularTagShared = RubyCacheProbe(
            size=l3_tag_size,
            assoc=singular_tag_asssoc,
            start_index_bit=self.getIndexBit(num_l3Caches)+index_bits_shift,
            replacement_policy=singular_tag_rp_policy,
            valid_candidate_ct_threshold=valid_candidate_ct_threshold,
        )

        self.dataProc = RubyDataProc(
            preprocessing=preproc,
            compress=compression,
            segment_size_in_byte=data_array_segment_size_in_byte,
            tagptr_size_in_bit=l3_tagptr_size_in_bit,
            DecompressLatency=5,
        )

        # self.dmt = RubyDirectMapTable(
        #     map_bits=map_bits,
        #     list_capacity=list_capacity,
        #     regular_xor_folding=regular_xor_folding,
        #     xor_policy=xor_policy,
        # )
        # self.dmtShared = RubyDirectMapTable(
        #     map_bits=map_bits,
        #     list_capacity=list_capacity,
        #     regular_xor_folding=regular_xor_folding,
        #     xor_policy=xor_policy,
        # )
        # self.dmtNShared = RubyDirectMapTable(
        #     map_bits=map_bits,
        #     list_capacity=list_capacity,
        #     regular_xor_folding=regular_xor_folding,
        #     xor_policy=xor_policy,
        # )
        self.dmt = RubyAssociativeMapTable(
            map_bits=map_bits,
            num_set=num_maptable_set,
            list_capacity=list_capacity,
            xor_folding_scheme=xor_folding_scheme,
            xor_policy=xor_policy,
        )
        self.dmtShared = RubyAssociativeMapTable(
            map_bits=map_bits,
            num_set=num_maptable_set,
            list_capacity=list_capacity,
            xor_folding_scheme=xor_folding_scheme,
            xor_policy=xor_policy,
        )
        self.dmtNShared = RubyAssociativeMapTable(
            map_bits=map_bits,
            num_set=num_maptable_set,
            list_capacity=list_capacity,
            xor_folding_scheme=xor_folding_scheme,
            xor_policy=xor_policy,
        )

        self.entropyProfiler = RubyEntropyProfiler(
            compute_line_level_entropy=record_line_level_entropy,
            xor_folding_scheme=xor_folding_scheme,
        )
        self.entropyProfilerRaw = RubyEntropyProfiler(
            compute_line_level_entropy=False,
            xor_folding_scheme=xor_folding_scheme,
        )
        self.entropyProfilerXORed = RubyEntropyProfiler(
            compute_line_level_entropy=False,
            xor_folding_scheme=xor_folding_scheme,
        )

        self.centroidCache = RubyCache(
            size="32kB",
            assoc=8,
            start_index_bit=int(math.log(self._cache_line_size, 2)),
        )
        self.centroidMemory = RubyCacheCounter(
            size="256kB",
            assoc=1,
            start_index_bit=int(math.log(self._cache_line_size, 2)),
        )

        self.transitions_per_cycle = transitions_per_cycle
        # self.transitions_per_cycle = "8" # 4 for cache plus 4 for directory

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

        self.triggerQueue = MessageBuffer(
            allow_zero_latency=True,
        )