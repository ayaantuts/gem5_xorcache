from m5.params import *
from m5.objects.ReplacementPolicies import *
from m5.objects.RubyCache import RubyCache

class RubyCacheRegionSector(RubyCache):
    type = "RubyCacheRegionSector"
    cxx_class = "gem5::ruby::CacheMemoryRegionSector"
    cxx_header = "mem/ruby/structures/mystructures/msi/CacheMemoryRegionSector.hh"

    full_percentage = Param.Percent(85, "percentage of sectors that must be full before a sector is considered full")    
    num_regions = Param.Int(32, "number of regions in the cache")
    # replacement_policy = Param.BaseReplacementPolicy(RandomRP(), "")
