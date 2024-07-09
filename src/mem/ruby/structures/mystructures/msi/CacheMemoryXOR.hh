#ifndef __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_CACHEMEMORYXOR_HH__
#define __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_CACHEMEMORYXOR_HH__

#include "params/RubyCacheXOR.hh"
#include "mem/ruby/structures/mystructures/msi/CacheMemoryDecoupledTagData.hh"
#include "mem/ruby/common/MachineID.hh"
#include "enums/SearchScope.hh"
#include "enums/Enforce.hh"
#include "enums/RankCriteria.hh"

namespace gem5
{

namespace ruby
{

class CacheMemoryXOR : public CacheMemoryDecoupledTagData
{
  public:
    typedef RubyCacheXORParams Params;
    CacheMemoryXOR(const Params &p);
    ~CacheMemoryXOR();

    void init() override;

    bool shouldDoXOR(Addr address, MachineID requestingCore);
    bool shouldThisBlockDoXOR(AbstractCacheEntry* thisTag);

    void getFinalCandidates(std::vector<AbstractCacheEntry*> &candidates, Addr address, MachineID requestingCore);
    void populateAllCandidates(std::vector<AbstractCacheEntry*> &candidates, Addr address);
    void filterCandidates(std::vector<AbstractCacheEntry*> &candidates, Addr address, MachineID requestingCore);
    
    Addr probeXORPartner(Addr address, MachineID requestingCore);
    AbstractCacheEntry* rankFinalCandidates(std::vector<AbstractCacheEntry*> candidates);


    bool hasPartnerFromMap(Addr address) const;
    Addr getPartnerTagAddressFromMap(Addr address) const;

    // bool hasPartner(Addr address) const;
    // Addr getPartnerTagAddress(Addr address) const;

    void removePartnerFromMap(Addr address);
    void setXORed(Addr address);
    void clearXORed(Addr address);


    void linkToPartner(Addr address, Addr partnerAddr);
    void linkToPartner(Addr address, Addr partnerAddr, int data_size);
    void unlinkDataToTag(Addr address);
    void deallocateTagData(Addr address);

  protected:
    const enums::SearchScope m_search_scope;
    const enums::Enforce m_enforce;
    const enums::RankCriteria m_rank_criteria;
    std::vector<std::vector<bool> > m_xored;
    int m_valid_candidate_ct_threshold;

    std::unordered_map<Addr, Addr> map_partner_address;


    struct CacheMemoryXORStats : public statistics::Group
    {
        CacheMemoryXORStats(statistics::Group *parent);
        statistics::Distribution xor_candidate_ct;
        
    } cacheMemoryXORStats;
};

} // namespace ruby

} // namespace gem5
#endif