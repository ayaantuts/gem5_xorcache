#ifndef __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_CACHEMEMORYREGIONSECTOR_HH__
#define __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_CACHEMEMORYREGIONSECTOR_HH__

#include "params/RubyCacheRegionSector.hh"
#include "mem/ruby/structures/CacheMemory.hh"

//CacheMemoryRegionSector is adapted from CacheMemoryFASector
// it is partitioned with sector granularity and models fragmentation within regions

namespace gem5
{

namespace ruby
{

class CacheMemoryRegionSector : public CacheMemory
{
  public:
    typedef RubyCacheRegionSectorParams Params;
    CacheMemoryRegionSector(const Params &p);
    ~CacheMemoryRegionSector();

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
      return (float) cacheMemoryRegionSectorStats.numByteInUse.value() / (m_num_bytes_total) * 100;
    }

  protected:
    int m_num_bytes_total;
    int m_num_regions;
    int m_num_bytes_in_use;
    std::unordered_map<Addr, int> m_size_map;
    std::unordered_map<Addr, int> m_region_map; // new
    std::vector<int> m_numbyteinuse_per_region; // new
    int m_full_percentage;

    struct CacheMemoryRegionSectorStats : public statistics::Group
    {
        CacheMemoryRegionSectorStats(statistics::Group *parent);
        statistics::Average numByteInUse;

        statistics::Scalar numDataEviction;
        statistics::Scalar numDataContraction;
        statistics::Scalar numDataExpansion;
        
        statistics::Scalar util_byte;
        statistics::Scalar compression_ratio_intra;
        statistics::Scalar numByteTotal;


    } cacheMemoryRegionSectorStats;
};

} // namespace ruby

} // namespace gem5
#endif