#include "mem/ruby/structures/mystructures/msi/LSHComputer.hh"

#include "base/compiler.hh"
#include "base/intmath.hh"
#include "base/logging.hh"
#include "base/random.hh"
#include "debug/RubyLSHComputer.hh"
#include "mem/ruby/system/RubySystem.hh"

#include <iostream>

namespace gem5
{

namespace ruby
{

std::ostream&
operator<<(std::ostream& out, const LSHComputer& obj)
{
    obj.print(out);
    out << std::flush;
    return out;
}

LSHComputer::LSHComputer(const Params &p)
    : SimObject(p),
    lshComputerStats(this, pow(2, p.fingerprint_bits))
{
    m_fingerprint_bits = p.fingerprint_bits;
    std::cout << "hash hash! From a LSHComputer! map bits=" << m_fingerprint_bits << std::endl;
    m_block_size = p.block_size;  // may be 0 at this point. Updated in init()
    m_basetable_start_addr = p.basetable_start_addr;
}

void
LSHComputer::init()
{
    if (m_block_size == 0) {
        m_block_size = RubySystem::getBlockSizeBytes();
    }
    gen_lsh_matrix();
}

void
LSHComputer::gen_lsh_matrix() {
    srand (12345);
    m_lsh_matrix.clear();
    for (int i = 0; i < m_fingerprint_bits; i++) {
        DPRINTF(RubyLSHComputer, "m_lsh_matrix[%d] = ", i);
        int *lsh_vector = new int[m_block_size];
        for (int j = 0; j < m_block_size; j++) {
            int random = rand() % 6;
            if (random == 0) {
                lsh_vector[j] = 1;
            } else if (random == 1) {
                lsh_vector[j] = -1;
            } else {
                lsh_vector[j] = 0;
            }
            DPRINTF(RubyLSHComputer, "%d ", lsh_vector[j]);
        }
        m_lsh_matrix.push_back(lsh_vector);
        DPRINTF(RubyLSHComputer, "\n");
    }
}

Addr
LSHComputer::castToAddr(uint64_t fingerprint) const
{
    return Addr(fingerprint);
}

LSHComputer::~LSHComputer()
{

    for (int i = 0; i < m_fingerprint_bits; i++) {
        delete[] m_lsh_matrix[i];
    }
    m_lsh_matrix.clear();
}
void
LSHComputer::print(std::ostream& out) const
{
    out << "LSHComputer dump: " << name() << std::endl;
}

int
LSHComputer::getNumberOfBins() const
{
    return pow(2, m_fingerprint_bits);
}

uint64_t
LSHComputer::peek_compute(DataBlock blk) const
{   
    // this implements thesaurus locality-sensitive hashing
    uint64_t result = 0;
    for (int i = 0; i < m_lsh_matrix.size(); i++) {
        int * lsh_vector = m_lsh_matrix[i];
        int sum = 0;
        for (int j = 0; j < m_block_size; j++) {
            uint8_t * chunk8bit = reinterpret_cast<uint8_t*>(blk.getDataMod(j));
            sum += lsh_vector[j] * (int)(chunk8bit[0]);
            DPRINTF(RubyLSHComputer, "  lsh_vector[%d]=%d, chunk8bit[%d]=%d, sum=%d\n", j, lsh_vector[j], j, chunk8bit[0], sum);
        }
        if (sum > 0) {
            result += 1 << i;
        }
        DPRINTF(RubyLSHComputer, "%dth result=%d\n", i, result);
    }
    DPRINTF(RubyLSHComputer, "peek_compute result=%d\n", result);
    result = result << 6; // shift left by 6 bits for 64 byte alignment
    DPRINTF(RubyLSHComputer, "after shift left by 6 result=%d\n", result);
    return result;
}

uint64_t
LSHComputer::compute(DataBlock blk)
{   
    lshComputerStats.numComp++;
    uint64_t result = peek_compute(blk);
    lshComputerStats.binLSH[result >> 6]++;
    return result;
}


Addr
LSHComputer::computeLSHBaseTableAddr(DataBlock blk) const
{
    uint64_t fingerprint = peek_compute(blk);
    return m_basetable_start_addr + (fingerprint * 128);
}


LSHComputer::
LSHComputerStats::LSHComputerStats(statistics::Group *parent, int num_bins)
    : statistics::Group(parent),
      ADD_STAT(numComp, "Number of LSH computation"),
      ADD_STAT(binLSH, "LSH bin distribution")
{
    numComp
        .flags(statistics::nozero);

    binLSH
        .init(num_bins)
        .flags(statistics::pdf | statistics::total | statistics::nozero);
}


} // namespace ruby
} // namespace gem5
