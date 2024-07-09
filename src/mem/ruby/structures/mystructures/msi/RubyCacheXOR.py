from m5.params import *
from m5.objects.ReplacementPolicies import *
from m5.objects.RubyCacheDecoupledTagData import RubyCacheDecoupledTagData

class SearchScope(Enum):
    vals = ["bank", "set"]

class Enforce(Enum):
    vals = ["null", "same_core", "no_sharer", "many_valid_candidates", "clean"]
    
class RankCriteria(Enum):
    vals = ["lru", "mru", "random", "similarity"]

class RubyCacheXOR(RubyCacheDecoupledTagData):
    type = "RubyCacheXOR"
    cxx_class = "gem5::ruby::CacheMemoryXOR"
    cxx_header = "mem/ruby/structures/mystructures/msi/CacheMemoryXOR.hh"

    search_scope = Param.SearchScope("set", "search scope for xor candidates")
    enforce = Param.Enforce("clean", "enforce xor candidates to be from the same core")
    rank_criteria = Param.RankCriteria("random", "rank criteria for xor candidates")
    valid_candidate_ct_threshold = Param.Int(2, "valid candidate count threshold")
