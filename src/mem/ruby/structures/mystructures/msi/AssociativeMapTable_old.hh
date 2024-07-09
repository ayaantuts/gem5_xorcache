#ifndef __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_ASSOCIATIVEMAPTABLE_HH__
#define __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_ASSOCIATIVEMAPTABLE_HH__

#include "base/statistics.hh"
#include "params/RubyAssociativeMapTable.hh"
#include "mem/ruby/common/DataBlock.hh"
#include "mem/cache/replacement_policies/base.hh"
#include "mem/cache/replacement_policies/replaceable_entry.hh"
#include "sim/sim_object.hh"
#include "enums/XOR_Policy.hh"
#include <queue>
namespace gem5
{

namespace ruby
{

class AssociativeMapTable : public SimObject
{
  public:
    typedef RubyAssociativeMapTableParams Params;
    AssociativeMapTable(const Params &p);
    ~AssociativeMapTable();

    void init();
    void print(std::ostream& out) const;

    bool isXORPolicyBalanced() const { return m_xor_policy == enums::XOR_Policy::balanced; }
    bool isXORPolicySynergy() const { return m_xor_policy == enums::XOR_Policy::synergy; }
    bool isXORPolicyOppurtunistic() const { return m_xor_policy == enums::XOR_Policy::oppurtunistic; }

    int getNumberOfBins() const;
    int64_t mapToSet(uint64_t hash) const;

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
    int m_num_sets;
    int m_assoc;
    bool m_regular_xor_folding;
    enums::XOR_Policy m_xor_policy;
    std::vector<std::vector<Addr>> m_map_table;
    std::vector<std::vector<bool>> m_valid;
    std::unordered_map<uint64_t, int> m_hash_way_map; //maps hash to way
    std::vector<std::vector<ReplData> > replacement_data;
    replacement_policy::Base *m_replacementPolicy_ptr;
    std::unordered_map<Addr, uint64_t> m_uomap; // maps addr to hash
    int m_num_set_bits;
    int m_start_index_bit=0;

    struct AssociativeMapTableStats : public statistics::Group
    {
        AssociativeMapTableStats(statistics::Group *parent, int numBins);
        statistics::Average numInUse;
        statistics::Scalar numMapCollisionXOR;
        statistics::Scalar numMapRandomXOR;
        statistics::Scalar numAddrUpdate;
        statistics::Scalar m_read;
        statistics::Scalar m_write;
        statistics::Scalar hashValueReplacement;
    } associativeMapTableStats;
};

std::ostream& operator<<(std::ostream& out, const AssociativeMapTable& obj);

} // namespace ruby

} // namespace gem5
#endif