#ifndef __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_DIRECTMAPTABLE_HH__
#define __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_DIRECTMAPTABLE_HH__

#include "base/statistics.hh"
#include "params/RubyDirectMapTable.hh"
#include "mem/ruby/common/DataBlock.hh"
#include "sim/sim_object.hh"
#include "enums/XOR_Policy.hh"
#include <queue>
namespace gem5
{

namespace ruby
{

class DirectMapTable : public SimObject
{
  public:
    typedef RubyDirectMapTableParams Params;
    DirectMapTable(const Params &p);
    ~DirectMapTable();

    void init();
    void print(std::ostream& out) const;

    bool isXORPolicyBalanced() const { return m_xor_policy == enums::XOR_Policy::balanced; }
    bool isXORPolicySynergy() const { return m_xor_policy == enums::XOR_Policy::synergy; }
    bool isXORPolicyOppurtunistic() const { return m_xor_policy == enums::XOR_Policy::oppurtunistic; }

    int getNumberOfBins() const;
    void insert(Addr addr, DataBlock blk);
    void insert_map(Addr addr, uint64_t map);
    void remove(Addr addr);
    uint64_t remove_return(Addr addr);

    bool hasRegisteredCandidate(DataBlock blk) const;
    Addr getRandomRegisteredCandidate(DataBlock blk) ;

    bool hasAnyRegisteredCandidate() const;
    Addr getAnyRandomRegisteredCandidate();

    int getAnyRegisteredCandidateCt() const;
    int getRegisteredCandidateCt(DataBlock blk) const;

    bool isCandidate(Addr addr) const;
    
    void profileRead();
    void profileWrite();

  protected:
    int m_block_size;
    uint64_t blockToMap(DataBlock blk) const;

  private:
    int m_map_bits;
    int m_list_capacity;
    int m_xor_folding_scheme;
    enums::XOR_Policy m_xor_policy;
    std::vector<std::queue<Addr> > m_map_table;
    std::unordered_map<Addr, int> m_uomap;

    struct DirectMapTableStats : public statistics::Group
    {
        DirectMapTableStats(statistics::Group *parent, int numBins);
        statistics::Vector numMaxCapcityReached;
        statistics::AverageVector listCapacityInUse;
        statistics::Scalar numMapCollisionXOR;
        statistics::Scalar numMapRandomXOR;
        statistics::Scalar m_read;
        statistics::Scalar m_write;
    } directMapTableStats;
};

std::ostream& operator<<(std::ostream& out, const DirectMapTable& obj);

} // namespace ruby

} // namespace gem5
#endif