from m5.params import *
from m5.proxy import *
from m5.SimObject import SimObject


class RubyLSHComputer(SimObject):
    type = "RubyLSHComputer"
    cxx_class = "gem5::ruby::LSHComputer"
    cxx_header = "mem/ruby/structures/mystructures/msi/LSHComputer.hh"

    block_size = Param.MemorySize(
        "0B", "block size in bytes. 0 means default RubyBlockSize"
    )
    fingerprint_bits = Param.Int(12, "fingerprint bits")
    basetable_start_addr = Param.Addr(0x200000, "basetable start address")

    ruby_system = Param.RubySystem(Parent.any, "")