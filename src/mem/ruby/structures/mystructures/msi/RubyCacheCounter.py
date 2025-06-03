from m5.params import *
from m5.objects.ReplacementPolicies import *
from m5.objects.RubyCache import RubyCache


class RubyCacheCounter(RubyCache):
    type = "RubyCacheCounter"
    cxx_class = "gem5::ruby::CacheMemoryCounter"
    cxx_header = "mem/ruby/structures/mystructures/msi/CacheMemoryCounter.hh"

    