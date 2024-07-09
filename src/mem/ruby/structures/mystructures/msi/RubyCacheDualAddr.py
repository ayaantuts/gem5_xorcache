from m5.params import *
from m5.objects.ReplacementPolicies import *
from m5.objects.RubyCache import RubyCache

class RubyCacheDualAddr(RubyCache):
    type = "RubyCacheDualAddr"
    cxx_class = "gem5::ruby::CacheMemoryDualAddr"
    cxx_header = "mem/ruby/structures/mystructures/msi/CacheMemoryDualAddr.hh"
    
