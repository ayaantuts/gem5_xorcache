from m5.params import *
from m5.objects.ReplacementPolicies import *
from m5.objects.RubyCache import RubyCache

class RubyCacheSASector(RubyCache):
    type = "RubyCacheSASector"
    cxx_class = "gem5::ruby::CacheMemorySASector"
    cxx_header = "mem/ruby/structures/mystructures/msi/CacheMemorySASector.hh"

    full_percentage = Param.Percent(85, "percentage of sectors that must be full before a sector is considered full")    