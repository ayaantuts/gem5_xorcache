from m5.params import *
from m5.objects.ReplacementPolicies import *
from m5.objects.RubyCache import RubyCache

class RubyCacheDecoupledTagData(RubyCache):
    type = "RubyCacheDecoupledTagData"
    cxx_class = "gem5::ruby::CacheMemoryDecoupledTagData"
    cxx_header = "mem/ruby/structures/mystructures/msi/CacheMemoryDecoupledTagData.hh"
    
    dataArrayAssoc = Param.Int("Associativity of data array")
    dataArraySet = Param.Int("number of set of data array")
    numSegPerBlk = Param.Int("number of segment per block")
    replacement_policy_data = Param.BaseReplacementPolicy(LRURP(), "")
    print_util_interval_tick = Param.UInt64(10000000000, "print utilization every interval ticks")
