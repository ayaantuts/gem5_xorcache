from m5.params import *
from m5.objects.ReplacementPolicies import *
from m5.objects.RubyCache import RubyCache

class RubyCacheFASector(RubyCache):
    type = "RubyCacheFASector"
    cxx_class = "gem5::ruby::CacheMemoryFASector"
    cxx_header = "mem/ruby/structures/mystructures/msi/CacheMemoryFASector.hh"

    full_percentage = Param.Percent(85, "percentage of sectors that must be full before a sector is considered full")    
    # replacement_policy = Param.BaseReplacementPolicy(RandomRP(), "")
