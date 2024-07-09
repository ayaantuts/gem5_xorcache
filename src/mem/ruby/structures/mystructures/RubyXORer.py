from m5.params import *
from m5.proxy import *
from m5.SimObject import SimObject


class RubyXORer(SimObject):
    type = "RubyXORer"
    cxx_class = "gem5::ruby::XORer"
    cxx_header = "mem/ruby/structures/mystructures/XORer.hh"

    block_size = Param.MemorySize(
        "0B", "block size in bytes. 0 means default RubyBlockSize"
    )

    ruby_system = Param.RubySystem(Parent.any, "")
