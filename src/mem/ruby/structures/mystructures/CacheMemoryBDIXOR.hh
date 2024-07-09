#ifndef __MEM_RUBY_STRUCTURES_MYSTRUCTURES_CACHEMEMORYBDIXOR_HH__
#define __MEM_RUBY_STRUCTURES_MYSTRUCTURES_CACHEMEMORYBDIXOR_HH__

#include "params/RubyCacheBDIXOR.hh"
#include "mem/ruby/structures/mystructures/CacheMemoryDecoupled.hh"
#include "mem/ruby/common/MachineID.hh"
// #include "mem/ruby/structures/mystructures/XORPolicy.hh"

namespace gem5
{

namespace ruby
{

class CacheMemoryBDIXOR : public CacheMemoryDecoupled
{
  public:
    typedef RubyCacheBDIXORParams Params;
    CacheMemoryBDIXOR(const Params &p);
    ~CacheMemoryBDIXOR();

    void init() override;

    AbstractCacheEntry* allocate(Addr address, AbstractCacheEntry* new_entry);

    /* return true if (there is a unpaired logical datablock AND can xor) 
    OR able to coallocate worst case block size */
    bool cacheAvailData(Addr address, int data_size) const;
    /* return true if there is space to coallocate data */
    bool hasSpace(Addr address, int data_size) const;
    /* return true if there is any data that is unpaired */
    bool hasAnyUnpaired(Addr address) const;
    bool hasAnyUnpaired_withSharer(Addr address) const;

    /* return true if data array can coallocate worst case block size */
    // bool cacheCanCoallocate(Addr address, int data_size) const; // same as CacheMemoryDecoupled

    /* return the address of head tag of the conflicting data */
    // Addr cacheProbeData(Addr address) const; // same as in CacheMemoryDecoupled

    bool hasPartner(Addr address) const;
    /* return true if the tag with input address has a next tag */
    bool hasNextTag(Addr address) const;
    /* return true if the tag with input address has a prev tag */
    bool hasPrevTag(Addr address) const;
    /* return ture if the tag is unparied, i.e., no prev and no next */
    bool isUnpaired(Addr address) const;
    /* return true if the input tag has a next tag */
    bool hasNextTag(AbstractCacheEntry* entry) const;
    /* return true if the input tag has a prev tag */
    bool hasPrevTag(AbstractCacheEntry* entry) const;
    /* return ture if the tag is unparied, i.e., no prev and no next */
    bool isUnpaired(AbstractCacheEntry* entry) const;

    Addr getPartnerTagAddress(Addr address);
    /* return address of the next tag of provided address */
    Addr getNextTagAddress(Addr address);
    /* return address of the prev tag of provided address */
    Addr getPrevTagAddress(Addr address);

    void profileReplacementXOR();

    /* randomly choose a way in data set that can xor and is currently unpaired, can also choose -1*/
    int getXORChoiceWay(Addr address);
    /* return true if we cannot do xor */
    bool canNotXOR(Addr address);
    bool canNotXOR_getX(Addr address);

    ////////////////////////////////
    /// @brief high level function to determine if there's good xor candidate
    /// @param address addr of block to fill
    /// @param requestor the id of L1 sending GET message
    /// @return true if good candidate exists, otherwise false
    bool hasGoodXORCandidate(Addr address, MachineID requestor) const;
    bool hasGoodXORCandidate_getX(Addr address, MachineID requestor) const;
    /* return true if no good candidate
    good as long as it is unpaired. */
    bool hasGoodXORCandidate_greedy(Addr address, MachineID requestor) const;
    bool hasGoodXORCandidate_greedy_getX(Addr address, MachineID requestor) const;
    /* return true as long as data space is all full. */
    bool hasGoodXORCandidate_nongreedy(Addr address, MachineID requestor) const;
    bool hasGoodXORCandidate_nongreedy_getX(Addr address, MachineID requestor) const;
    /* return true as long as there is unpaired block from same core*/
    bool hasGoodXORCandidate_same_core(Addr address, MachineID requestor) const;
    bool hasGoodXORCandidate_same_core_getX(Addr address, MachineID requestor) const;

    /* randomly choose a way in data set that can xor and is currently unpaired, cannot choose -1*/
    int getXORChoiceWay_existingOnly(Addr address);

    ////////////////////////////////
    /// @brief high level function to select a xor candidate and return candidate's addr
    /// @param address addr of block to fill
    /// @param requestor the id of L1 sending GET message
    /// @return addr of the selected candidate
    Addr getXORChoiceAddr(Addr address, MachineID requestor);
    Addr getXORChoiceAddr_getX(Addr address, MachineID requestor);
    /* **randomly** choose a block from same core, or a block from different core */
    Addr getXORChoiceAddr_random_favor_sameCore(Addr address, MachineID requestor);
    Addr getXORChoiceAddr_random_favor_sameCore_getX(Addr address, MachineID requestor);
    /* chooses the closest in time block from same core, or closest in time block from different core */
    Addr getXORChoiceAddr_MRU_favor_sameCore(Addr address, MachineID requestor);
    Addr getXORChoiceAddr_MRU_favor_sameCore_getX(Addr address, MachineID requestor);
    /* chooses the most different in time block from same core, or most different in time block from different core.
    aka.LRU*/
    Addr getXORChoiceAddr_LRU_favor_sameCore(Addr address, MachineID requestor);
    Addr getXORChoiceAddr_LRU_favor_sameCore_getX(Addr address, MachineID requestor);

