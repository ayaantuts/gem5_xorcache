from m5.params import *
from m5.proxy import *
from m5.SimObject import SimObject
from m5.objects import XOR_Policy

class RubyAssociativeMapTable(SimObject):
    type = "RubyAssociativeMapTable"
    cxx_class = "gem5::ruby::AssociativeMapTable"
    cxx_header = "mem/ruby/structures/mystructures/msi/AssociativeMapTable.hh"

    block_size = Param.MemorySize(
        "0B", "block size in bytes. 0 means default RubyBlockSize"
    )
    map_bits = Param.Int(8, "Number of bits to map")
    num_set = Param.Int(64, "Number of sets in the map table")
    xor_policy = Param.XOR_Policy("balanced", "xor policy knob")
    list_capacity = Param.Int(128, "Number of entries in the list")
    xor_folding_scheme = Param.Int(0, "Regular xor folding")
    ruby_system = Param.RubySystem(Parent.any, "")
