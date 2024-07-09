#ifndef __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_DIRECTMAPPEDHASHTABLE_HH__
#define __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_DIRECTMAPPEDHASHTABLE_HH__

#include "base/statistics.hh"
#include "params/RubyDirectMappedHashTable.hh"
#include "mem/ruby/common/DataBlock.hh"
#include "sim/sim_object.hh"
// #include "enums/Compress.hh"
#include <queue>
namespace gem5
{

namespace ruby
{

class DirectMappedHashTable : public SimObject
{
  public:
    typedef RubyDirectMappedHashTableParams Params;
    DirectMappedHashTable(const Params &p);
    ~DirectMappedHashTable();

    void init();
    void print(std::ostream& out) const;
    int getNumberOfBins() const;

  protected:
    int m_block_size;
    uint64_t blockToMap(DataBlock blk) const;

  private:
    int m_fingerprint_bits;
    std::vector<Addr> m_hash_table;
    std::vector<int *> lsh_matrix;

    struct DirectMappedHashTableStats : public statistics::Group
    {
        DirectMappedHashTableStats(statistics::Group *parent, int numBins);
    } directMappedHashTableStats;
};

std::ostream& operator<<(std::ostream& out, const DirectMappedHashTable& obj);

} // namespace ruby

} // namespace gem5
#endif