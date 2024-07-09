#include "debug/RubyCacheProbe.hh"
#include "mem/ruby/structures/mystructures/msi/CacheMemoryProbe.hh"
#include "mem/ruby/system/RubySystem.hh"

#include <iostream>

namespace gem5
{

namespace ruby
{

CacheMemoryProbe::CacheMemoryProbe(const Params &p)
    : CacheMemory(p),
    cacheMemoryProbeStats(this)
{
    m_valid_candidate_ct_threshold = p.valid_candidate_ct_threshold;
}

void
CacheMemoryProbe::init()
{
    CacheMemory::init();
    std::cout << "Hello World! From a CacheMemoryProbe! "<< std::endl;
}

CacheMemoryProbe::~CacheMemoryProbe()
{
}

// rewriting the cacheProbe function
Addr
CacheMemoryProbe::candidateProbe(Addr address) const
{
    assert(address == makeLineAddress(address));
    // assert(!cacheAvail(address)); // we are using this function to probe 
    // the xor candidate so we dont need this check

    int64_t cacheSet = addressToCacheSet(address);
    std::vector<ReplaceableEntry*> candidates;
    for (int i = 0; i < m_cache_assoc; i++) {
        if (m_cache[cacheSet][i] != nullptr) {
            candidates.push_back(static_cast<ReplaceableEntry*>(
                                                        m_cache[cacheSet][i]));
        }
    }
    return m_cache[cacheSet][m_replacementPolicy_ptr->
                        getVictim(candidates)->getWay()]->m_Address;
}

int
CacheMemoryProbe::candidateCount(Addr address) const
{
    assert(address == makeLineAddress(address));

    int64_t cacheSet = addressToCacheSet(address);
    std::vector<ReplaceableEntry*> candidates;
    for (int i = 0; i < m_cache_assoc; i++) {
        if (m_cache[cacheSet][i] != nullptr) {
            candidates.push_back(static_cast<ReplaceableEntry*>(
                                                        m_cache[cacheSet][i]));
        }
    }
    return (candidates.size());
}

int 
CacheMemoryProbe::getCandidateCtThreshold() const
{
    return m_valid_candidate_ct_threshold;
}


CacheMemoryProbe::
CacheMemoryProbeStats::CacheMemoryProbeStats(statistics::Group *parent)
    : statistics::Group(parent)
{
    
}

}
}