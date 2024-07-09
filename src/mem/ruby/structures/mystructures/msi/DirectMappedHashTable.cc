#include "mem/ruby/structures/mystructures/msi/DirectMappedHashTable.hh"

#include "base/compiler.hh"
#include "base/intmath.hh"
#include "base/logging.hh"
#include "base/random.hh"
#include "debug/RubyDirectMappedHashTable.hh"
#include "mem/ruby/system/RubySystem.hh"

#include <iostream>

namespace gem5
{

namespace ruby
{

std::ostream&
operator<<(std::ostream& out, const DirectMappedHashTable& obj)
{
    obj.print(out);
    out << std::flush;
    return out;
}

DirectMappedHashTable::DirectMappedHashTable(const Params &p)
    : SimObject(p),
    directMapTableStats(this, pow(2, p.fingerprint_bits))
{
    m_fingerprint_bits = p.fingerprint_bits;
    std::cout << "hash hash! From a DirectMappedHashTable! map bits=" << m_fingerprint_bits << std::endl;
    m_block_size = p.block_size;  // may be 0 at this point. Updated in init()
}

void
DirectMappedHashTable::init()
{
    if (m_block_size == 0) {
        m_block_size = RubySystem::getBlockSizeBytes();
    }
    m_hash_table.clear();
    gen_lsh_matrix();
}

void
DirectMappedHashTable::gen_lsh_matrix() {
    srand (12345);
    m_lsh_matrix.clear();
    for (int i = 0; i < m_fingerprint_bits; i++) {
        DPRINTF(RubyDirectMappedHashTable, "m_lsh_matrix[%d] = ", i);
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
            DPRINTF(RubyDirectMappedHashTable, "%d ", lsh_vector[j]);
        }
        m_lsh_matrix.push_back(lsh_vector);
        DPRINTF(RubyDirectMappedHashTable, "\n");
    }
}

DirectMappedHashTable::~DirectMappedHashTable()
{
    m_hash_table.clear();

    for (int i = 0; i < m_fingerprint_bits; i++) {
        delete[] m_lsh_matrix[i];
    }
    m_lsh_matrix.clear();
}
void
DirectMappedHashTable::print(std::ostream& out) const
{
    out << "DirectMappedHashTable dump: " << name() << std::endl;
}

int
DirectMappedHashTable::getNumberOfBins() const
{
    return pow(2, m_fingerprint_bits);
}

uint64_t
DirectMappedHashTable::blockToMap(DataBlock blk) const
{   
    // this implements thesaurus locality-sensitive hashing
    uint64_t result = 0;
    for (int i = 0; i < lsh_matrix.size(); i++) {
        int * lsh_vector = lsh_matrix[i];
        int sum = 0;
        for (int j = 0; j < m_block_size; j++) {
            uint8_t * chunk8bit = reinterpret_cast<uint8_t*>(blk.getDataMod(j));
            sum += lsh_vector[j] * (int)(chunk8bit[0]);
        }
        if (sum > 0) {
            result += 1 << i;
        }
    }
    return result;
}



DirectMappedHashTable::
DirectMappedHashTableStats::DirectMappedHashTableStats(statistics::Group *parent, int num_bins)
    : statistics::Group(parent)
{
}


} // namespace ruby
} // namespace gem5
