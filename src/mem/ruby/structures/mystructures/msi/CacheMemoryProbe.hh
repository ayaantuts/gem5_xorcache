#ifndef __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_CACHEMEMORYPROBE_HH__
#define __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_CACHEMEMORYPROBE_HH__

#include "params/RubyCacheProbe.hh"
#include "mem/ruby/structures/CacheMemory.hh"

namespace gem5
{

namespace ruby
{

class CacheMemoryProbe : public CacheMemory
{
  public:
    typedef RubyCacheProbeParams Params;
    CacheMemoryProbe(const Params &p);
    ~CacheMemoryProbe();

    void init() override;

    int candidateCount(Addr address) const;
    Addr candidateProbe(Addr address) const;
    int getCandidateCtThreshold() const;
    

  protected:
    int m_valid_candidate_ct_threshold;
    struct CacheMemoryProbeStats : public statistics::Group
    {
        CacheMemoryProbeStats(statistics::Group *parent);

    } cacheMemoryProbeStats;
};

} // namespace ruby

} // namespace gem5
#endif