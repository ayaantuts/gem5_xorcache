#ifndef __MEM_RUBY_STRUCTURES_MYSTRUCTURES_CACHEMEMORYDECOUPLEDMN_HH__
#define __MEM_RUBY_STRUCTURES_MYSTRUCTURES_CACHEMEMORYDECOUPLEDMN_HH__

#include "params/RubyCacheDecoupledMN.hh"
#include "mem/ruby/structures/mystructures/CacheMemoryDecoupled.hh"
#include "mem/ruby/structures/mystructures/HashTableEntry.hh"

namespace gem5
{

namespace ruby
{

class CacheMemoryDecoupledMN : public CacheMemoryDecoupled
{
  public:
    typedef RubyCacheDecoupledMNParams Params;
    CacheMemoryDecoupledMN(const Params &p);
    ~CacheMemoryDecoupledMN();

    void init() override;
    ///////// rewriting functions in CacheMemoryDecoupled ////////
    /* setup pointer mapping from tag to data and vice versa, tag->data has to go through hashTable */
    void linkDataToTag(Addr address, AbstractCacheEntry* new_dataEntry, int data_size, uint32_t hash);
    /* setup pointer mapping from tag to data and vice versa, tag->data has to go through hashTable;
    Note: this is only called when data matches! */
    void linkDataToTag_dedup(Addr address, int data_size, uint32_t hash);
    // void updateLinkDataToTag(Addr address, int data_size, uint32_t hash);
    // void updateLinkDataToTag_dedup(Addr address, int data_size, uint32_t hash);
    void unlinkDataToTag(Addr address);
    /* called on data update; returns true if 1) hashtable hit and data match or 
    2) hashtable hit and data mismatch and data array has free space or 
    3) hashtable miss and data array has free space.
    Pseudocode: (If hashtable hit and data match => true
    else check data array space avail
      if avail => true
      else => false)
    Note: tag already maps to some space in data array, can potentially free up old space when evaluating
    data array availability, i.e., when no other tag points to it (m_data_cntr)*/
    bool cacheCanCoallocate(Addr address, int data_size);
    /* called on data first write; guaranteed no allocated data for this tag*/
    bool cacheAvailData(Addr address, int data_size) const;
    /* convert a Address to its location in the cache. if this dataset does not have 
    enough vacancy, select first free set.
    Note: make sure there is at least one set has enough vacancy!*/
    int64_t addressToCacheSetData(Addr address, int data_size);
    int64_t addressToCacheSet(Addr address) const;
    Addr cacheProbeData(Addr address) const;

    ////////// hash table: maps hash(dataBlock) to cacheSet ///////
    int64_t hashToHashTableSet(uint32_t hash) const;
    uint32_t hashToHashTablePartialTag(uint32_t hash) const;
    HashTableEntry* lookupHash(uint32_t hash) const;
    /* if present in hashtable return dataset, else return -1 */
    int64_t hashToDataSet_noInsert(uint32_t hash) const;
    HashTableEntry* hashTableProbe(uint32_t hash) const;
    int findTagInSetHashTable(int64_t hashSet, Addr hashTag) const;
    /* returns true if there is space in ht or this hash already exist in ht */
    bool hashTableAvail(uint32_t hash) const;
    /* return duplicated data's tag if present, else return null */
    Addr findDuplicatedDatasTagAddr(uint32_t hash, int dataWayorSeg) const;
    /* return duplicated data's tag's way if present, else return -1 */
    int findDuplicatedDatasTagWay(uint32_t hash) const;
    // int64_t hashToDataSet(uint32_t hash, Addr address);
    bool doesTagListContainAddress(AbstractCacheEntry* tagHead, Addr address) const;
    ////////// new functions /////////////
    // void profileDataUpdate(Addr address, int data_size);

  protected:
    /* hashTable set */
    int m_num_hash_bucket;
    /* hashTable assoc */
    int m_chain_length;
    /* log2(hashTable set) */
    int m_hashTable_num_set_bits;
    /* hashTable tag size in bits */
    int m_hashTable_partialHash_length;

    replacement_policy::Base *m_replacementPolicy_ptr_hashTable;
    std::vector<std::vector<ReplData> > replacement_data_hashTable;

    /* hashTable data structure */
    std::vector<std::vector<HashTableEntry*> > m_cache_hashTable;
    /* hashTable chain/assoc=m_hashTable_index[partialHash] */
    std::vector<std::unordered_map<uint32_t, int>> m_hashTable_index;

    /* tag to hashtable pointer */
    std::vector<std::vector<uint32_t>> m_tag_hashTable_ptr;
    /* tag to hashtable pointer valid */
    std::vector<std::vector<bool>> m_tag_hashTable_ptr_valid;


  protected:
      struct CacheMemoryDecoupledMNStats : public statistics::Group
      {
          CacheMemoryDecoupledMNStats(statistics::Group *parent);
          statistics::Average numHashTableEntryInUse;
          statistics::Scalar numDataSetMisplace;
          statistics::Scalar numDataSetDefaultPlacement;
          statistics::Scalar numHashTableEntryReplacement;
          statistics::Scalar numHashTableHit;
          statistics::Scalar numHashTableMiss;
          statistics::Scalar numHashCollision;

      } cacheMemoryDecoupledMNStats;
};

} // namespace ruby

} // namespace gem5
#endif