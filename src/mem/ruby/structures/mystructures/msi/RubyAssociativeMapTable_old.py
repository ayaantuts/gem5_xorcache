from m5.params import *
from m5.proxy import *
from m5.SimObject import SimObject
from m5.objects import XOR_Policy
from m5.objects.ReplacementPolicies import *


class RubyAssociativeMapTable(SimObject):
    type = "RubyAssociativeMapTable"
    cxx_class = "gem5::ruby::AssociativeMapTable"
    cxx_header = "mem/ruby/structures/mystructures/msi/AssociativeMapTable.hh"

    block_size = Param.MemorySize(
        "0B", "block size in bytes. 0 means default RubyBlockSize"
    )
    map_bits = Param.Int(8, "Number of bits to map")
    num_sets = Param.Int(64, "Number of sets in the map table")
    assoc = Param.Int(4, "Associativity of the map table")
    xor_policy = Param.XOR_Policy("balanced", "xor policy knob")
    regular_xor_folding = Param.Bool(True, "Regular xor folding")
    replacement_policy = Param.BaseReplacementPolicy(LRURP(), "")
    ruby_system = Param.RubySystem(Parent.any, "")
