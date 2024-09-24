#include "mem/ruby/structures/mystructures/msi/DataProc.hh"

#include "base/compiler.hh"
#include "base/intmath.hh"
#include "base/logging.hh"
#include "debug/RubyDataProc.hh"
#include "mem/ruby/system/RubySystem.hh"

#include <iostream>

namespace gem5
{

namespace ruby
{

std::ostream&
operator<<(std::ostream& out, const DataProc& obj)
{
    obj.print(out);
    out << std::flush;
    return out;
}

DataProc::DataProc(const Params &p)
    : SimObject(p),
    m_preproc(p.preprocessing),
    m_compress(p.compress),
    dataProcStats(this)
{
    m_block_size = p.block_size;  // may be 0 at this point. Updated in init()
    m_compress_latency = p.CompressLatency;
    if (m_compress == enums::no_compress) {
        m_decompress_latency = Cycles(0);
    } else {
        m_decompress_latency = p.DecompressLatency;
    }
    std::cout << "Comp comp! From a DataProc! "<< p.preprocessing << "," << p.compress << "(decompress lat=" <<
        m_decompress_latency << ")" << std::endl;
    m_preproc_latency = p.PreprocLatency;
    m_rev_preproc_latency = p.ReversePreprocLatency;
    m_segment_size_in_byte = p.segment_size_in_byte;
    m_tagptr_size_in_bit = p.tagptr_size_in_bit;
}

void
DataProc::init()
{
    if (m_block_size == 0) {
        m_block_size = RubySystem::getBlockSizeBytes();
    }
    m_tagptr_size_in_byte = divCeil(m_tagptr_size_in_bit, 8);
}

DataProc::~DataProc()
{
}
// =========== Compression ===========


int 
DataProc::peek_compress_intra_bdi(DataBlock blk)
{
    DPRINTF(RubyDataProc, "peek_compress(blk) in Compressor\n");
    int comp_size = m_block_size;

    if (is_compressible_zero(blk)) {
        comp_size = 1;
        DPRINTF(RubyDataProc, "size=%d\n", comp_size);
        return comp_size;
    }

    if (is_compressible_repeatByte(blk)) {
        comp_size = 8;
        DPRINTF(RubyDataProc, "size=%d\n", comp_size);
        return comp_size;
    }

    if (is_compressible_bdi<int64_t>(blk, 8, 1)) {
        comp_size = 8 + m_block_size/8*1 + m_block_size/8/8;
        DPRINTF(RubyDataProc, "size=%d\n", comp_size);
        return comp_size;
    }
    if (is_compressible_bdi<int32_t>(blk, 4, 1)) {
        comp_size = 4 + m_block_size/4*1 + m_block_size/4/8;
        DPRINTF(RubyDataProc, "size=%d\n", comp_size);
        return comp_size;
    }
    if (is_compressible_bdi<int64_t>(blk, 8, 2)) {
        comp_size = 8 + m_block_size/8*2 + m_block_size/8/8;
        DPRINTF(RubyDataProc, "size=%d\n", comp_size);
        return comp_size;
    }
    if (is_compressible_bdi<int16_t>(blk, 2, 1)) {
        comp_size = 2 + m_block_size/2*1 + m_block_size/2/8;
        DPRINTF(RubyDataProc, "size=%d\n", comp_size);
        return comp_size;
    }
    if (is_compressible_bdi<int32_t>(blk, 4, 2)) {
        comp_size = 4 + m_block_size/4*2 + m_block_size/4/8;
        DPRINTF(RubyDataProc, "size=%d\n", comp_size);
        return comp_size;
    }
    if (is_compressible_bdi<int64_t>(blk, 8, 4)) {
        comp_size = 8 + m_block_size/8*4 + m_block_size/8/8;
        DPRINTF(RubyDataProc, "size=%d\n", comp_size);
        return comp_size;
    }

    DPRINTF(RubyDataProc, "size=%d\n", comp_size);
    return comp_size;
}


// returns the idealistic compressed size in byte, ignoring the actual segment size
int
DataProc::peek_compress_intra(DataBlock blk)
{
    DPRINTF(RubyDataProc, "peek_compress_intra(blk) in DataProc\n");
    int comp_size = m_block_size;
    // DataBlock comp;

    if (m_compress == enums::bdi) {
        comp_size = peek_compress_intra_bdi(blk);
    }
    else if (m_compress == enums::no_compress) {
        comp_size = m_block_size;
    }
    else {
        panic("unknown compression type\n");
    }

    // final
    DPRINTF(RubyDataProc, "size=%d\n", comp_size);
    return comp_size;
}

int
DataProc::peek_compress_inter(DataBlock blk, DataBlock ref) 
{
    DPRINTF(RubyDataProc, "peek_compress_inter(blk,ref) in DataProc\n");
    int comp_size = m_block_size;

    if (m_compress == enums::thesaurus) {
        int diff_byte = 0;
        uint64_t diff_mask = 0;
        bool ref_all_zero = true;
        for (int i = 0; i < m_block_size; i++) {
            uint8_t * chunk8_this = reinterpret_cast<uint8_t*>(blk.getDataMod(i));
            uint8_t * chunk8_ref = reinterpret_cast<uint8_t*>(ref.getDataMod(i));
            if (chunk8_this[0] != chunk8_ref[0]) {
                diff_byte++;
                diff_mask |= 1 << i;
            }
            if (chunk8_ref[0] != 0) {
                ref_all_zero = false;
            }
        }
        DPRINTF(RubyDataProc, "diff_byte=%d, ref_all_zero=%d\n", diff_byte, ref_all_zero);
        if (diff_byte == 0) {
            comp_size = 0;
        } else {
            comp_size = 8 + diff_byte;
        }
    }
    else {
        panic("unknown compression type\n");
    }

    // final
    DPRINTF(RubyDataProc, "size=%d\n", comp_size);
    return comp_size;
}

int
DataProc::peek_compress(DataBlock blk)
{
    return peek_compress_intra(blk);
}

int
DataProc::peek_compress(DataBlock blk, DataBlock ref) 
{
    return peek_compress_inter(blk, ref);
}


// returns the realistic compressed size in byte, taking into account the actual segment size
int
DataProc::compress(DataBlock blk) {
    if (m_compress == enums::no_compress) {
        return m_block_size;
    } else {
        if (m_compress == enums::bdi) {
            dataProcStats.numCompressionIntra++;
            int comp_size_bytes = DataProc::peek_compress_intra(blk);
            dataProcStats.compSizeinByte.sample(comp_size_bytes);

            int comp_size_bytes_plus_tagptr = comp_size_bytes + m_tagptr_size_in_byte;
            dataProcStats.compSizeinByteTagptr.sample(comp_size_bytes_plus_tagptr);

            int num_seg = divCeil(comp_size_bytes_plus_tagptr, m_segment_size_in_byte);
            int comp_size_bytes_real = num_seg * m_segment_size_in_byte;
            dataProcStats.compSizeinByteReal.sample(comp_size_bytes_real);

            if (comp_size_bytes_real < m_block_size) {
                dataProcStats.numCompIntraSuccess++;
            }
            else {
                DPRINTF(RubyDataProc, "unsuccessful blk:%s\n", blk);
            }
            return comp_size_bytes_real;
        }
        else {
            panic("unknown compression type\n");
        }
    }
}
// returns the realistic compressed size in byte, taking into account the actual segment size
int
DataProc::compress(DataBlock blk, DataBlock ref) {
    if (m_compress == enums::no_compress) {
        return m_block_size;
    } else {
        if (m_compress == enums::thesaurus) {
            dataProcStats.numCompressionInter++;
            int comp_size_bytes = DataProc::peek_compress_inter(blk, ref);
            dataProcStats.compSizeinByte.sample(comp_size_bytes);

            int comp_size_bytes_plus_tagptr = comp_size_bytes + m_tagptr_size_in_byte;
            dataProcStats.compSizeinByteTagptr.sample(comp_size_bytes_plus_tagptr);

            int num_seg = divCeil(comp_size_bytes_plus_tagptr, m_segment_size_in_byte);
            int comp_size_bytes_real = num_seg * m_segment_size_in_byte;
            dataProcStats.compSizeinByteReal.sample(comp_size_bytes_real);

            if (comp_size_bytes_real < m_block_size) {
                dataProcStats.numCompInterSuccess++;
            }
            else {
                DPRINTF(RubyDataProc, "unsuccessful blk:%s\n", blk);
            }
            return comp_size_bytes_real;
        }
        else {
            panic("unknown compression type\n");
        }
    }
}

Cycles
DataProc::decompress() {
    if (m_compress != enums::no_compress) {
        dataProcStats.numDecomp++;
        return m_decompress_latency;
    } else {
        return Cycles(0);
    }
}

Cycles
DataProc::reverse_proc() {
    if (m_preproc != enums::no_preproc) {
        dataProcStats.numReverseProc++;
        return m_rev_preproc_latency;
    } else {
        return Cycles(0);
    }
}

int
DataProc::get_min_achieveable_size()const
{
    if (m_compress != enums::no_compress) {
        return m_segment_size_in_byte;
    } else {
        return m_block_size;
    }
}

bool
DataProc::is_compressible_zero(DataBlock blk) const
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
DataProc::is_compressible_repeatByte(DataBlock blk) const
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
DataProc::int_fall_into_range(T int_num, int test_bit_width) const
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
DataProc::is_compressible_bdi(DataBlock blk, int base_size, int delta_size) const
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



// =========== Preprocessing ===========
DataBlock
DataProc::preprocess(DataBlock blk1, DataBlock blk2) 
{
    if (m_preproc != enums::no_preproc) {
        dataProcStats.numPreproc++;
        DataBlock res = DataProc::peek_preproc(blk1, blk2);
        profilePreproc(res);
        return res;
    }
    return blk1;
}

DataBlock
DataProc::peek_preproc(DataBlock blk1, DataBlock blk2) 
{
    if (m_preproc == enums::xor_preproc) {
        DataBlock xor_result = DataBlock();

        int base = 1;
        for (int i = 0; i < m_block_size/base; i++) {
            uint8_t * chunk8_new = reinterpret_cast<uint8_t*>(blk1.getDataMod(i*base));
            uint8_t * chunk8_old = reinterpret_cast<uint8_t*>(blk2.getDataMod(i*base));
            uint8_t chunck8_xor_result = uint8_t(chunk8_new[0])^uint8_t(chunk8_old[0]);
            // DPRINTF(RubyDataProc, " 1B: 0x%llx ^ 0x%llx = 0x%llx\n", chunk8_new[0], chunk8_old[0], chunck8_xor_result);
            // DPRINTF(RubyDataProc, " 1B: 0x%llx\n", chunck8_xor_result);
            xor_result.setData(&chunck8_xor_result,i,1);
        }
        // DPRINTF(RubyDataProc, "xor_result:%s\n", xor_result);
        return xor_result;
    } else {
        panic("unknown preprocessing type\n");
    }
}

void
DataProc::profilePreproc(DataBlock preprocResult)
{
    // do nothing
}

// =========== Other ===========
void
DataProc::print(std::ostream& out) const
{
    out << "DataProc dump: " << name() << std::endl;
    
}

DataProc::
DataProcStats::DataProcStats(statistics::Group *parent)
    : statistics::Group(parent),
      ADD_STAT(numCompressionIntra, "Number of intra compression"),
      ADD_STAT(numCompressionInter, "Number of inter compression"),
      ADD_STAT(numCompIntraSuccess, "Number of intra successful compression"),
      ADD_STAT(numCompInterSuccess, "Number of inter successful compression"),
      ADD_STAT(numDecomp, "Number of decompression"),
      ADD_STAT(numReverseProc, "Number of reverse preprocessing"),
      ADD_STAT(compSizeinByte, "Compression size distribution"),
      ADD_STAT(compSizeinByteTagptr, "Compression size distribution, considering tag ptr"),
      ADD_STAT(compSizeinByteReal, "Compression size distribution, considering segment size and tag ptr"),
      ADD_STAT(numPreproc, "Number of preprocessing"),
      ADD_STAT(numRevPreproc, "Number of rev preprocessing")
{
    numCompressionIntra
        .flags(statistics::nozero);

    numCompressionInter
        .flags(statistics::nozero);

    numCompIntraSuccess
        .flags(statistics::nozero);

    numCompInterSuccess
        .flags(statistics::nozero);

    numDecomp
        .flags(statistics::nozero);
    
    numReverseProc
        .flags(statistics::nozero);
    
    compSizeinByte
        .init(16)
        .flags(statistics::pdf | statistics::nozero | statistics::nonan);
    
    compSizeinByteTagptr
        .init(16)
        .flags(statistics::pdf | statistics::nozero | statistics::nonan);
    
    compSizeinByteReal
        .init(16)
        .flags(statistics::pdf | statistics::nozero | statistics::nonan);

    numPreproc
        .flags(statistics::nozero);
    
    numRevPreproc
        .flags(statistics::nozero);
}

} // namespace ruby
} // namespace gem5
