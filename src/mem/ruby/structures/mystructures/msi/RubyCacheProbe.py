from m5.params import *
from m5.objects.ReplacementPolicies import *
from m5.objects.RubyCache import RubyCache

# class Enforce(Enum):
#     vals = ["null", "same_core", "no_sharer", "many_valid_candidates", "clean"]

class RubyCacheProbe(RubyCache):
    type = "RubyCacheProbe"
    cxx_class = "gem5::ruby::CacheMemoryProbe"
    cxx_header = "mem/ruby/structures/mystructures/msi/CacheMemoryProbe.hh"

    valid_candidate_ct_threshold = Param.Int(0, "valid candidate count threshold")
    # enforce = Param.Enforce("clean", "enforce xor candidates to be from the same core")
    