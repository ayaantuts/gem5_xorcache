from m5.params import *
from m5.proxy import *
from m5.SimObject import SimObject


class Preproc(Enum):
    vals = ["no_preproc", "xor_preproc"]

class Compress(Enum):
    vals = ["no_compress", "bdi", "thesaurus"]

class RubyDataProc(SimObject):
    type = "RubyDataProc"
    cxx_class = "gem5::ruby::DataProc"
    cxx_header = "mem/ruby/structures/mystructures/msi/DataProc.hh"

    block_size = Param.MemorySize(
        "0B", "block size in bytes. 0 means default RubyBlockSize"
    )

    preprocessing = Param.Preproc("xor_preproc", "preprocessing method")
    compress = Param.Compress("no_compress", "compression method")

    PreprocLatency = Param.Cycles(1, "cycles for preprocessing")
    ReversePreprocLatency = Param.Cycles(1, "cycles for reverse preprocessing")
    CompressLatency = Param.Cycles(1, "cycles for compression")
    DecompressLatency = Param.Cycles(1, "cycles for decompression")
    segment_size_in_byte = Param.Int(8, "segment size in byte")
    tagptr_size_in_bit = Param.Int(15, "tagptr size in bit")

    ruby_system = Param.RubySystem(Parent.any, "")
