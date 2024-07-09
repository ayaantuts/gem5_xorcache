from m5.params import *
from m5.objects.ReplacementPolicies import *
from m5.objects.RubyCacheDecoupled import RubyCacheDecoupled

class RubyCacheBDIXOR(RubyCacheDecoupled):
    type = "RubyCacheBDIXOR"
    cxx_class = "gem5::ruby::CacheMemoryBDIXOR"
    cxx_header = "mem/ruby/structures/mystructures/CacheMemoryBDIXOR.hh"

    include_proactive_eviction = Param.Bool(True, "if this cache include proactive evictions, eg., MT,L1_PUTX incurred")
    search_in_set = Param.Bool(True, "if xor candidates are only from the same set")
    xor_policy_id = Param.Int(1, "xor policy id. 1:greedy; 2:same core only")
    # print_util_interval_tick = Param.UInt64(10000000000, "print utilization every interval ticks")
