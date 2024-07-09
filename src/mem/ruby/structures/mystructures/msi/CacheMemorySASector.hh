#ifndef __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_CACHEMEMORYSASECTOR_HH__
#define __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_CACHEMEMORYSASECTOR_HH__

#include "params/RubyCacheSASector.hh"
#include "mem/ruby/structures/CacheMemory.hh"

//CacheMemorySASector is fully associative cache with sector granularity

namespace gem5
{

namespace ruby
{

class CacheMemorySASector : public CacheMemory
{
  public:
    typedef RubyCacheSASectorParams Params;
    CacheMemorySASector(const Params &p);
    ~CacheMemorySASector();

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
      return (float) cacheMemorySASectorStats.numByteInUse.value() / (m_cache_num_sets * m_cache_assoc) * 100;
    }

  protected:
    int m_num_bytes_in_use;
    std::unordered_map<Addr, int> m_size_map;
    std::vector<int> m_size_in_set_vec;
    int m_full_percentage;

    struct CacheMemorySASectorStats : public statistics::Group
    {
        CacheMemorySASectorStats(statistics::Group *parent);
        statistics::Average numByteInUse;
        statistics::Scalar numDataContraction;
        statistics::Scalar numDataExpansion;
        statistics::Scalar util_byte;
        statistics::Scalar compression_ratio_intra;
        statistics::Scalar numBlockMigrationAcrossSet;


    } cacheMemorySASectorStats;
};

} // namespace ruby

} // namespace gem5
#endif