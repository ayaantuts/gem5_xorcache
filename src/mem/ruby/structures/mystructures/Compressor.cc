#include "mem/ruby/structures/mystructures/Compressor.hh"

#include "base/compiler.hh"
#include "base/intmath.hh"
#include "base/logging.hh"
#include "debug/RubyCompressor.hh"
#include "mem/ruby/system/RubySystem.hh"

#include <iostream>

namespace gem5
{

namespace ruby
{

std::ostream&
operator<<(std::ostream& out, const Compressor& obj)
{
    obj.print(out);
    out << std::flush;
    return out;
}

Compressor::Compressor(const Params &p)
    : SimObject(p),
    compressorStats(this)
{
    std::cout << "Comp comp! From a Compressor!" << std::endl;
    m_block_size = p.block_size;  // may be 0 at this point. Updated in init()
    m_compress_latency = p.CompressLatency;
    m_decompress_latency = p.DecompressLatency;
}

void
Compressor::init()
{
    if (m_block_size == 0) {
        m_block_size = RubySystem::getBlockSizeBytes();
    }
}

Compressor::~Compressor()
{
    
}

int
Compressor::peek_compress(DataBlock blk)
{
    DPRINTF(RubyCompressor, "peek_compress(blk) in Compressor\n");
    int comp_size = m_block_size;
    // DataBlock comp;

    // ======= zero =======
    DPRINTF(RubyCompressor, "  try zero....\n");
    bool zero = true;
    int base = 8;
    for (int i = 0; i < m_block_size/base; i++) {
        uint64_t * chunk64 = reinterpret_cast<uint64_t*>(blk.getDataMod(i*base));
        if (chunk64[0] != 0) {
            zero = false;
            break;
        }
    }
    if (zero == true) {
        comp_size = 1;
        DPRINTF(RubyCompressor, "size=%d\n", comp_size);
        return comp_size;
    }
    
    // ======= b8 =======
    DPRINTF(RubyCompressor, "  try b8/rep....\n");
    bool b8d1 = true;
    bool b8d2 = true;
    bool b8d4 = true;
    bool rep = true;
    base = 8;
    uint64_t* base_nonzero_64 = NULL;
    for (int i = 0; i < m_block_size/base; i++) {
        uint64_t * chunk64 = reinterpret_cast<uint64_t*>(blk.getDataMod(i*base));
        if (chunk64[0] <= std::numeric_limits<uint8_t>::max()) {
            // std::cout << "      immediate[" << i << "] "<<
            // std::setw(2) << std::setfill('0') << std::hex << "0x" <<
            // uint64_t(chunk64[0])
            // << " " << std::setfill(' ')<< std::dec << std::endl;
        }
        else {
            rep = false;
            if (base_nonzero_64 == NULL) {
                base_nonzero_64 = chunk64;
                // std::cout << "  base="<<
                // std::setw(2) << std::setfill('0') << std::hex << "0x" <<
                // uint64_t(base_nonzero_64[0])
                // << " " << std::setfill(' ')<< std::dec << std::endl;
            }
            uint64_t delta_i = uint64_t(chunk64[0])-uint64_t(base_nonzero_64[0]);
            // std::cout << "      delta[" << i << "] "<<
            //     std::setw(2) << std::setfill('0') << std::hex << "0x" <<
            //     uint64_t(delta_i)
            //     << " " << std::setfill(' ')<< std::dec << std::endl;
            if (delta_i > std::numeric_limits<uint8_t>::max()) {
                DPRINTF(RubyCompressor, "-> b8d1 failed.\n");
                b8d1 = false;
                if (delta_i > std::numeric_limits<uint16_t>::max()) {
                    DPRINTF(RubyCompressor, "-> b8d2 failed.\n");
                    b8d2 = false;
                    if (delta_i > std::numeric_limits<uint32_t>::max()) {
                        DPRINTF(RubyCompressor, "-> b8d4 failed.\n");
                        b8d4 = false;
                        break;
                    }
                }
            }

        }
    }
    if (rep == true) {
        comp_size = 8;
        DPRINTF(RubyCompressor, "size=%d\n",comp_size);
        return comp_size;
    }
    if (b8d1 == true) {
        int new_comp_size = base + m_block_size/base*1;
        if (new_comp_size < comp_size) {
            comp_size = new_comp_size;
        }
    }
    if (b8d2 == true) {
        int new_comp_size = base + m_block_size/base*2;
        if (new_comp_size < comp_size) {
            comp_size = new_comp_size;
        }
    }
    if (b8d4 == true) {
        int new_comp_size = base + m_block_size/base*4;
        if (new_comp_size < comp_size) {
            comp_size = new_comp_size;
        }
    }

    
    // ======= b4 =======
    DPRINTF(RubyCompressor, "  try b4....\n");
    bool b4d1 = true;
    bool b4d2 = true;
    base = 4;
    uint32_t * base_nonzero_32 = NULL;
    for (int i = 0; i < m_block_size/base; i++) {
        uint32_t * chunk32 = reinterpret_cast<uint32_t*>(blk.getDataMod(i*base));
        if (chunk32[0] <= std::numeric_limits<uint8_t>::max()) {
            // std::cout << "      immediate[" << i << "] "<<
            // std::setw(2) << std::setfill('0') << std::hex << "0x" <<
            // uint32_t(chunk32[0])
            // << " " << std::setfill(' ')<< std::dec << std::endl;
        }
        else {
            if (base_nonzero_32 == NULL) {
                base_nonzero_32 = chunk32;
                // std::cout << "  base="<<
                // std::setw(2) << std::setfill('0') << std::hex << "0x" <<
                // uint32_t(base_nonzero_32[0])
                // << " " << std::setfill(' ')<< std::dec << std::endl;
            }
            uint32_t delta_i = uint32_t(chunk32[0])-uint32_t(base_nonzero_32[0]);
            // std::cout << "      delta[" << i << "] "<<
            //     std::setw(2) << std::setfill('0') << std::hex << "0x" <<
            //     uint32_t(delta_i)
            //     << " " << std::setfill(' ')<< std::dec << std::endl;
            if (delta_i > std::numeric_limits<uint8_t>::max()) {
                DPRINTF(RubyCompressor, "-> b4d1 failed.\n");
                b4d1 = false;
                if (delta_i > std::numeric_limits<uint16_t>::max()) {
                    DPRINTF(RubyCompressor, "-> b4d2 failed.\n");
                    b4d2 = false;
                    break;
                }
            }

        }
    }
    if (b4d1 == true) {
        int new_comp_size = base + m_block_size/base*1;
        if (new_comp_size < comp_size) {
            comp_size = new_comp_size;
        }
    }
    if (b4d2 == true) {
        int new_comp_size = base + m_block_size/base*2;
        if (new_comp_size < comp_size) {
            comp_size = new_comp_size;
        }
    }

    // ======= b2 =======
    DPRINTF(RubyCompressor, "  try b2....\n");
    bool b2d1 = true;
    base = 2;
    uint16_t * base_nonzero_16 = NULL;
    for (int i = 0; i < m_block_size/base; i++) {
        uint16_t * chunk16 = reinterpret_cast<uint16_t*>(blk.getDataMod(i*base));
        if (chunk16[0] <= std::numeric_limits<uint8_t>::max()) {
            // std::cout << "      immediate[" << i << "] "<<
            // std::setw(2) << std::setfill('0') << std::hex << "0x" <<
            // uint16_t(chunk16[0])
            // << " " << std::setfill(' ')<< std::dec << std::endl;
        }
        else {
            if (base_nonzero_16 == NULL) {
                base_nonzero_16 = chunk16;
                // std::cout << "  base="<<
                // std::setw(2) << std::setfill('0') << std::hex << "0x" <<
                // uint16_t(base_nonzero_16[0])
                // << " " << std::setfill(' ')<< std::dec << std::endl;
            }
            uint16_t delta_i = uint16_t(chunk16[0])-uint16_t(base_nonzero_16[0]);
            // std::cout << "      delta[" << i << "] "<<
            //     std::setw(2) << std::setfill('0') << std::hex << "0x" <<
            //     uint16_t(delta_i)
            //     << " " << std::setfill(' ')<< std::dec << std::endl;
            if (delta_i > std::numeric_limits<uint8_t>::max()) {
                DPRINTF(RubyCompressor, "-> b2d1 failed.\n");
                b2d1 = false;
                break;
            }

        }
    }
    if (b2d1 == true) {
        int new_comp_size = base + m_block_size/base*1;
        if (new_comp_size < comp_size) {
            comp_size = new_comp_size;
        }
    }
    
    // final
    DPRINTF(RubyCompressor, "size=%d\n", comp_size);
    return comp_size;
}


int Compressor::peek_compress(DataBlock blk)
{
    DPRINTF(RubyCompressor, "peek_compress(blk) in Compressor\n");
    int comp_size = m_block_size;

    if (is_compressible_zero(blk)) {
        comp_size = 1;
        DPRINTF(RubyCompressor, "size=%d\n", comp_size);
        return comp_size;
    }

    if (is_compressible_repeatByte(blk)) {
        comp_size = 8;
        DPRINTF(RubyCompressor, "size=%d\n", comp_size);
        return comp_size;
    }

    if (is_compressible_bdi<int64_t>(blk, 8, 1)) {
        comp_size = 8 + m_block_size/8*1;
        DPRINTF(RubyCompressor, "size=%d\n", comp_size);
        return comp_size;
    }
    if (is_compressible_bdi<int32_t>(blk, 4, 1)) {
        comp_size = 4 + m_block_size/4*1;
        DPRINTF(RubyCompressor, "size=%d\n", comp_size);
        return comp_size;
    }
    if (is_compressible_bdi<int64_t>(blk, 8, 2)) {
        comp_size = 8 + m_block_size/8*2;
        DPRINTF(RubyCompressor, "size=%d\n", comp_size);
        return comp_size;
    }
    if (is_compressible_bdi<int16_t>(blk, 2, 1)) {
        comp_size = 2 + m_block_size/2*1;
        DPRINTF(RubyCompressor, "size=%d\n", comp_size);
        return comp_size;
    }
    if (is_compressible_bdi<int32_t>(blk, 4, 2)) {
        comp_size = 4 + m_block_size/4*2;
        DPRINTF(RubyCompressor, "size=%d\n", comp_size);
        return comp_size;
    }
    if (is_compressible_bdi<int64_t>(blk, 8, 4)) {
        comp_size = 8 + m_block_size/8*4;
        DPRINTF(RubyCompressor, "size=%d\n", comp_size);
        return comp_size;
    }

    DPRINTF(RubyCompressor, "size=%d\n", comp_size);
    return comp_size;
}

int
Compressor::compress(DataBlock blk) {
    compressorStats.numCompression++;
    int comp_size = Compressor::peek_compress(blk);
    compressorStats.compSizeinByte.sample(comp_size);

    if (comp_size < m_block_size) {
        compressorStats.numCompSuccess++;
    }
    else {
        DPRINTF(RubyCompressor, "unsuccessful blk:%s\n", blk);
    }
    return comp_size;
}

Cycles
Compressor::decompress() {
    compressorStats.numDecomp++;
    return m_decompress_latency;
}

int
Compressor::get_min_achieveable_size()const
{
    return 1;
}

bool
Compressor::is_compressible_zero(DataBlock blk) const
{
    for (int i = 0; i < m_block_size; i++) {
        uint8_t * byte = reinterpret_cast<uint8_t*>(blk.getDataMod(i));
        if (byte[0] != 0) {
            return false;
        }
    }
    return true;
}

bool
Compressor::is_compressible_repeatByte(DataBlock blk) const
{
    uint64_t * words = reinterpret_cast<uint64_t*>(blk.getDataMod(0));
    for (int i = 1; i < m_block_size/8; i++) {
        uint64_t word = words[i];
        if (word != words[0]) {
            return false;
        }
    }
    return true;
}

template<typename T>
bool
Compressor::int_fall_into_range(T int_num, int test_bit_width) const
{
    if (test_bit_width == 8) {
        return int_num <= INT8_MAX && int_num >= INT8_MIN;
    } else if (test_bit_width == 16) {
        return int_num <= INT16_MAX && int_num >= INT16_MIN;
    } else if (test_bit_width == 32) {
        return int_num <= INT32_MAX && int_num >= INT32_MIN;
    } else {
        assert(false);
        return false;
    }
}

template<typename T> bool
Compressor::is_compressible_bdi(DataBlock blk, int base_size, int delta_size) const
{
    int num_deltas = m_block_size / base_size;
    bool found_base = false;
    T base0;

    T* segs = reinterpret_cast<T*>(blk.getDataMod(0));
    for (int i = 0; i < num_deltas; i++) {
        T segment = segs[i];
        if (int_fall_into_range<T>(segment, delta_size*8)) {}
        else { // uncompressible with 0 base
            if (!found_base) {
                found_base = true;
                base0 = segment;
            }
            assert(found_base);
            T delta = segment - base0;
            if (int_fall_into_range<T>(delta, delta_size*8)) {}
            else {
                // uncompressible with selected base
                return false;
            }
        }
    }
    return true;
}



void
Compressor::print(std::ostream& out) const
{
    out << "Compressor dump: " << name() << std::endl;
    
}

Compressor::
CompressorStats::CompressorStats(statistics::Group *parent)
    : statistics::Group(parent),
      ADD_STAT(numCompression, "Number of compression"),
      ADD_STAT(numCompSuccess, "Number of successful compression"),
      ADD_STAT(numDecomp, "Number of decompression"),
      ADD_STAT(compSizeinByte, "Compression size distribution")
{
    numCompression
        .flags(statistics::nozero);

    numCompSuccess
        .flags(statistics::nozero);

    numDecomp
        .flags(statistics::nozero);
    
    compSizeinByte
        .init(16)
        .flags(statistics::pdf | statistics::nozero | statistics::nonan);
}

} // namespace ruby
} // namespace gem5
