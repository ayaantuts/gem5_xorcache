from m5.params import *
from m5.proxy import *
from m5.SimObject import SimObject

class RubyEntropyProfiler(SimObject):
    type = "RubyEntropyProfiler"
    cxx_class = "gem5::ruby::EntropyProfiler"
    cxx_header = "mem/ruby/structures/mystructures/msi/EntropyProfiler.hh"

    block_size = Param.MemorySize(
        "0B", "block size in bytes. 0 means default RubyBlockSize"
    )
    dedup_fingerprint_size_bits = Param.Int(
        16, "dedup fingerprint size in bits."
    )
    compute_line_level_entropy = Param.Bool(
        False, "compute line level entropy. By default, false."
    )
    xor_folding_scheme = Param.Int(0, "Regular xor folding")
    ruby_system = Param.RubySystem(Parent.any, "")
