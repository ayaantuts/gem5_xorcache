from m5.params import *
from m5.proxy import *
from m5.SimObject import SimObject


class RubyCompressor(SimObject):
    type = "RubyCompressor"
    cxx_class = "gem5::ruby::Compressor"
    cxx_header = "mem/ruby/structures/mystructures/Compressor.hh"

    block_size = Param.MemorySize(
        "0B", "block size in bytes. 0 means default RubyBlockSize"
    )

    CompressLatency = Param.Cycles(1, "cycles for compression")
    DecompressLatency = Param.Cycles(1, "cycles for decompression")
    ruby_system = Param.RubySystem(Parent.any, "")