    AbstractCacheEntry* getDataEntryAtWay(Addr address, int way);
    Addr getAddrDataAtWay(Addr address, int way);
    void lockXOR(Addr address);
    void unlockXOR(Addr address);
    bool isLockedXOR(Addr address);

    // adding new functions
    void linkDataToTag_existing(Addr address, AbstractCacheEntry* new_dataEntry, int data_size);
    void linkDataToTag_existing(Addr address, int data_size);
    AbstractCacheEntry* unlinkDataToTag_existing(Addr address);
    bool isPartnerReplBlocked(Addr address) const;
    bool isPartnerReplBlocked_memdata(Addr address);
    bool isPartnerShared(Addr requested_address);
    void settupTempLink(Addr requested_address, Addr existing_addr);
    void validateTempLink(Addr headAddr);
    Addr getExistingAddr(Addr requested_address) const;
    // void removeBothLinks(Addr existing_add);
    void unblockRepl(Addr existing_add);
    void rmReqToExisting(Addr req_address);
    DataBlock xorTwoDataBlock(Addr address);
    DataBlock tryXOR(Addr address, DataBlock newblk);

    // rewriting functions
    void unlinkDataToTag(Addr address);
    void linkDataToTag(Addr address, AbstractCacheEntry* new_dataEntry, int data_size);
    Addr cacheProbeData(Addr address) const;
    Addr cacheProbeExcludePartner(Addr address) const;
    bool cacheCanCoallocate(Addr address, int data_size) const;

    void profileCompressedAccess(Addr address, MachineID requestor);
    
    typedef enum FWDT {
      MemoryDirectFwd, 
      SamecoreFwd,
      CrosscoreFwd,
    }FWDTYPE;

    FWDTYPE determineForwardingType(Addr address, MachineID requestor);
    bool canDoSameCoreForwarding(Addr address, MachineID requestor);
    bool noSpecialFwdNeeded(Addr address, MachineID requestor);
    void profileUncompressedAccess();
    void profileFillNonXOR();
    void profileFillNonXOR_noGoodCandidate();
    void profileFillNonXOR_noSingular();
    void profileFillXOR();

    void profileXORDecompReason_notRecoverable_putx();
    void profileXORDecompReason_notRecoverable_get();
    void profileXORDecompReason_noSharer();
    void profileXORDecompReason_tM();
    void profileXORDecompReason_tag();
    void profileXORDecompReason_data();

    // m_pendingEvictionMap[initiate] = toEvict
    void addPendingEviction(Addr initiate, Addr toEvict); 
    //return m_pendingEvictionMap[initiate]
    Addr getPendingEviction(Addr initiate) const; 
    // if true if no match
    bool noPendingEviction(Addr initiate) const;
    // delete initiate from map
    void rmPendingEviction(Addr toEvict);

    // m_blockedHitMap[toInv] = blockedHit
    void addBlockedHitBlock(Addr toInv, Addr blockedHit);
    // return m_blockedHitMap[toInv]
    Addr getBlockedHitAddress(Addr toInv) const;
    // if true if no match
    bool noBlockedHitBlock(Addr toInv) const;
    // delete toInv from map
    void rmBlockedHitBlock(Addr blockedHit);

    bool includeProactiveEviction() const;

  protected:
    // uint64_t m_print_util_interval_tick;
    // Tick last_print_tick;
    std::vector<std::vector<bool> > m_tag_can_xor;
    // XORer m_xorer;
    std::unordered_map<Addr, Addr> m_tempLink;
    std::unordered_map<Addr, std::vector<Addr>> m_pendingEvictionMap;
    std::unordered_map<Addr, std::vector<Addr>> m_blockedHitMap;
    bool m_includeProactiveEviction;
    bool m_search_in_set;
    int m_xor_policy_id;

  protected:
      struct CacheMemoryBDIXORStats : public statistics::Group
      {
          CacheMemoryBDIXORStats(statistics::Group *parent);
          statistics::Scalar numReplXOR;
          statistics::Scalar XORChoice_sameCore;
          statistics::Scalar XORChoice_pureRandom;
          statistics::Scalar numXOR;
          statistics::Scalar accessToCompressedBlock;
          statistics::Scalar accessToUncompressedBlock;
          statistics::Scalar sameCoreForwarding;
          statistics::Scalar crossCoreForwarding;
          statistics::Scalar directForwarding;
          statistics::Scalar patnerHasNoSharer;
          statistics::Distribution partnerSharerCt;
          statistics::Distribution xorChoiceCt;
          statistics::Distribution xorChoiceCt_sameCore;
          statistics::Scalar fillNonXOR;
          statistics::Scalar fillNonXOR_noGoodCandidate;
          statistics::Scalar fillNonXOR_noSingular;
          statistics::Scalar fillXOR;
          statistics::Scalar XORDecompReason_notRecoverable;
          statistics::Scalar XORDecompReason_notRecoverable_putx;
          statistics::Scalar XORDecompReason_notRecoverable_get;
          statistics::Scalar XORDecompReason_tM;
          statistics::Scalar XORDecompReason_tag;
          statistics::Scalar XORDecompReason_data;
          statistics::Scalar XORDecompReason_noSharer;
          statistics::Average numTagLocked;

      } cacheMemoryBDIXORStats;
};

} // namespace ruby

} // namespace gem5
#endif