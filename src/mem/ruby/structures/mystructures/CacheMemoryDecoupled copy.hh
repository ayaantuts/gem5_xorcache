#ifndef __MEM_RUBY_STRUCTURES_MYSTRUCTURES_CACHEMEMORYDECOUPLED_HH__
#define __MEM_RUBY_STRUCTURES_MYSTRUCTURES_CACHEMEMORYDECOUPLED_HH__

#include "params/RubyCacheDecoupled.hh"
#include "mem/ruby/structures/CacheMemory.hh"

namespace gem5
{

namespace ruby
{

class CacheMemoryDecoupled : public CacheMemory
{
  public:
    typedef RubyCacheDecoupledParams Params;
    CacheMemoryDecoupled(const Params &p);
    ~CacheMemoryDecoupled();

    void init() override;

    // tests to see if an address is present in the cache data array
    bool isDataPresent(Addr address) const;

    // Returns true if there is:
    //   a) a tag match on this address with allocated data entry or there is
    //   b) an unused space in the same cache set
    bool cacheAvailData(Addr address, int data_size) const;

    // Returns true if there is enough space to coallocate, i.e., no need to replace!
    bool cacheCanCoallocate(Addr address, int data_size) const;

    void cacheAvailData_set_way(Addr address, int data_size, int* ret_dataset, int* ret_dataway) const;

    // Returns with the physical address of the conflicting cache line for data array
    Addr cacheProbeData(Addr address) const;

    // find an unused entry and sets the tag appropriate for the address
    AbstractCacheEntry* allocate(Addr address, AbstractCacheEntry* new_entry);
    
    // Explicitly free up this address
    void deallocate(Addr address);

    void linkDataToTag(Addr address, AbstractCacheEntry* new_dataEntry, int data_size);
    void unlinkDataToTag(Addr address);
    void updateLinkDataToTag(Addr address, int data_size);

    void profileReplacmentDataArray();

  private:
    int m_data_num_set_bits;
    int m_data_array_assoc;
    int m_data_array_set;
    int m_num_seg_per_blk;
    int m_segment_size;

    std::unordered_map<Addr, int> m_data_index; //map address to seg

    // 3D abstractcacheentry for cache's data array, set,way,seg
    std::vector<std::vector<std::vector<AbstractCacheEntry*> > > m_cache_data;
    replacement_policy::Base *m_replacementPolicy_ptr_data;
    std::vector<std::vector<std::vector<ReplData> > > replacement_data_for_data;

    // from data to tag: each per data (3d)
    std::vector<std::vector<std::vector<AbstractCacheEntry*> > > m_data_head_tag_ptr;
    // data internal- size of each data in unit segment: each per data (3d)
    std::vector<std::vector<std::vector<int> > > m_data_cntr;
    std::vector<std::vector<int> > m_data_blk_vacancy;

    // tag internal: each per tag (2d)
    std::vector<std::vector<AbstractCacheEntry*> > m_tag_next_tag_ptr;
    std::vector<std::vector<AbstractCacheEntry*> > m_tag_prev_tag_ptr;
    // from tag to data: each per tag (2d)
    std::vector<std::vector<AbstractCacheEntry*> > m_tag_data_ptr;
    std::vector<std::vector<int> > m_tag_seg_cntr;

    // convert a Address to its location in the cache
    int64_t addressToCacheSetData(Addr address) const;

    // Given a address: returns the segment index of the data.
    int findDataSegIdx(Addr address) const;

    // Given a data set and data way: returns the segment index of an empty entry pointer.
    int findEmptyDataSegIdx(int dataSet, int dataWay) const;

  private:
      struct CacheMemoryDecoupledStats : public statistics::Group
      {
          CacheMemoryDecoupledStats(statistics::Group *parent);

          statistics::Scalar block_size;
          statistics::Scalar segment_size;
          statistics::Scalar numExpansion;
          statistics::Scalar numExpMigration;
          statistics::Scalar numContraction;
          statistics::Scalar numReplDataArr;
          statistics::Average numSegInUse;
          statistics::Average numTagInUse;
          statistics::Formula compRatio;

      } cacheMemoryDecoupledStats;
};

} // namespace ruby

} // namespace gem5
#endif