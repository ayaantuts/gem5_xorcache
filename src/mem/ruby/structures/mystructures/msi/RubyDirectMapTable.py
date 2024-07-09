from m5.params import *
from m5.proxy import *
from m5.SimObject import SimObject


class XOR_Policy(Enum):
    vals = [
        "balanced", # balanced between inter compression oppurtunity and intra compression oppurtunity
        "synergy", # focus on intra compression oppurtunity (only xor when bin hit)
        "oppurtunistic" # focus on inter compression oppurtunity (xor whenever possible)
        ]

class RubyDirectMapTable(SimObject):
    type = "RubyDirectMapTable"
    cxx_class = "gem5::ruby::DirectMapTable"
    cxx_header = "mem/ruby/structures/mystructures/msi/DirectMapTable.hh"

    block_size = Param.MemorySize(
        "0B", "block size in bytes. 0 means default RubyBlockSize"
    )
    map_bits = Param.Int(8, "Number of bits to map")
    xor_policy = Param.XOR_Policy("balanced", "xor policy knob")
    list_capacity = Param.Int(128, "Number of entries in the list")
    xor_folding_scheme = Param.Int(0, "Regular xor folding")
    ruby_system = Param.RubySystem(Parent.any, "")
