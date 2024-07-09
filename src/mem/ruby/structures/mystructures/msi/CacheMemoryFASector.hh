#ifndef __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_CACHEMEMORYFASECTOR_HH__
#define __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_CACHEMEMORYFASECTOR_HH__

#include "params/RubyCacheFASector.hh"
#include "mem/ruby/structures/CacheMemory.hh"

//CacheMemoryFASector is fully associative cache with sector granularity

namespace gem5
{

namespace ruby
{

class CacheMemoryFASector : public CacheMemory
{
  public:
    typedef RubyCacheFASectorParams Params;
    CacheMemoryFASector(const Params &p);
    ~CacheMemoryFASector();

    void init() override;


    AbstractCacheEntry* allocate(Addr address, AbstractCacheEntry* new_entry);
    AbstractCacheEntry* allocate(Addr address, AbstractCacheEntry* new_entry, int size);
    void deallocate(Addr address);

    // original_addr should be in cache, just change its address to new_addr without
    // touching replacement policy nor changing the size
    void changeAddr(Addr original_addr, Addr new_addr);

    Addr candidateProbe(Addr address) const;
    int candidateCount(Addr address) const;

    // Returns true if there is:
    //   a) a tag match on this address or there is
    //   b) an unused **space** in the same cache "way"
    bool cacheAvail(Addr address, int sizes) const;
    bool cacheAvail(Addr address) const;
    bool cacheFull() const;

    void updateDataSize(Addr address, int size);
    int getDataSize(Addr address) const;
    
    void calculateStatAtEnd();

    float getUtilByte() const
    {
      return (float) cacheMemoryFASectorStats.numByteInUse.value() / (m_cache_num_sets * m_cache_assoc) * 100;
    }

  protected:
    int m_num_bytes_in_use;
    std::unordered_map<Addr, int> m_size_map;
    int m_full_percentage;

    struct CacheMemoryFASectorStats : public statistics::Group
    {
        CacheMemoryFASectorStats(statistics::Group *parent);
        statistics::Average numByteInUse;
        statistics::Scalar numDataContraction;
        statistics::Scalar numDataExpansion;
        statistics::Scalar util_byte;
        statistics::Scalar compression_ratio_intra;


    } cacheMemoryFASectorStats;
};

} // namespace ruby

} // namespace gem5
#endif