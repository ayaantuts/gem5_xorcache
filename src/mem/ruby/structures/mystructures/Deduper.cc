#include "mem/ruby/structures/mystructures/Deduper.hh"

#include "base/compiler.hh"
#include "base/intmath.hh"
#include "base/logging.hh"
#include "debug/RubyDeduper.hh"
#include "mem/ruby/system/RubySystem.hh"

#include <iostream>

namespace gem5
{

namespace ruby
{

std::ostream&
operator<<(std::ostream& out, const Deduper& obj)
{
    obj.print(out);
    out << std::flush;
    return out;
}

Deduper::Deduper(const Params &p)
    : SimObject(p),
    deduperStats(this)
{
    std::cout << "Dedup dedup! From a Deduper!" << std::endl;
    m_block_size = p.block_size;  // may be 0 at this point. Updated in init()
    m_compress_latency = p.CompressLatency;
    m_decompress_latency = p.DecompressLatency;
}

void
Deduper::init()
{
    if (m_block_size == 0) {
        m_block_size = RubySystem::getBlockSizeBytes();
    }
}

Deduper::~Deduper()
{
    
}

int
Deduper::peek_compress(DataBlock blk)
{
    DPRINTF(RubyDeduper, "peek_compress(blk) in Deduper\n");
    int comp_size = m_block_size;
    // DataBlock comp;

    // final
    DPRINTF(RubyDeduper, "size=%d\n", comp_size);
    return comp_size;
}

int
Deduper::compress(DataBlock blk) {
    deduperStats.numCompression++;
    int comp_size = Deduper::peek_compress(blk);
    if (comp_size < m_block_size) {
        deduperStats.numCompSuccess++;
    }
    else {
        DPRINTF(RubyDeduper, "unsuccessful blk:%s\n", blk);
    }
    return comp_size;
}

Cycles
Deduper::decompress() {
    deduperStats.numDecomp++;
    return m_decompress_latency;
}

uint32_t
Deduper::peek_hash(DataBlock blk) {
    int chunk_size = 4;
    int num_chunk = m_block_size / chunk_size;
    std::vector<uint32_t> chunks_ping;
    chunks_ping.resize(num_chunk, (uint32_t)0);
    for (int i = 0; i < num_chunk; i++) {
        uint32_t * chunk32 = reinterpret_cast<uint32_t*>(blk.getDataMod(i*chunk_size));
        uint32_t c = *chunk32;
        chunks_ping[i] = c;
        // std::cout << "          ping[" << i << "]" <<
        //     std::setw(2) << std::setfill('0') << std::hex << "0x" <<
        //     uint32_t(c)
        //     << " " << std::setfill(' ')<< std::dec << std::endl;
    }

    int num_level = 4;
    // std::cout << "  level 0"  << std::endl;
    DPRINTF(RubyDeduper, "  level 0\n");
    std::vector<uint32_t> chunks_pang; //smaller
    // std::cout << "  resizing pang to be " << num_chunk/2 << std::endl;
    DPRINTF(RubyDeduper, "  resizing pang to be %d\n",num_chunk/2);
    chunks_pang.resize(num_chunk/2, (uint32_t)0);
    for(int j = 0; j < num_chunk/2; j++) {
        chunks_pang[j] = chunks_ping[j] ^ chunks_ping[j+num_chunk/2];
        // std::cout << "          pang[" << j << "]" <<
        //     std::setw(2) << std::setfill('0') << std::hex << "0x" <<
        //     uint32_t(chunks_pang[j])
        //     << " " << std::setfill(' ')<< std::dec << std::endl;
    }

    for (int i = 1; i < num_level; i++) {
        // std::cout << "  level " << i << std::endl;
        DPRINTF(RubyDeduper, "    level %d\n",i);
        // resizing larger's size
        int length_large = std::max(chunks_pang.size(), chunks_ping.size());
        int length_small = std::min(chunks_pang.size(), chunks_ping.size());
        assert(length_small == length_large/2);
        int size_new = length_small/2;
        if (length_large == chunks_pang.size()) {
            // std::cout << "  resizing pang to be " << size_new << std::endl;
            DPRINTF(RubyDeduper, "  resizing pang to be %d\n",size_new);
            chunks_pang.resize(size_new, (uint32_t)0);
            for(int j = 0; j < size_new; j++) {
                chunks_pang[j] = chunks_ping[j] ^ chunks_ping[j+length_small/2];
                // std::cout << "          pang[" << j << "]" <<
                //     std::setw(2) << std::setfill('0') << std::hex << "0x" <<
                //     uint32_t(chunks_pang[j])
                //     << " " << std::setfill(' ')<< std::dec 
                //     << "{" << j+length_small/2 << "}"
                //     << std::endl;
            }
        }
        else {
            // std::cout << "  resizing ping to be " << size_new << std::endl;
            DPRINTF(RubyDeduper, "  resizing ping to be %d\n",size_new);
            chunks_ping.resize(size_new, (uint32_t)0);
            for(int j = 0; j < size_new; j++) {
                chunks_ping[j] = chunks_pang[j] ^ chunks_pang[j+length_small/2];
                // std::cout << "          ping[" << j << "]" <<
                //     std::setw(2) << std::setfill('0') << std::hex << "0x" <<
                //     uint32_t(chunks_ping[j])
                //     << " " << std::setfill(' ')<< std::dec 
                //     << "{" << j+length_small/2 << "}"
                //     << std::endl;
            }
        }
    }

    int length_small = std::min(chunks_pang.size(), chunks_ping.size());
    uint32_t ret = 0;
    assert(length_small == 1);
    assert(std::max(chunks_pang.size(), chunks_ping.size()) == 2);
    if (length_small == chunks_pang.size()) {
        chunks_ping.clear();
        ret = chunks_pang[0];
        chunks_pang.clear();
    } else {
        chunks_pang.clear();
        ret = chunks_ping[0];
        chunks_ping.clear();
    }
    // std::cout << "  outcome=" <<
    //     std::setw(2) << std::setfill('0') << std::hex << "0x" <<
    //     uint32_t(ret)
    //     << " " << std::setfill(' ')<< std::dec << std::endl;
    return ret;
}

uint32_t
Deduper::hash(DataBlock blk) {
    deduperStats.numHash++;
    uint32_t hash = Deduper::peek_hash(blk);
    return hash;
}

bool
Deduper::isDataMatch(DataBlock blk1, DataBlock blk2) {
    return blk1.equal(blk2);
}

void
Deduper::print(std::ostream& out) const
{
    out << "Deduper dump: " << name() << std::endl;
    
}

Deduper::
DeduperStats::DeduperStats(statistics::Group *parent)
    : statistics::Group(parent),
      ADD_STAT(numHash, "Number of hashing"),
      ADD_STAT(numCompression, "Number of compression"),
      ADD_STAT(numCompSuccess, "Number of successful compression"),
      ADD_STAT(numDecomp, "Number of decompression")
{
    numHash
        .flags(statistics::nozero);

    numCompression
        .flags(statistics::nozero);

    numCompSuccess
        .flags(statistics::nozero);

    numDecomp
        .flags(statistics::nozero);
}

} // namespace ruby
} // namespace gem5
