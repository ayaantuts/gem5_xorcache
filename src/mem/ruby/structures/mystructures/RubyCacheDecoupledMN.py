from m5.params import *
from m5.objects.ReplacementPolicies import *
from m5.objects.RubyCacheDecoupled import RubyCacheDecoupled

class RubyCacheDecoupledMN(RubyCacheDecoupled):
    type = "RubyCacheDecoupledMN"
    cxx_class = "gem5::ruby::CacheMemoryDecoupledMN"
    cxx_header = "mem/ruby/structures/mystructures/CacheMemoryDecoupledMN.hh"

    numHashBucket = Param.Int(8192, "number of hash buckets; (hash table) num of set")
    chainLength = Param.Int(16,"number of chain length of each hash bucket; (hash table) associativity")
    replacement_policy_hashTable = Param.BaseReplacementPolicy(LRURP(), "")
    partialHashLength = Param.Int(15, "partial hash length (tag bits)")
