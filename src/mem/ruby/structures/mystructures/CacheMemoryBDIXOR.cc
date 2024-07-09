#include "debug/RubyCacheBDIXOR.hh"
#include "debug/RubyCacheBDIXORSelection.hh"
#include "debug/RubyCacheBDIXORFwd.hh"
#include "debug/RubyCacheUtil.hh"
#include "mem/ruby/structures/mystructures/CacheMemoryBDIXOR.hh"
#include "mem/ruby/system/RubySystem.hh"
#include "mem/ruby/protocol/L2Cache_Entry.hh"
#include "mem/ruby/protocol/L2Cache_State.hh"

#include <iostream>

namespace gem5
{

namespace ruby
{

CacheMemoryBDIXOR::CacheMemoryBDIXOR(const Params &p)
    : CacheMemoryDecoupled(p),
    cacheMemoryBDIXORStats(this)
{
    std::cout << "Hello World comp xor! From a CacheMemoryBDIXOR! "<<std::endl;
    m_includeProactiveEviction = p.include_proactive_eviction;
    m_search_in_set = p.search_in_set;
    m_xor_policy_id = p.xor_policy_id;
    // m_print_util_interval_tick = p.print_util_interval_tick;
    
}

void
CacheMemoryBDIXOR::init()
{
    CacheMemoryDecoupled::init();
    if (m_search_in_set == false) {
        assert(m_data_array_set == 1); // data array has to be fully associative to search entire bank
    }
    std::cout << "CacheMemoryBDIXOR::m_search_in_set=" << m_search_in_set << std::endl;
    std::cout << "CacheMemoryBDIXOR::m_num_seg_per_set=" << m_num_seg_per_set << std::endl;
    m_tag_can_xor.resize(m_cache_num_sets,
                    std::vector<bool>(m_cache_assoc, true));
}

CacheMemoryBDIXOR::~CacheMemoryBDIXOR()
{
    m_tag_can_xor.clear();
    m_pendingEvictionMap.clear();
    m_blockedHitMap.clear();
}

AbstractCacheEntry*
CacheMemoryBDIXOR::allocate(Addr address, AbstractCacheEntry *entry)
{
    AbstractCacheEntry *retEntry = CacheMemoryDecoupled::allocate(address, entry);

    // print out the number of tags in use every interval (10 billion) ticks
    if (curTick()==last_print_tick) {
        DPRINTF(RubyCacheUtil, "XOR_nr_putx=%d, nr_get=%d, XOR_tag=%d, XOR_data=%d, repl_tag=%d, repl_data=%d, nosharer=%d\n", 
        cacheMemoryBDIXORStats.XORDecompReason_notRecoverable_putx.value(),
        cacheMemoryBDIXORStats.XORDecompReason_notRecoverable_get.value(),
        cacheMemoryBDIXORStats.XORDecompReason_tag.value(),
        cacheMemoryBDIXORStats.XORDecompReason_data.value(),
        cacheMemoryStats.numReplTagArr.value(),
        cacheMemoryDecoupledStats.numReplDataArr.value(),
        cacheMemoryBDIXORStats.XORDecompReason_noSharer.value()
        );
        
    }

    return retEntry;
}

bool
CacheMemoryBDIXOR::hasAnyUnpaired(Addr address) const
{
    if (m_search_in_set == true) {
        int dataSet = addressToCacheSetData(address);
        for (int i = 0; i < m_num_seg_per_set; i++) {
            if (m_cache_data[dataSet][i] != nullptr) {
                AbstractCacheEntry* tagHeadEntry = m_data_head_tag_ptr[dataSet][i];
                if (isUnpaired(tagHeadEntry) && m_tag_can_xor[tagHeadEntry->getSet()][tagHeadEntry->getWay()]) {
                    return true;
                }
            }
        }
        return false;
    }
    else {
        for (int j=0; j < m_data_array_set; j++) {
            for (int i=0; i< m_num_seg_per_set; i++) {
                if (m_cache_data[j][i] != nullptr) {
                    AbstractCacheEntry* tagHeadEntry = m_data_head_tag_ptr[j][i];
                    if (isUnpaired(tagHeadEntry) && m_tag_can_xor[tagHeadEntry->getSet()][tagHeadEntry->getWay()]) {
                        return true;
                    }
                }
            }
        }
        return false;
    }
}
bool
CacheMemoryBDIXOR::hasAnyUnpaired_withSharer(Addr address) const
{
    if (m_search_in_set == true) {
        int dataSet = addressToCacheSetData(address);
        for (int i = 0; i < m_num_seg_per_set; i++) {
            if (m_cache_data[dataSet][i] != nullptr) {
                AbstractCacheEntry* tagHeadEntry = m_data_head_tag_ptr[dataSet][i];
                L2Cache_Entry * tagHeadEntry_cast = dynamic_cast<L2Cache_Entry *>(tagHeadEntry);
                if (isUnpaired(tagHeadEntry) 
                    && m_tag_can_xor[tagHeadEntry->getSet()][tagHeadEntry->getWay()]
                    && tagHeadEntry_cast->getCacheState() != L2Cache_State::L2Cache_State_MT
                    && tagHeadEntry_cast->getCacheState() != L2Cache_State::L2Cache_State_MT_MB
                    && tagHeadEntry_cast->getCacheState() != L2Cache_State::L2Cache_State_SS_MB
                    && tagHeadEntry_cast->m_Sharers.count() > 0) {
                    return true;
                }
            }
        }
        return false;
    }
    else {
        for (int j=0; j < m_data_array_set; j++) {
            for (int i=0; i< m_num_seg_per_set; i++) {
                if (m_cache_data[j][i] != nullptr) {
                    AbstractCacheEntry* tagHeadEntry = m_data_head_tag_ptr[j][i];
                    L2Cache_Entry * tagHeadEntry_cast = dynamic_cast<L2Cache_Entry *>(tagHeadEntry);
                    if (isUnpaired(tagHeadEntry) 
                        && m_tag_can_xor[tagHeadEntry->getSet()][tagHeadEntry->getWay()]
                        && tagHeadEntry_cast->getCacheState() != L2Cache_State::L2Cache_State_MT
                        && tagHeadEntry_cast->getCacheState() != L2Cache_State::L2Cache_State_MT_MB
                        && tagHeadEntry_cast->getCacheState() != L2Cache_State::L2Cache_State_SS_MB
                        && tagHeadEntry_cast->m_Sharers.count() > 0) {
                        return true;
                    }
                }
            }
        }
        return false;
    }
}

bool
CacheMemoryBDIXOR::hasSpace(Addr address, int data_size) const
{
    return CacheMemoryDecoupled::cacheAvailData(address, data_size);
}


bool
CacheMemoryBDIXOR::cacheAvailData(Addr address, int data_size) const 
{
    bool canCoallocate = hasSpace(address, data_size);
    bool hasUnpaired = hasAnyUnpaired(address);
    if (canCoallocate && hasUnpaired) {
        DPRINTF(RubyCacheBDIXOR, "cacheAvailData() canCoallocate && hasUnpaired\n");
        return true;
    }
    if (!canCoallocate && !hasUnpaired) {
        DPRINTF(RubyCacheBDIXOR, "cacheAvailData() !canCoallocate && !hasUnpaired!!!\n");
        return false;
    }
    if (canCoallocate && !hasUnpaired) {
        DPRINTF(RubyCacheBDIXOR, "cacheAvailData() canCoallocate && !hasUnpaired\n");
        return true;
    }
    if (!canCoallocate && hasUnpaired) {
        DPRINTF(RubyCacheBDIXOR, "cacheAvailData() !canCoallocate && hasUnpaired\n");
        return true;
    }
    panic("should not be here");
    return false;
}

bool
CacheMemoryBDIXOR::isUnpaired(AbstractCacheEntry* tagEntry) const
{
    return (!hasNextTag(tagEntry) && !hasPrevTag(tagEntry));
}

bool
CacheMemoryBDIXOR::isUnpaired(Addr address) const
{
    return (!hasNextTag(address) && !hasPrevTag(address));
}

bool
CacheMemoryBDIXOR::hasPartner(Addr address) const
{
    return (hasNextTag(address) || hasPrevTag(address));
}

bool
CacheMemoryBDIXOR::hasNextTag(Addr address) const {
    //lookup tag
    const AbstractCacheEntry* const tagEntry = lookup(address);
    assert(tagEntry != nullptr);
    int tagSet = tagEntry->getSet();
    int tagWay = tagEntry->getWay();
    
    return (m_tag_next_tag_ptr[tagSet][tagWay] != nullptr);
}

bool
CacheMemoryBDIXOR::hasPrevTag(Addr address) const {
    //lookup tag
    const AbstractCacheEntry* const tagEntry = lookup(address);
    assert(tagEntry != nullptr);
    int tagSet = tagEntry->getSet();
    int tagWay = tagEntry->getWay();
    
    return (m_tag_prev_tag_ptr[tagSet][tagWay] != nullptr);
}

bool
CacheMemoryBDIXOR::hasNextTag(AbstractCacheEntry* tagEntry) const {
    int tagSet = tagEntry->getSet();
    int tagWay = tagEntry->getWay();
    
    return (m_tag_next_tag_ptr[tagSet][tagWay] != nullptr);
}

bool
CacheMemoryBDIXOR::hasPrevTag(AbstractCacheEntry* tagEntry) const {
    int tagSet = tagEntry->getSet();
    int tagWay = tagEntry->getWay();
    
    return (m_tag_prev_tag_ptr[tagSet][tagWay] != nullptr);
}

Addr
CacheMemoryBDIXOR::getPartnerTagAddress(Addr address) {
    if (hasNextTag(address)) {
        return getNextTagAddress(address);
    }
    else if (hasPrevTag(address)) {
        return getPrevTagAddress(address);
    }
    else {
        assert(false);
    }
}
Addr
CacheMemoryBDIXOR::getNextTagAddress(Addr address) {
    //lookup tag
    AbstractCacheEntry* tagEntry = lookup(address);
    assert(tagEntry != nullptr);
    int tagSet = tagEntry->getSet();
    int tagWay = tagEntry->getWay();
    assert(m_cache[tagSet][tagWay]->m_Address == address);
    assert(m_tag_next_tag_ptr[tagSet][tagWay] != nullptr);
    return m_tag_next_tag_ptr[tagSet][tagWay]->m_Address;
}

Addr
CacheMemoryBDIXOR::getPrevTagAddress(Addr address) {
    //lookup tag
    AbstractCacheEntry* tagEntry = lookup(address);
    assert(tagEntry != nullptr);
    int tagSet = tagEntry->getSet();
    int tagWay = tagEntry->getWay();
    assert(m_cache[tagSet][tagWay]->m_Address == address);
    assert(m_tag_prev_tag_ptr[tagSet][tagWay] != nullptr);
    return m_tag_prev_tag_ptr[tagSet][tagWay]->m_Address;
}

void
CacheMemoryBDIXOR::profileReplacementXOR() {
    cacheMemoryBDIXORStats.numReplXOR++;
}

AbstractCacheEntry* 
CacheMemoryBDIXOR::getDataEntryAtWay(Addr address, int way) {
    int set = addressToCacheSetData(address);
    assert(m_cache_data[set][way] != nullptr);
    return m_cache_data[set][way];
}

Addr
CacheMemoryBDIXOR::getAddrDataAtWay(Addr address, int way) {
    int set = addressToCacheSetData(address);
    assert(m_cache_data[set][way] != nullptr);
    AbstractCacheEntry* tag = m_data_head_tag_ptr[set][way];
    assert(tag != nullptr);
    return tag->m_Address;
}


int
CacheMemoryBDIXOR::getXORChoiceWay(Addr address) {
    int set = addressToCacheSetData(address);
    std::vector<int> candidates_way;
    candidates_way.push_back(-1);
    for (int i=0; i < m_num_seg_per_set; i++) {
        if (m_cache_data[set][i] != nullptr) {
            AbstractCacheEntry* tag = m_data_head_tag_ptr[set][i];
            if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()]) {
                // choose among the unpaired and can xored candidates
                candidates_way.push_back(i);
            }
        } 
    }
    int candidate_ind = rand() % candidates_way.size();
    int way = candidates_way.at(candidate_ind);
    candidates_way.clear();
    DPRINTF(RubyCacheBDIXOR, "getXORChoiceWay() rand to %d\n",way);
    return way;
}

DataBlock
CacheMemoryBDIXOR::xorTwoDataBlock(Addr address)
{
    AbstractCacheEntry* tagEntry = lookup(address);
    DataBlock xor_result = DataBlock();

    //get old tag
    AbstractCacheEntry* tagEntry_old = m_tag_prev_tag_ptr[tagEntry->getSet()][tagEntry->getWay()];
    assert(tagEntry_old != nullptr);

    int base = 8;
    for (int i = 0; i < m_block_size/base; i++) {
        uint8_t * chunk8_new = reinterpret_cast<uint8_t*>(tagEntry->getDataBlk().getDataMod(i*base));
        uint8_t * chunk8_old = reinterpret_cast<uint8_t*>(tagEntry_old->getDataBlk().getDataMod(i*base));
        uint8_t chunck8_xor_result = uint8_t(chunk8_new[0])^uint8_t(chunk8_old[0]);
        xor_result.setData(&chunck8_xor_result,i,1);
    }
    cacheMemoryBDIXORStats.numXOR += 1;
    return xor_result;
    // std::cout << "3.checking data[" << dataset << "," << i << "]=" <<tag->getDataBlk() << std::endl;

}
DataBlock
CacheMemoryBDIXOR::tryXOR(Addr address, DataBlock newblk)
{
    AbstractCacheEntry* tagEntry = lookup(address);
    DataBlock xor_result = DataBlock();

    int base = 8;
    for (int i = 0; i < m_block_size/base; i++) {
        uint8_t * chunk8_new = reinterpret_cast<uint8_t*>(tagEntry->getDataBlk().getDataMod(i*base));
        uint8_t * chunk8_old = reinterpret_cast<uint8_t*>(newblk.getDataMod(i*base));
        uint8_t chunck8_xor_result = uint8_t(chunk8_new[0])^uint8_t(chunk8_old[0]);
        xor_result.setData(&chunck8_xor_result,i,1);
    }
    return xor_result;
}


bool
CacheMemoryBDIXOR::canNotXOR(Addr address) {
    // we cannot do xor
    if (hasAnyUnpaired(address) == false) { return true; }

    return false;
}

bool
CacheMemoryBDIXOR::canNotXOR_getX(Addr address) {
    // we cannot do xor if there is no unpaired or
    // all the unpaired has no sharer
    if (hasAnyUnpaired_withSharer(address) == false) { return true; }

    return false;
}

bool
CacheMemoryBDIXOR::hasGoodXORCandidate(Addr address, MachineID requestor) const
{
    switch (m_xor_policy_id) {
        case 1:
            return hasGoodXORCandidate_greedy(address, requestor);
        case 2:
            return hasGoodXORCandidate_nongreedy(address, requestor);
        case 3:
            return hasGoodXORCandidate_greedy(address, requestor);
        case 4:
            return hasGoodXORCandidate_nongreedy(address, requestor);
        case 5:
            return hasGoodXORCandidate_greedy(address, requestor);
        case 6:
            return hasGoodXORCandidate_nongreedy(address, requestor);
    }

    panic("unknown xor policy id %d\n",m_xor_policy_id);
}
bool
CacheMemoryBDIXOR::hasGoodXORCandidate_getX(Addr address, MachineID requestor) const
{
    switch (m_xor_policy_id) {
        case 1:
            return hasGoodXORCandidate_greedy_getX(address, requestor);
        case 2:
            return hasGoodXORCandidate_nongreedy_getX(address, requestor);
        case 3:
            return hasGoodXORCandidate_greedy_getX(address, requestor);
        case 4:
            return hasGoodXORCandidate_nongreedy_getX(address, requestor);
        case 5:
            return hasGoodXORCandidate_greedy_getX(address, requestor);
        case 6:
            return hasGoodXORCandidate_nongreedy_getX(address, requestor);
    }

    panic("unknown xor policy id %d\n",m_xor_policy_id);
}

bool
CacheMemoryBDIXOR::hasGoodXORCandidate_greedy(Addr address, MachineID requestor) const
{
    if (m_search_in_set == true) {
        int dataset = addressToCacheSetData(address);
        for (int i=0; i < m_num_seg_per_set; i++) {
            if (m_cache_data[dataset][i] != nullptr) {
                AbstractCacheEntry* tag = m_data_head_tag_ptr[dataset][i];
                if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()]) {
                    // bool isSharer = false;
                    L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                    if (tag_cast != nullptr) {
                        return true;
                    } else {
                        assert(false);
                    }
                }
            }
        }
        return false;
    }
    else {
        assert(m_data_array_set==1);
        for (int j=0; j < m_data_array_set; j++) {
            for (int i=0; i< m_num_seg_per_set; i++) {
                if (m_cache_data[j][i] != nullptr) {
                    AbstractCacheEntry* tag = m_data_head_tag_ptr[j][i];
                    if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()]) {
                        L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                        if (tag_cast != nullptr) {
                            return true;
                        } else {
                            assert(false);
                        }
                    }
                }
            }
        }
        return false;
    }
}
bool
CacheMemoryBDIXOR::hasGoodXORCandidate_greedy_getX(Addr address, MachineID requestor) const
{
    if (m_search_in_set == true) {
        int dataset = addressToCacheSetData(address);
        for (int i=0; i < m_num_seg_per_set; i++) {
            if (m_cache_data[dataset][i] != nullptr) {
                AbstractCacheEntry* tag = m_data_head_tag_ptr[dataset][i];
                if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()]) {
                    // bool isSharer = false;
                    L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                    if (tag_cast != nullptr) {
                        if (tag_cast->m_Sharers.count() > 0 && 
                            tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT &&
                            tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT_MB &&
                            tag_cast->getCacheState() != L2Cache_State::L2Cache_State_SS_MB) {
                            return true;
                        }
                    } else {
                        assert(false);
                    }
                }
            }
        }
        return false;
    }
    else {
        assert(m_data_array_set==1);
        for (int j=0; j < m_data_array_set; j++) {
            for (int i=0; i< m_num_seg_per_set; i++) {
                if (m_cache_data[j][i] != nullptr) {
                    AbstractCacheEntry* tag = m_data_head_tag_ptr[j][i];
                    if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()]) {
                        L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                        if (tag_cast != nullptr) {
                            if (tag_cast->m_Sharers.count() > 0 && 
                                tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT &&
                                tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT_MB &&
                                tag_cast->getCacheState() != L2Cache_State::L2Cache_State_SS_MB) {
                                return true;
                            }
                        } else {
                            assert(false);
                        }
                    }
                }
            }
        }
        return false;
    }
}

bool
CacheMemoryBDIXOR::hasGoodXORCandidate_nongreedy(Addr address, MachineID requestor) const
{
    if (m_search_in_set == true) {
        int dataset = addressToCacheSetData(address);
        for (int i=0; i < m_num_seg_per_set; i++) {
            if (m_cache_data[dataset][i] != nullptr) {
                AbstractCacheEntry* tag = m_data_head_tag_ptr[dataset][i];
                if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()]) {
                    // bool isSharer = false;
                    L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                    if (tag_cast != nullptr) {
                        if (m_data_set_vacancy[dataset] < m_num_seg_per_blk) {
                            return true;
                        }
                    } else {
                        assert(false);
                    }
                }
            }
        }
        return false;
    }
    else {
        assert(m_data_array_set==1);
        int dataset = addressToCacheSetData(address);
        assert(dataset == 0);
        for (int i=0; i < m_num_seg_per_set; i++) {
            if (m_cache_data[dataset][i] != nullptr) {
                AbstractCacheEntry* tag = m_data_head_tag_ptr[dataset][i];
                if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()]) {
                    // bool isSharer = false;
                    L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                    if (tag_cast != nullptr) {
                        if (m_data_set_vacancy[dataset] < m_num_seg_per_blk) {
                            return true;
                        }
                    } else {
                        assert(false);
                    }
                }
            }
        }
        return false;
    }
}

bool
CacheMemoryBDIXOR::hasGoodXORCandidate_nongreedy_getX(Addr address, MachineID requestor) const
{
    if (m_search_in_set == true) {
        int dataset = addressToCacheSetData(address);
        for (int i=0; i < m_num_seg_per_set; i++) {
            if (m_cache_data[dataset][i] != nullptr) {
                AbstractCacheEntry* tag = m_data_head_tag_ptr[dataset][i];
                if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()]) {
                    // bool isSharer = false;
                    L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                    if (tag_cast != nullptr) {
                        if (m_data_set_vacancy[dataset] < m_num_seg_per_blk && 
                            tag_cast->m_Sharers.count() > 0 && 
                            tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT &&
                            tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT_MB &&
                            tag_cast->getCacheState() != L2Cache_State::L2Cache_State_SS_MB) {
                            return true;
                        }
                    } else {
                        assert(false);
                    }
                }
            }
        }
        return false;
    }
    else {
        assert(m_data_array_set==1);
        int dataset = addressToCacheSetData(address);
        assert(dataset == 0);
        for (int i=0; i < m_num_seg_per_set; i++) {
            if (m_cache_data[dataset][i] != nullptr) {
                AbstractCacheEntry* tag = m_data_head_tag_ptr[dataset][i];
                if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()]) {
                    // bool isSharer = false;
                    L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                    if (tag_cast != nullptr) {
                        if (m_data_set_vacancy[dataset] < m_num_seg_per_blk && 
                            tag_cast->m_Sharers.count() > 0 && 
                            tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT &&
                            tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT_MB &&
                            tag_cast->getCacheState() != L2Cache_State::L2Cache_State_SS_MB) {
                            return true;
                        }
                    } else {
                        assert(false);
                    }
                }
            }
        }
        return false;
    }
}

bool
CacheMemoryBDIXOR::hasGoodXORCandidate_same_core(Addr address, MachineID requestor) const
{
    if (m_search_in_set == true) {
        int dataset = addressToCacheSetData(address);
        for (int i=0; i < m_num_seg_per_set; i++) {
            if (m_cache_data[dataset][i] != nullptr) {
                AbstractCacheEntry* tag = m_data_head_tag_ptr[dataset][i];
                if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()]) {
                    bool isSharer = false;
                    bool isOwner = false;
                    L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                    if (tag_cast != nullptr) {
                        isSharer = tag_cast->m_Sharers.isElement(requestor);
                        isOwner = tag_cast->m_Exclusive == requestor;
                        if (isOwner || isSharer) return true;
                    } else {
                        assert(false);
                    }
                }
            }
        }
        return false;
    }
    else {
        assert(m_data_array_set==1);
        for (int j=0; j < m_data_array_set; j++) {
            for (int i=0; i< m_num_seg_per_set; i++) {
                if (m_cache_data[j][i] != nullptr) {
                    AbstractCacheEntry* tag = m_data_head_tag_ptr[j][i];
                    if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()]) {
                        bool isSharer = false;
                        bool isOwner = false;
                        L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                        if (tag_cast != nullptr) {
                            isSharer = tag_cast->m_Sharers.isElement(requestor);
                            isOwner = tag_cast->m_Exclusive == requestor;
                            if (isOwner || isSharer) return true;
                        } else {
                            assert(false);
                        }
                    }
                }
            }
        }
        return false;
    }
}

bool
CacheMemoryBDIXOR::hasGoodXORCandidate_same_core_getX(Addr address, MachineID requestor) const
{
    if (m_search_in_set == true) {
        int dataset = addressToCacheSetData(address);
        for (int i=0; i < m_num_seg_per_set; i++) {
            if (m_cache_data[dataset][i] != nullptr) {
                AbstractCacheEntry* tag = m_data_head_tag_ptr[dataset][i];
                if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()]) {
                    bool isSharer = false;
                    bool isOwner = false;
                    L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                    if (tag_cast != nullptr) {
                        isSharer = tag_cast->m_Sharers.isElement(requestor);
                        isOwner = tag_cast->m_Exclusive == requestor;
                        if ((isOwner || isSharer) && 
                            tag_cast->m_Sharers.count() > 0 && 
                            tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT &&
                            tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT_MB &&
                            tag_cast->getCacheState() != L2Cache_State::L2Cache_State_SS_MB) {
                                return true;
                            }
                    } else {
                        assert(false);
                    }
                }
            }
        }
        return false;
    }
    else {
        assert(m_data_array_set==1);
        for (int j=0; j < m_data_array_set; j++) {
            for (int i=0; i< m_num_seg_per_set; i++) {
                if (m_cache_data[j][i] != nullptr) {
                    AbstractCacheEntry* tag = m_data_head_tag_ptr[j][i];
                    if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()]) {
                        bool isSharer = false;
                        bool isOwner = false;
                        L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                        if (tag_cast != nullptr) {
                            isSharer = tag_cast->m_Sharers.isElement(requestor);
                            isOwner = tag_cast->m_Exclusive == requestor;
                            if ((isOwner || isSharer) && 
                            tag_cast->m_Sharers.count() > 0 && 
                            tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT &&
                            tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT_MB &&
                            tag_cast->getCacheState() != L2Cache_State::L2Cache_State_SS_MB) {
                                return true;
                            } 
                        } else {
                            assert(false);
                        }
                    }
                }
            }
        }
        return false;
    }
}

int
CacheMemoryBDIXOR::getXORChoiceWay_existingOnly(Addr address) {
    int set = addressToCacheSetData(address);
    std::vector<int> candidates_way;
    for (int i=0; i < m_num_seg_per_set; i++) {
        if (m_cache_data[set][i] != nullptr) {
            AbstractCacheEntry* tag = m_data_head_tag_ptr[set][i];
            if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()]) {
                // choose among the unpaired and can xored candidates
                candidates_way.push_back(i);
            }
        } 
    }
    assert(candidates_way.size() > 0);
    int candidate_ind = rand() % candidates_way.size();
    int way = candidates_way.at(candidate_ind);
    candidates_way.clear();
    DPRINTF(RubyCacheBDIXOR, "getXORChoiceWay_existingOnly() rand to %d\n",way);
    return way;
}

/* Favor same core xor. If unavailable, random select candidate
*/
Addr
CacheMemoryBDIXOR::getXORChoiceAddr_random_favor_sameCore(Addr address, MachineID requestor)
{
    int set = addressToCacheSetData(address);
    std::vector<std::pair<int,int>> candidates_set_way_samecore;
    std::vector<std::pair<int,int>> candidates_set_way;
    
    // add all valid candidates
    if (m_search_in_set == true) {
        for (int i=0; i < m_num_seg_per_set; i++) {
            if (m_cache_data[set][i] != nullptr) {
                AbstractCacheEntry* tag = m_data_head_tag_ptr[set][i];
                bool isSharer = false;
                bool isOwner = false;
                L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                if (tag_cast != nullptr) {
                    isSharer = tag_cast->m_Sharers.isElement(requestor);
                    isOwner = tag_cast->m_Exclusive == requestor;
                } else {
                    assert(false);
                }
                // if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()] && isGoodState) {
                if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()]) {
                    // choose among the unpaired and can xored candidates
                    candidates_set_way.push_back(std::make_pair(set,i));
                    if (isOwner) {
                        candidates_set_way_samecore.push_back(std::make_pair(set,i)); 
                        DPRINTF(RubyCacheBDIXORSelection, 
                            "tag[%d,%d](%llx) is owner; <%s>; %s\n",tag->getSet(), tag->getWay(), 
                            tag->m_Address ,tag_cast->getCacheState(),tag_cast->m_Exclusive);
                    }
                    else if (isSharer) { 
                        candidates_set_way_samecore.push_back(std::make_pair(set,i)); 
                        DPRINTF(RubyCacheBDIXORSelection, 
                            "tag[%d,%d](%llx) is a sharer; <%s>; %s\n",tag->getSet(), tag->getWay(), 
                            tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Sharers);
                    }
                    else {
                        DPRINTF(RubyCacheBDIXORSelection, 
                            "tag[%d,%d](%llx) not a sharer nor owner; <%s>; %s;%s != %s\n",tag->getSet(), tag->getWay(), 
                            tag->m_Address, tag_cast->getCacheState(),tag_cast->m_Sharers, requestor,tag_cast->m_Exclusive);
                    }
                }
            } 
        }
    }
    else {
        for (int j=0; j < m_data_array_set; j++) {
            for (int i=0; i< m_num_seg_per_set; i++) {
                if (m_cache_data[j][i] != nullptr) {
                    AbstractCacheEntry* tag = m_data_head_tag_ptr[j][i];
                    bool isSharer = false;
                    bool isOwner = false;
                    L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                    if (tag_cast != nullptr) {
                        isSharer = tag_cast->m_Sharers.isElement(requestor);
                        isOwner = tag_cast->m_Exclusive == requestor;
                    } else {
                        assert(false);
                    }

                    if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()]) {
                        candidates_set_way.push_back(std::make_pair(j,i));
                        if (isOwner) {
                            candidates_set_way_samecore.push_back(std::make_pair(j,i)); 
                            DPRINTF(RubyCacheBDIXORSelection, 
                                "data[%d,%d]->tag[%d,%d](%llx) is owner; <%s>; %s\n",j,i,tag->getSet(), tag->getWay(), 
                                tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Exclusive);
                        }
                        else if (isSharer) { 
                            candidates_set_way_samecore.push_back(std::make_pair(j,i)); 
                            DPRINTF(RubyCacheBDIXORSelection, 
                                "data[%d,%d]->tag[%d,%d](%llx) is a sharer; <%s>; %s\n",j,i,tag->getSet(), tag->getWay(), 
                                tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Sharers);
                        }
                        else {
                            DPRINTF(RubyCacheBDIXORSelection, 
                                "data[%d,%d]->tag[%d,%d](%llx) not a sharer nor owner; <%s>; %s;%s != %s\n",j,i,tag->getSet(), tag->getWay(), 
                                tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Sharers, requestor,tag_cast->m_Exclusive);
                        }
                    }
                }
            }
        }
    }

    // select a candidate randomly
    if (candidates_set_way_samecore.size() > 0) {
        int candidate_ind = rand() % candidates_set_way_samecore.size();
        int way = candidates_set_way_samecore.at(candidate_ind).second;
        int set = candidates_set_way_samecore.at(candidate_ind).first;

        cacheMemoryBDIXORStats.xorChoiceCt_sameCore.sample(candidates_set_way_samecore.size());
        cacheMemoryBDIXORStats.xorChoiceCt.sample(candidates_set_way.size());

        candidates_set_way_samecore.clear();
        candidates_set_way.clear();
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_biasedRandom() <same core> rand to data %d,%d\n",set,way);
        cacheMemoryBDIXORStats.XORChoice_sameCore += 1;

        assert(m_cache_data[set][way] != nullptr);
        AbstractCacheEntry* tag = m_data_head_tag_ptr[set][way];
        assert(tag != nullptr);
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_biasedRandom() <same core> returning tag addr %llx\n",tag->m_Address);
        return tag->m_Address;
    }
    else {
        assert(candidates_set_way.size() > 0);
        int candidate_ind = rand() % candidates_set_way.size();
        int way = candidates_set_way.at(candidate_ind).second;
        int set = candidates_set_way.at(candidate_ind).first;

        cacheMemoryBDIXORStats.xorChoiceCt.sample(candidates_set_way.size());

        candidates_set_way.clear();
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_biasedRandom() rand to data %d,%d\n",set,way);
        cacheMemoryBDIXORStats.XORChoice_pureRandom += 1;

        assert(m_cache_data[set][way] != nullptr);
        AbstractCacheEntry* tag = m_data_head_tag_ptr[set][way];
        assert(tag != nullptr);
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_biasedRandom() returning tag addr %llx\n",tag->m_Address);
        return tag->m_Address;
    }
}

/* Favor same core xor. If unavailable, random select candidate
*/
Addr
CacheMemoryBDIXOR::getXORChoiceAddr_random_favor_sameCore_getX(Addr address, MachineID requestor)
{
    int set = addressToCacheSetData(address);
    std::vector<std::pair<int,int>> candidates_set_way_samecore;
    std::vector<std::pair<int,int>> candidates_set_way;
    
    // add all valid candidates
    if (m_search_in_set == true) {
        for (int i=0; i < m_num_seg_per_set; i++) {
            if (m_cache_data[set][i] != nullptr) {
                AbstractCacheEntry* tag = m_data_head_tag_ptr[set][i];
                bool isSharer = false;
                bool isOwner = false;
                L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                if (tag_cast != nullptr) {
                    isSharer = tag_cast->m_Sharers.isElement(requestor);
                    isOwner = tag_cast->m_Exclusive == requestor;
                } else {
                    assert(false);
                }
                // if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()] && isGoodState) {
                if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()] 
                    && tag_cast->m_Sharers.count() > 0 && 
                    tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT &&
                    tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT_MB &&
                    tag_cast->getCacheState() != L2Cache_State::L2Cache_State_SS_MB) {
                    // choose among the unpaired and can xored candidates
                    candidates_set_way.push_back(std::make_pair(set,i));
                    if (isOwner) {
                        candidates_set_way_samecore.push_back(std::make_pair(set,i)); 
                        DPRINTF(RubyCacheBDIXORSelection, 
                            "tag[%d,%d](%llx) is owner; <%s>; %s\n",tag->getSet(), tag->getWay(), 
                            tag->m_Address ,tag_cast->getCacheState(),tag_cast->m_Exclusive);
                    }
                    else if (isSharer) { 
                        candidates_set_way_samecore.push_back(std::make_pair(set,i)); 
                        DPRINTF(RubyCacheBDIXORSelection, 
                            "tag[%d,%d](%llx) is a sharer; <%s>; %s\n",tag->getSet(), tag->getWay(), 
                            tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Sharers);
                    }
                    else {
                        DPRINTF(RubyCacheBDIXORSelection, 
                            "tag[%d,%d](%llx) not a sharer nor owner; <%s>; %s;%s != %s\n",tag->getSet(), tag->getWay(), 
                            tag->m_Address, tag_cast->getCacheState(),tag_cast->m_Sharers, requestor,tag_cast->m_Exclusive);
                    }
                }
            } 
        }
    }
    else {
        for (int j=0; j < m_data_array_set; j++) {
            for (int i=0; i< m_num_seg_per_set; i++) {
                if (m_cache_data[j][i] != nullptr) {
                    AbstractCacheEntry* tag = m_data_head_tag_ptr[j][i];
                    bool isSharer = false;
                    bool isOwner = false;
                    L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                    if (tag_cast != nullptr) {
                        isSharer = tag_cast->m_Sharers.isElement(requestor);
                        isOwner = tag_cast->m_Exclusive == requestor;
                    } else {
                        assert(false);
                    }

                    if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()] && 
                        tag_cast->m_Sharers.count() > 0 && 
                        tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT &&
                        tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT_MB &&
                        tag_cast->getCacheState() != L2Cache_State::L2Cache_State_SS_MB) {
                        candidates_set_way.push_back(std::make_pair(j,i));
                        if (isOwner) {
                            candidates_set_way_samecore.push_back(std::make_pair(j,i)); 
                            DPRINTF(RubyCacheBDIXORSelection, 
                                "data[%d,%d]->tag[%d,%d](%llx) is owner; <%s>; %s\n",j,i,tag->getSet(), tag->getWay(), 
                                tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Exclusive);
                        }
                        else if (isSharer) { 
                            candidates_set_way_samecore.push_back(std::make_pair(j,i)); 
                            DPRINTF(RubyCacheBDIXORSelection, 
                                "data[%d,%d]->tag[%d,%d](%llx) is a sharer; <%s>; %s\n",j,i,tag->getSet(), tag->getWay(), 
                                tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Sharers);
                        }
                        else {
                            DPRINTF(RubyCacheBDIXORSelection, 
                                "data[%d,%d]->tag[%d,%d](%llx) not a sharer nor owner; <%s>; %s;%s != %s\n",j,i,tag->getSet(), tag->getWay(), 
                                tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Sharers, requestor,tag_cast->m_Exclusive);
                        }
                    }
                }
            }
        }
    }

    // select a candidate randomly
    if (candidates_set_way_samecore.size() > 0) {
        int candidate_ind = rand() % candidates_set_way_samecore.size();
        int way = candidates_set_way_samecore.at(candidate_ind).second;
        int set = candidates_set_way_samecore.at(candidate_ind).first;

        cacheMemoryBDIXORStats.xorChoiceCt_sameCore.sample(candidates_set_way_samecore.size());
        cacheMemoryBDIXORStats.xorChoiceCt.sample(candidates_set_way.size());

        candidates_set_way_samecore.clear();
        candidates_set_way.clear();
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_random_favor_sameCore_getX() <same core> rand to data %d,%d\n",set,way);
        cacheMemoryBDIXORStats.XORChoice_sameCore += 1;

        assert(m_cache_data[set][way] != nullptr);
        AbstractCacheEntry* tag = m_data_head_tag_ptr[set][way];
        assert(tag != nullptr);
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_random_favor_sameCore_getX() <same core> returning tag addr %llx\n",tag->m_Address);
        return tag->m_Address;
    }
    else {
        assert(candidates_set_way.size() > 0);
        int candidate_ind = rand() % candidates_set_way.size();
        int way = candidates_set_way.at(candidate_ind).second;
        int set = candidates_set_way.at(candidate_ind).first;

        cacheMemoryBDIXORStats.xorChoiceCt.sample(candidates_set_way.size());

        candidates_set_way.clear();
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_random_favor_sameCore_getX() rand to data %d,%d\n",set,way);
        cacheMemoryBDIXORStats.XORChoice_pureRandom += 1;

        assert(m_cache_data[set][way] != nullptr);
        AbstractCacheEntry* tag = m_data_head_tag_ptr[set][way];
        assert(tag != nullptr);
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_random_favor_sameCore_getX() returning tag addr %llx\n",tag->m_Address);
        return tag->m_Address;
    }
}

/* Favor same core xor. If unavailable, random select candidate
*/
Addr
CacheMemoryBDIXOR::getXORChoiceAddr_MRU_favor_sameCore(Addr address, MachineID requestor)
{
    int set = addressToCacheSetData(address);
    std::vector<std::pair<int,int>> candidates_set_way_samecore;
    std::vector<std::pair<int,int>> candidates_set_way;
    
    // add all valid candidates
    if (m_search_in_set == true) {
        for (int i=0; i < m_num_seg_per_set; i++) {
            if (m_cache_data[set][i] != nullptr) {
                AbstractCacheEntry* tag = m_data_head_tag_ptr[set][i];
                bool isSharer = false;
                bool isOwner = false;
                L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                if (tag_cast != nullptr) {
                    isSharer = tag_cast->m_Sharers.isElement(requestor);
                    isOwner = tag_cast->m_Exclusive == requestor;
                } else {
                    assert(false);
                }
                // if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()] && isGoodState) {
                if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()]) {
                    // choose among the unpaired and can xored candidates
                    candidates_set_way.push_back(std::make_pair(set,i));
                    if (isOwner) {
                        candidates_set_way_samecore.push_back(std::make_pair(set,i)); 
                        DPRINTF(RubyCacheBDIXORSelection, 
                            "tag[%d,%d](%llx) is owner; <%s>; %s\n",tag->getSet(), tag->getWay(), 
                            tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Exclusive);
                    }
                    else if (isSharer) { 
                        candidates_set_way_samecore.push_back(std::make_pair(set,i)); 
                        DPRINTF(RubyCacheBDIXORSelection, 
                            "tag[%d,%d](%llx) is a sharer; <%s>; %s\n",tag->getSet(), tag->getWay(), 
                            tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Sharers);
                    }
                    else {
                        DPRINTF(RubyCacheBDIXORSelection, 
                            "tag[%d,%d](%llx) not a sharer nor owner; <%s>; %s;%s != %s\n",tag->getSet(), tag->getWay(), 
                            tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Sharers, requestor,tag_cast->m_Exclusive);
                    }
                }
            } 
        }
    }
    else {
        for (int j=0; j < m_data_array_set; j++) {
            for (int i=0; i< m_num_seg_per_set; i++) {
                if (m_cache_data[j][i] != nullptr) {
                    AbstractCacheEntry* tag = m_data_head_tag_ptr[j][i];
                    bool isSharer = false;
                    bool isOwner = false;
                    L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                    if (tag_cast != nullptr) {
                        isSharer = tag_cast->m_Sharers.isElement(requestor);
                        isOwner = tag_cast->m_Exclusive == requestor;
                    } else {
                        assert(false);
                    }

                    if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()]) {
                        candidates_set_way.push_back(std::make_pair(j,i));
                        if (isOwner) {
                            candidates_set_way_samecore.push_back(std::make_pair(j,i)); 
                            DPRINTF(RubyCacheBDIXORSelection, 
                                "tag[%d,%d](%llx) is owner; <%s>; %s\n",tag->getSet(), tag->getWay(), 
                                tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Exclusive);
                        }
                        else if (isSharer) { 
                            candidates_set_way_samecore.push_back(std::make_pair(j,i)); 
                            DPRINTF(RubyCacheBDIXORSelection, 
                                "tag[%d,%d](%llx) is a sharer; <%s>; %s\n",tag->getSet(), tag->getWay(), 
                                tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Sharers);
                        }
                        else {
                            DPRINTF(RubyCacheBDIXORSelection, 
                                "tag[%d,%d](%llx) not a sharer nor owner; <%s>; %s;%s != %s\n",tag->getSet(), tag->getWay(), 
                                tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Sharers, requestor,tag_cast->m_Exclusive);
                        }
                    }
                }
            }
        }
    }

    // select a candidate
    if (candidates_set_way_samecore.size() > 0) {
        int candidate_ind = -1;
        Tick max_tick = 0;
        for(unsigned int i = 0; i < candidates_set_way_samecore.size(); i++)
        {
            int way_i = candidates_set_way_samecore.at(i).second;
            int set_i = candidates_set_way_samecore.at(i).first;
            AbstractCacheEntry* tag_i = m_data_head_tag_ptr[set_i][way_i];
            assert(tag_i != nullptr);
            if (tag_i->getLastAccess() >= max_tick) {
                max_tick = tag_i->getLastAccess();
                candidate_ind = i;
            }
        }
        assert(candidate_ind >= 0);
        int way = candidates_set_way_samecore.at(candidate_ind).second;
        int set = candidates_set_way_samecore.at(candidate_ind).first;

        cacheMemoryBDIXORStats.xorChoiceCt_sameCore.sample(candidates_set_way_samecore.size());
        cacheMemoryBDIXORStats.xorChoiceCt.sample(candidates_set_way.size());

        candidates_set_way_samecore.clear();
        candidates_set_way.clear();
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_MRU_favor_sameCore() <same core> MRU data %d,%d\n",set,way);
        cacheMemoryBDIXORStats.XORChoice_sameCore += 1;

        assert(m_cache_data[set][way] != nullptr);
        AbstractCacheEntry* tag = m_data_head_tag_ptr[set][way];
        assert(tag != nullptr);
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_MRU_favor_sameCore() <same core> returning tag addr %llx\n",tag->m_Address);
        return tag->m_Address;
    }
    else {
        assert(candidates_set_way.size() > 0);
        int candidate_ind = -1;
        Tick max_tick = 0;
        for(unsigned int i = 0; i < candidates_set_way.size(); i++)
        {
            int way_i = candidates_set_way.at(i).second;
            int set_i = candidates_set_way.at(i).first;
            AbstractCacheEntry* tag_i = m_data_head_tag_ptr[set_i][way_i];
            assert(tag_i != nullptr);
            if (tag_i->getLastAccess() >= max_tick) {
                max_tick = tag_i->getLastAccess();
                candidate_ind = i;
            }
        }
        assert(candidate_ind >= 0);
        int way = candidates_set_way.at(candidate_ind).second;
        int set = candidates_set_way.at(candidate_ind).first;

        cacheMemoryBDIXORStats.xorChoiceCt.sample(candidates_set_way.size());

        candidates_set_way.clear();
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_MRU_favor_sameCore() MRU data %d,%d\n",set,way);
        cacheMemoryBDIXORStats.XORChoice_pureRandom += 1;

        assert(m_cache_data[set][way] != nullptr);
        AbstractCacheEntry* tag = m_data_head_tag_ptr[set][way];
        assert(tag != nullptr);
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_MRU_favor_sameCore() returning tag addr %llx\n",tag->m_Address);
        return tag->m_Address;
    }
}

/* Favor same core xor. If unavailable, random select candidate
*/
Addr
CacheMemoryBDIXOR::getXORChoiceAddr_MRU_favor_sameCore_getX(Addr address, MachineID requestor)
{
    int set = addressToCacheSetData(address);
    std::vector<std::pair<int,int>> candidates_set_way_samecore;
    std::vector<std::pair<int,int>> candidates_set_way;
    
    // add all valid candidates
    if (m_search_in_set == true) {
        for (int i=0; i < m_num_seg_per_set; i++) {
            if (m_cache_data[set][i] != nullptr) {
                AbstractCacheEntry* tag = m_data_head_tag_ptr[set][i];
                bool isSharer = false;
                bool isOwner = false;
                L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                if (tag_cast != nullptr) {
                    isSharer = tag_cast->m_Sharers.isElement(requestor);
                    isOwner = tag_cast->m_Exclusive == requestor;
                } else {
                    assert(false);
                }
                // if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()] && isGoodState) {
                if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()] && 
                    tag_cast->m_Sharers.count() > 0 && 
                    tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT &&
                    tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT_MB &&
                    tag_cast->getCacheState() != L2Cache_State::L2Cache_State_SS_MB) {
                    // choose among the unpaired and can xored candidates
                    candidates_set_way.push_back(std::make_pair(set,i));
                    if (isOwner) {
                        candidates_set_way_samecore.push_back(std::make_pair(set,i)); 
                        DPRINTF(RubyCacheBDIXORSelection, 
                            "tag[%d,%d](%llx) is owner; <%s>; %s\n",tag->getSet(), tag->getWay(), 
                            tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Exclusive);
                    }
                    else if (isSharer) { 
                        candidates_set_way_samecore.push_back(std::make_pair(set,i)); 
                        DPRINTF(RubyCacheBDIXORSelection, 
                            "tag[%d,%d](%llx) is a sharer; <%s>; %s\n",tag->getSet(), tag->getWay(), 
                            tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Sharers);
                    }
                    else {
                        DPRINTF(RubyCacheBDIXORSelection, 
                            "tag[%d,%d](%llx) not a sharer nor owner; <%s>; %s;%s != %s\n",tag->getSet(), tag->getWay(), 
                            tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Sharers, requestor,tag_cast->m_Exclusive);
                    }
                }
            } 
        }
    }
    else {
        for (int j=0; j < m_data_array_set; j++) {
            for (int i=0; i< m_num_seg_per_set; i++) {
                if (m_cache_data[j][i] != nullptr) {
                    AbstractCacheEntry* tag = m_data_head_tag_ptr[j][i];
                    bool isSharer = false;
                    bool isOwner = false;
                    L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                    if (tag_cast != nullptr) {
                        isSharer = tag_cast->m_Sharers.isElement(requestor);
                        isOwner = tag_cast->m_Exclusive == requestor;
                    } else {
                        assert(false);
                    }

                    if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()] && 
                        tag_cast->m_Sharers.count() > 0 && 
                        tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT &&
                        tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT_MB &&
                        tag_cast->getCacheState() != L2Cache_State::L2Cache_State_SS_MB) {
                        candidates_set_way.push_back(std::make_pair(j,i));
                        if (isOwner) {
                            candidates_set_way_samecore.push_back(std::make_pair(j,i)); 
                            DPRINTF(RubyCacheBDIXORSelection, 
                                "tag[%d,%d](%llx) is owner; <%s>; %s\n",tag->getSet(), tag->getWay(), 
                                tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Exclusive);
                        }
                        else if (isSharer) { 
                            candidates_set_way_samecore.push_back(std::make_pair(j,i)); 
                            DPRINTF(RubyCacheBDIXORSelection, 
                                "tag[%d,%d](%llx) is a sharer; <%s>; %s\n",tag->getSet(), tag->getWay(), 
                                tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Sharers);
                        }
                        else {
                            DPRINTF(RubyCacheBDIXORSelection, 
                                "tag[%d,%d](%llx) not a sharer nor owner; <%s>; %s;%s != %s\n",tag->getSet(), tag->getWay(), 
                                tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Sharers, requestor,tag_cast->m_Exclusive);
                        }
                    }
                }
            }
        }
    }

    // select a candidate
    if (candidates_set_way_samecore.size() > 0) {
        int candidate_ind = -1;
        Tick max_tick = 0;
        for(unsigned int i = 0; i < candidates_set_way_samecore.size(); i++)
        {
            int way_i = candidates_set_way_samecore.at(i).second;
            int set_i = candidates_set_way_samecore.at(i).first;
            AbstractCacheEntry* tag_i = m_data_head_tag_ptr[set_i][way_i];
            assert(tag_i != nullptr);
            if (tag_i->getLastAccess() >= max_tick) {
                max_tick = tag_i->getLastAccess();
                candidate_ind = i;
            }
        }
        assert(candidate_ind >= 0);
        int way = candidates_set_way_samecore.at(candidate_ind).second;
        int set = candidates_set_way_samecore.at(candidate_ind).first;

        cacheMemoryBDIXORStats.xorChoiceCt_sameCore.sample(candidates_set_way_samecore.size());
        cacheMemoryBDIXORStats.xorChoiceCt.sample(candidates_set_way.size());

        candidates_set_way_samecore.clear();
        candidates_set_way.clear();
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_MRU_favor_sameCore_getX() <same core> MRU data %d,%d\n",set,way);
        cacheMemoryBDIXORStats.XORChoice_sameCore += 1;

        assert(m_cache_data[set][way] != nullptr);
        AbstractCacheEntry* tag = m_data_head_tag_ptr[set][way];
        assert(tag != nullptr);
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_MRU_favor_sameCore_getX() <same core> returning tag addr %llx\n",tag->m_Address);
        return tag->m_Address;
    }
    else {
        assert(candidates_set_way.size() > 0);
        int candidate_ind = -1;
        Tick max_tick = 0;
        for(unsigned int i = 0; i < candidates_set_way.size(); i++)
        {
            int way_i = candidates_set_way.at(i).second;
            int set_i = candidates_set_way.at(i).first;
            AbstractCacheEntry* tag_i = m_data_head_tag_ptr[set_i][way_i];
            assert(tag_i != nullptr);
            if (tag_i->getLastAccess() >= max_tick) {
                max_tick = tag_i->getLastAccess();
                candidate_ind = i;
            }
        }
        assert(candidate_ind >= 0);
        int way = candidates_set_way.at(candidate_ind).second;
        int set = candidates_set_way.at(candidate_ind).first;

        cacheMemoryBDIXORStats.xorChoiceCt.sample(candidates_set_way.size());

        candidates_set_way.clear();
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_MRU_favor_sameCore_getX() MRU data %d,%d\n",set,way);
        cacheMemoryBDIXORStats.XORChoice_pureRandom += 1;

        assert(m_cache_data[set][way] != nullptr);
        AbstractCacheEntry* tag = m_data_head_tag_ptr[set][way];
        assert(tag != nullptr);
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_MRU_favor_sameCore_getX() returning tag addr %llx\n",tag->m_Address);
        return tag->m_Address;
    }
}

/* Favor same core xor. If unavailable, random select candidate
*/
Addr
CacheMemoryBDIXOR::getXORChoiceAddr_LRU_favor_sameCore(Addr address, MachineID requestor)
{
    int set = addressToCacheSetData(address);
    std::vector<std::pair<int,int>> candidates_set_way_samecore;
    std::vector<std::pair<int,int>> candidates_set_way;
    
    // add all valid candidates
    if (m_search_in_set == true) {
        for (int i=0; i < m_num_seg_per_set; i++) {
            if (m_cache_data[set][i] != nullptr) {
                AbstractCacheEntry* tag = m_data_head_tag_ptr[set][i];
                bool isSharer = false;
                bool isOwner = false;
                L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                if (tag_cast != nullptr) {
                    isSharer = tag_cast->m_Sharers.isElement(requestor);
                    isOwner = tag_cast->m_Exclusive == requestor;
                } else {
                    assert(false);
                }
                // if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()] && isGoodState) {
                if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()]) {
                    // choose among the unpaired and can xored candidates
                    candidates_set_way.push_back(std::make_pair(set,i));
                    if (isOwner) {
                        candidates_set_way_samecore.push_back(std::make_pair(set,i)); 
                        DPRINTF(RubyCacheBDIXORSelection, 
                            "tag[%d,%d](%llx) is owner; <%s>; %s\n",tag->getSet(), tag->getWay(), 
                            tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Exclusive);
                    }
                    else if (isSharer) { 
                        candidates_set_way_samecore.push_back(std::make_pair(set,i)); 
                        DPRINTF(RubyCacheBDIXORSelection, 
                            "tag[%d,%d](%llx) is a sharer; <%s>; %s\n",tag->getSet(), tag->getWay(), 
                            tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Sharers);
                    }
                    else {
                        DPRINTF(RubyCacheBDIXORSelection, 
                            "tag[%d,%d](%llx) not a sharer nor owner; <%s>; %s;%s != %s\n",tag->getSet(), tag->getWay(), 
                            tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Sharers, requestor,tag_cast->m_Exclusive);
                    }
                }
            } 
        }
    }
    else {
        for (int j=0; j < m_data_array_set; j++) {
            for (int i=0; i< m_num_seg_per_set; i++) {
                if (m_cache_data[j][i] != nullptr) {
                    AbstractCacheEntry* tag = m_data_head_tag_ptr[j][i];
                    bool isSharer = false;
                    bool isOwner = false;
                    L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                    if (tag_cast != nullptr) {
                        isSharer = tag_cast->m_Sharers.isElement(requestor);
                        isOwner = tag_cast->m_Exclusive == requestor;
                    } else {
                        assert(false);
                    }

                    if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()]) {
                        candidates_set_way.push_back(std::make_pair(j,i));
                        if (isOwner) {
                            candidates_set_way_samecore.push_back(std::make_pair(j,i)); 
                            DPRINTF(RubyCacheBDIXORSelection, 
                                "tag[%d,%d](%llx) is owner; <%s>; %s\n",tag->getSet(), tag->getWay(), 
                                tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Exclusive);
                        }
                        else if (isSharer) { 
                            candidates_set_way_samecore.push_back(std::make_pair(j,i)); 
                            DPRINTF(RubyCacheBDIXORSelection, 
                                "tag[%d,%d](%llx) is a sharer; <%s>; %s\n",tag->getSet(), tag->getWay(), 
                                tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Sharers);
                        }
                        else {
                            DPRINTF(RubyCacheBDIXORSelection, 
                                "tag[%d,%d](%llx) not a sharer nor owner; <%s>; %s;%s != %s\n",tag->getSet(), tag->getWay(), 
                                tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Sharers, requestor,tag_cast->m_Exclusive);
                        }
                    }
                }
            }
        }
    }

    // select a candidate
    if (candidates_set_way_samecore.size() > 0) {
        int candidate_ind = -1;
        Tick min_tick = MaxTick;
        for(unsigned int i = 0; i < candidates_set_way_samecore.size(); i++)
        {
            int way_i = candidates_set_way_samecore.at(i).second;
            int set_i = candidates_set_way_samecore.at(i).first;
            AbstractCacheEntry* tag_i = m_data_head_tag_ptr[set_i][way_i];
            assert(tag_i != nullptr);
            if (tag_i->getLastAccess() <= min_tick) {
                candidate_ind = i;
                min_tick = tag_i->getLastAccess();
            }
        }
        assert(candidate_ind >= 0);
        int way = candidates_set_way_samecore.at(candidate_ind).second;
        int set = candidates_set_way_samecore.at(candidate_ind).first;

        cacheMemoryBDIXORStats.xorChoiceCt_sameCore.sample(candidates_set_way_samecore.size());
        cacheMemoryBDIXORStats.xorChoiceCt.sample(candidates_set_way.size());

        candidates_set_way_samecore.clear();
        candidates_set_way.clear();
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_LRU_favor_sameCore() <same core> LRU data %d,%d\n",set,way);
        cacheMemoryBDIXORStats.XORChoice_sameCore += 1;

        assert(m_cache_data[set][way] != nullptr);
        AbstractCacheEntry* tag = m_data_head_tag_ptr[set][way];
        assert(tag != nullptr);
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_LRU_favor_sameCore() <same core> returning tag addr %llx\n",tag->m_Address);
        return tag->m_Address;
    }
    else {
        assert(candidates_set_way.size() > 0);
        int candidate_ind = -1;
        Tick min_tick = MaxTick;
        for(unsigned int i = 0; i < candidates_set_way.size(); i++)
        {
            int way_i = candidates_set_way.at(i).second;
            int set_i = candidates_set_way.at(i).first;
            AbstractCacheEntry* tag_i = m_data_head_tag_ptr[set_i][way_i];
            assert(tag_i != nullptr);
            if (tag_i->getLastAccess() <= min_tick) {
                min_tick = tag_i->getLastAccess();
                candidate_ind = i;
            }
        }
        assert(candidate_ind >= 0);
        int way = candidates_set_way.at(candidate_ind).second;
        int set = candidates_set_way.at(candidate_ind).first;

        cacheMemoryBDIXORStats.xorChoiceCt.sample(candidates_set_way.size());

        candidates_set_way.clear();
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_biasedRandom() LRU data %d,%d\n",set,way);
        cacheMemoryBDIXORStats.XORChoice_pureRandom += 1;

        assert(m_cache_data[set][way] != nullptr);
        AbstractCacheEntry* tag = m_data_head_tag_ptr[set][way];
        assert(tag != nullptr);
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_LRU_favor_sameCore() returning tag addr %llx\n",tag->m_Address);
        return tag->m_Address;
    }
}


/* Favor same core xor. If unavailable, random select candidate
*/
Addr
CacheMemoryBDIXOR::getXORChoiceAddr_LRU_favor_sameCore_getX(Addr address, MachineID requestor)
{
    int set = addressToCacheSetData(address);
    std::vector<std::pair<int,int>> candidates_set_way_samecore;
    std::vector<std::pair<int,int>> candidates_set_way;
    
    // add all valid candidates
    if (m_search_in_set == true) {
        for (int i=0; i < m_num_seg_per_set; i++) {
            if (m_cache_data[set][i] != nullptr) {
                AbstractCacheEntry* tag = m_data_head_tag_ptr[set][i];
                bool isSharer = false;
                bool isOwner = false;
                L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                if (tag_cast != nullptr) {
                    isSharer = tag_cast->m_Sharers.isElement(requestor);
                    isOwner = tag_cast->m_Exclusive == requestor;
                } else {
                    assert(false);
                }
                // if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()] && isGoodState) {
                if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()] && 
                    tag_cast->m_Sharers.count() > 0 && 
                    tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT &&
                    tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT_MB &&
                    tag_cast->getCacheState() != L2Cache_State::L2Cache_State_SS_MB) {
                    // choose among the unpaired and can xored candidates
                    candidates_set_way.push_back(std::make_pair(set,i));
                    if (isOwner) {
                        candidates_set_way_samecore.push_back(std::make_pair(set,i)); 
                        DPRINTF(RubyCacheBDIXORSelection, 
                            "tag[%d,%d](%llx) is owner; <%s>; %s\n",tag->getSet(), tag->getWay(), 
                            tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Exclusive);
                    }
                    else if (isSharer) { 
                        candidates_set_way_samecore.push_back(std::make_pair(set,i)); 
                        DPRINTF(RubyCacheBDIXORSelection, 
                            "tag[%d,%d](%llx) is a sharer; <%s>; %s\n",tag->getSet(), tag->getWay(), 
                            tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Sharers);
                    }
                    else {
                        DPRINTF(RubyCacheBDIXORSelection, 
                            "tag[%d,%d](%llx) not a sharer nor owner; <%s>; %s;%s != %s\n",tag->getSet(), tag->getWay(), 
                            tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Sharers, requestor,tag_cast->m_Exclusive);
                    }
                }
            } 
        }
    }
    else {
        for (int j=0; j < m_data_array_set; j++) {
            for (int i=0; i< m_num_seg_per_set; i++) {
                if (m_cache_data[j][i] != nullptr) {
                    AbstractCacheEntry* tag = m_data_head_tag_ptr[j][i];
                    bool isSharer = false;
                    bool isOwner = false;
                    L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(tag);
                    if (tag_cast != nullptr) {
                        isSharer = tag_cast->m_Sharers.isElement(requestor);
                        isOwner = tag_cast->m_Exclusive == requestor;
                    } else {
                        assert(false);
                    }

                    if (isUnpaired(tag) && m_tag_can_xor[tag->getSet()][tag->getWay()] && 
                        tag_cast->m_Sharers.count() > 0 && 
                        tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT &&
                        tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT_MB &&
                        tag_cast->getCacheState() != L2Cache_State::L2Cache_State_SS_MB) {
                        candidates_set_way.push_back(std::make_pair(j,i));
                        if (isOwner) {
                            candidates_set_way_samecore.push_back(std::make_pair(j,i)); 
                            DPRINTF(RubyCacheBDIXORSelection, 
                                "tag[%d,%d](%llx) is owner; <%s>; %s\n",tag->getSet(), tag->getWay(), 
                                tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Exclusive);
                        }
                        else if (isSharer) { 
                            candidates_set_way_samecore.push_back(std::make_pair(j,i)); 
                            DPRINTF(RubyCacheBDIXORSelection, 
                                "tag[%d,%d](%llx) is a sharer; <%s>; %s\n",tag->getSet(), tag->getWay(), 
                                tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Sharers);
                        }
                        else {
                            DPRINTF(RubyCacheBDIXORSelection, 
                                "tag[%d,%d](%llx) not a sharer nor owner; <%s>; %s;%s != %s\n",tag->getSet(), tag->getWay(), 
                                tag->m_Address,tag_cast->getCacheState(),tag_cast->m_Sharers, requestor,tag_cast->m_Exclusive);
                        }
                    }
                }
            }
        }
    }

    // select a candidate
    if (candidates_set_way_samecore.size() > 0) {
        int candidate_ind = -1;
        Tick min_tick = MaxTick;
        for(unsigned int i = 0; i < candidates_set_way_samecore.size(); i++)
        {
            int way_i = candidates_set_way_samecore.at(i).second;
            int set_i = candidates_set_way_samecore.at(i).first;
            AbstractCacheEntry* tag_i = m_data_head_tag_ptr[set_i][way_i];
            assert(tag_i != nullptr);
            if (tag_i->getLastAccess() <= min_tick) {
                candidate_ind = i;
                min_tick = tag_i->getLastAccess();
            }
        }
        assert(candidate_ind >= 0);
        int way = candidates_set_way_samecore.at(candidate_ind).second;
        int set = candidates_set_way_samecore.at(candidate_ind).first;

        cacheMemoryBDIXORStats.xorChoiceCt_sameCore.sample(candidates_set_way_samecore.size());
        cacheMemoryBDIXORStats.xorChoiceCt.sample(candidates_set_way.size());

        candidates_set_way_samecore.clear();
        candidates_set_way.clear();
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_LRU_favor_sameCore_getX() <same core> LRU data %d,%d\n",set,way);
        cacheMemoryBDIXORStats.XORChoice_sameCore += 1;

        assert(m_cache_data[set][way] != nullptr);
        AbstractCacheEntry* tag = m_data_head_tag_ptr[set][way];
        assert(tag != nullptr);
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_LRU_favor_sameCore_getX() <same core> returning tag addr %llx\n",tag->m_Address);
        return tag->m_Address;
    }
    else {
        assert(candidates_set_way.size() > 0);
        int candidate_ind = -1;
        Tick min_tick = MaxTick;
        for(unsigned int i = 0; i < candidates_set_way.size(); i++)
        {
            int way_i = candidates_set_way.at(i).second;
            int set_i = candidates_set_way.at(i).first;
            AbstractCacheEntry* tag_i = m_data_head_tag_ptr[set_i][way_i];
            assert(tag_i != nullptr);
            if (tag_i->getLastAccess() <= min_tick) {
                min_tick = tag_i->getLastAccess();
                candidate_ind = i;
            }
        }
        assert(candidate_ind >= 0);
        int way = candidates_set_way.at(candidate_ind).second;
        int set = candidates_set_way.at(candidate_ind).first;

        cacheMemoryBDIXORStats.xorChoiceCt.sample(candidates_set_way.size());

        candidates_set_way.clear();
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_biasedRandom() LRU data %d,%d\n",set,way);
        cacheMemoryBDIXORStats.XORChoice_pureRandom += 1;

        assert(m_cache_data[set][way] != nullptr);
        AbstractCacheEntry* tag = m_data_head_tag_ptr[set][way];
        assert(tag != nullptr);
        DPRINTF(RubyCacheBDIXORSelection, "getXORChoiceAddr_LRU_favor_sameCore() returning tag addr %llx\n",tag->m_Address);
        return tag->m_Address;
    }
}


Addr
CacheMemoryBDIXOR::getXORChoiceAddr(Addr address, MachineID requestor)
{
    switch (m_xor_policy_id) {
        case 1:
            return getXORChoiceAddr_random_favor_sameCore(address, requestor);
        case 2:
            return getXORChoiceAddr_random_favor_sameCore(address, requestor);
        case 3:
            return getXORChoiceAddr_MRU_favor_sameCore(address, requestor);
        case 4:
            return getXORChoiceAddr_MRU_favor_sameCore(address, requestor);
        case 5:
            return getXORChoiceAddr_LRU_favor_sameCore(address, requestor);
        case 6:
            return getXORChoiceAddr_LRU_favor_sameCore(address, requestor);
    }

    panic("unknown xor policy id %d\n",m_xor_policy_id);
}
Addr
CacheMemoryBDIXOR::getXORChoiceAddr_getX(Addr address, MachineID requestor)
{
    switch (m_xor_policy_id) {
        case 1:
            return getXORChoiceAddr_random_favor_sameCore_getX(address, requestor);
        case 2:
            return getXORChoiceAddr_random_favor_sameCore_getX(address, requestor);
        case 3:
            return getXORChoiceAddr_MRU_favor_sameCore_getX(address, requestor);
        case 4:
            return getXORChoiceAddr_MRU_favor_sameCore_getX(address, requestor);
        case 5:
            return getXORChoiceAddr_LRU_favor_sameCore_getX(address, requestor);
        case 6:
            return getXORChoiceAddr_LRU_favor_sameCore_getX(address, requestor);
    }

    panic("unknown xor policy id %d\n",m_xor_policy_id);
}

bool
CacheMemoryBDIXOR::isPartnerReplBlocked(Addr requested_address) const {
    auto it = m_tempLink.find(requested_address);
    if (it != m_tempLink.end()) {
        return true;
    }
    else {
        return false;
    }
}

/* Used to check if the partner is shared or not. if partner is not 
shared, aka., data copy can be found no where, then we quit
promoting the xoring data from S to MT.
*/
bool
CacheMemoryBDIXOR::isPartnerShared(Addr requested_address) {
    // lookup data to be linked
    Addr existing;
    auto it = m_tempLink.find(requested_address);
    if (it != m_tempLink.end()) {
        existing = it->second;
    }
    else {
        panic("isPartnerShared():did you forget to settupTempLink?");
    }
    AbstractCacheEntry* existing_tagEntry = lookup(existing);
    assert(existing_tagEntry != nullptr);
    L2Cache_Entry * existing_tagEntry_cast = dynamic_cast<L2Cache_Entry *>(existing_tagEntry);
    return existing_tagEntry_cast->getCacheState()!=L2Cache_State::L2Cache_State_MT_br 
        && existing_tagEntry_cast->getCacheState()!=L2Cache_State::L2Cache_State_MT_MB_br 
        && existing_tagEntry_cast->getCacheState()!=L2Cache_State::L2Cache_State_SS_MB_br 
        && existing_tagEntry_cast->m_Sharers.count() > 0;
}

bool
CacheMemoryBDIXOR::isPartnerReplBlocked_memdata(Addr requested_address)
{
    Addr existing_addr;
    auto it = m_tempLink.find(requested_address);
    if (it != m_tempLink.end()) {
        existing_addr = it->second;
    }
    else {
        // m_tempLink[req] -x> existing 
        return false;
    }
    auto it2 = m_tempLink.find(existing_addr);
    if (it2 != m_tempLink.end()) {
        // m_tempLink[req] -> existing 
        // m_tempLink[existing] -> req
        return true;
    }
    else {
        // m_tempLink[req] -> existing 
        // m_tempLink[existing] -x> req 
        return false;
    }
}

void
CacheMemoryBDIXOR::linkDataToTag_existing(Addr address, AbstractCacheEntry* existing_dataEntry, int data_size) {
    DPRINTF(RubyCacheBDIXOR, "=====linkDataToTag_existing() in CacheMemoryBDIXOR=====\n");
    int num_seg_per_data = divCeil(data_size,m_segment_size);
    DPRINTF(RubyCacheBDIXOR, "0.linkDataToTag:data_size=%dB, equivalent to %d segment\n", data_size, num_seg_per_data);

    assert(address == makeLineAddress(address));
    assert(CacheMemory::isTagPresent(address));
    assert(cacheAvailData(address, data_size));
    
    //lookup tag
    AbstractCacheEntry* tagEntry = lookup(address);
    assert(tagEntry != nullptr);
    uint32_t tagSet = tagEntry->getSet();
    uint32_t tagWay = tagEntry->getWay();
    assert(m_cache[tagSet][tagWay]->m_Address == address);

    existing_dataEntry->setLastAccess(curTick());
    m_replacementPolicy_ptr_data->touch(existing_dataEntry->replacementData);
    DPRINTF(RubyCacheBDIXOR, "   1.touched existing data block's repl\n");
    m_tag_data_ptr[tagSet][tagWay] = existing_dataEntry; //tag to data
    DPRINTF(RubyCacheBDIXOR, "   2.set tag to data pointer\n");

    AbstractCacheEntry* headTagEntry = m_data_head_tag_ptr[existing_dataEntry->getSet()][existing_dataEntry->getWay()]; 
    addToTail(headTagEntry, tagEntry);
    DPRINTF(RubyCacheBDIXOR, "   3.added tag to tag list\n");
    m_data_index[address] = existing_dataEntry->getWay();
    DPRINTF(RubyCacheBDIXOR, "   4.updated data_index\n");
    m_data_cntr[existing_dataEntry->getSet()][existing_dataEntry->getWay()] += 1;
    assert(m_data_cntr[existing_dataEntry->getSet()][existing_dataEntry->getWay()] == 2);
    
    DPRINTF(RubyCacheBDIXOR, "   5.set tag->seg cntr\n");
    m_tag_seg_cntr[tagSet][tagWay] = m_tag_seg_cntr[headTagEntry->getSet()][headTagEntry->getWay()];
}

void
CacheMemoryBDIXOR::linkDataToTag_existing(Addr address, int data_size) {
    DPRINTF(RubyCacheBDIXOR, "=====linkDataToTag_existing() no dataentry ptr version in CacheMemoryBDIXOR=====\n");
    int num_seg_per_data = divCeil(data_size,m_segment_size);
    DPRINTF(RubyCacheBDIXOR, "0.linkDataToTag_existing() no dataentry ptr version:data_size=%dB, equivalent to %d segment\n", 
    data_size, num_seg_per_data);

    assert(address == makeLineAddress(address));
    assert(CacheMemory::isTagPresent(address));
    // assert(cacheAvailData(address, data_size));
    
    //lookup tag
    AbstractCacheEntry* tagEntry = lookup(address);
    assert(tagEntry != nullptr);
    uint32_t tagSet = tagEntry->getSet();
    uint32_t tagWay = tagEntry->getWay();
    assert(m_cache[tagSet][tagWay]->m_Address == address);

    // lookup data to be linked
    Addr existing;
    auto it = m_tempLink.find(address);
    if (it != m_tempLink.end()) {
        existing = it->second;
    }
    else {
        panic("did you forget to settupTempLink?");
    }
    AbstractCacheEntry* existing_tagEntry = lookup(existing);
    assert(existing_tagEntry != nullptr);
    AbstractCacheEntry* existing_dataEntry = m_tag_data_ptr[existing_tagEntry->getSet()][existing_tagEntry->getWay()];
    assert(existing_dataEntry != nullptr);

    existing_dataEntry->setLastAccess(curTick());
    m_replacementPolicy_ptr_data->touch(existing_dataEntry->replacementData);
    DPRINTF(RubyCacheBDIXOR, "   1.touched existing data block's repl\n");
    m_tag_data_ptr[tagSet][tagWay] = existing_dataEntry; //tag to data
    DPRINTF(RubyCacheBDIXOR, "   2.set tag to data pointer: tag[%d,%d]->data[%d,%d]\n", 
        tagSet,tagWay, existing_dataEntry->getSet(), existing_dataEntry->getWay());

    addToTail(existing_tagEntry, tagEntry);
    DPRINTF(RubyCacheBDIXOR, "   3.added tag to tag list\n");
    m_data_index[address] = existing_dataEntry->getWay();
    DPRINTF(RubyCacheBDIXOR, "   4.updated data_index\n");
    m_data_cntr[existing_dataEntry->getSet()][existing_dataEntry->getWay()] += 1;
    assert(m_data_cntr[existing_dataEntry->getSet()][existing_dataEntry->getWay()] == 2);
    
    DPRINTF(RubyCacheBDIXOR, "   5.set tag->seg cntr\n");
    m_tag_seg_cntr[tagSet][tagWay] = m_tag_seg_cntr[existing_tagEntry->getSet()][existing_tagEntry->getWay()];
}

void
CacheMemoryBDIXOR::settupTempLink(Addr requested_address, Addr existing_address)
{
    m_tempLink[existing_address] = requested_address;
}


void
CacheMemoryBDIXOR::validateTempLink(Addr existing_address)
{
    auto it = m_tempLink.find(existing_address);
    if (it != m_tempLink.end()) {
        Addr temp_link_addr = it->second;
        // add backward link
        m_tempLink[temp_link_addr] = existing_address;
    }
    else {
        panic("did you forget to settupTempLink?");
    }
}

Addr
CacheMemoryBDIXOR::getExistingAddr(Addr requested_address) const
{
    auto it = m_tempLink.find(requested_address);
    if (it != m_tempLink.end()) {
        return it->second;
    }
    panic("did you forget to validateTempLink?");
}

void
CacheMemoryBDIXOR::unblockRepl(Addr existing_address)
{
    auto it = m_tempLink.find(existing_address);
    assert (it != m_tempLink.end());
    m_tempLink.erase(existing_address);
}

void
CacheMemoryBDIXOR::rmReqToExisting(Addr req_address)
{
    m_tempLink.erase(req_address);
}

void
CacheMemoryBDIXOR::unlinkDataToTag(Addr address) {
    DPRINTF(RubyCacheBDIXOR, "=====unlinkDataToTag() in CacheMemoryBDIXOR: %#x=====\n", address);
    AbstractCacheEntry* tagEntry = CacheMemory::lookup(address);
    assert(tagEntry != nullptr);
    uint32_t tagSet = tagEntry->getSet();
    uint32_t tagWay = tagEntry->getWay();
    AbstractCacheEntry* dataEntry = m_tag_data_ptr[tagSet][tagWay];
    assert(dataEntry != NULL);
    
    //locate data entry's index
    uint32_t dataSet = dataEntry->getSet();
    uint32_t dataSeg = dataEntry->getWay();
    assert(dataSeg < m_num_seg_per_set);

    DPRINTF(RubyCacheBDIXOR, "  0.data is at [%d,%d]\n", dataSet, dataSeg);

    if (m_data_cntr[dataSet][dataSeg] == 1) {
        DPRINTF(RubyCacheBDIXOR, "  1.no tag points to this data, deallocating...\n");
        //reset data's replacement data
        m_replacementPolicy_ptr_data->invalidate(dataEntry->replacementData);
        //delete data entry
        delete dataEntry;
        m_data_index.erase(address);
        
        //reset ptrs
        DPRINTF(RubyCacheBDIXOR, "  1a.freeing up %d segs in data[%d]\n", 
            m_tag_seg_cntr[tagSet][tagWay], dataSet);
        m_data_set_vacancy[dataSet] += m_tag_seg_cntr[tagSet][tagWay]; // now vacant
        m_cache_data[dataSet][dataSeg] = NULL;
        m_tag_data_ptr[tagSet][tagWay] = NULL; //tag to data
        int seg_cntr = m_tag_seg_cntr[tagSet][tagWay];
        m_tag_seg_cntr[tagSet][tagWay] = 0; 
        m_data_head_tag_ptr[dataSet][dataSeg] = NULL;
        cacheMemoryDecoupledStats.numSegInUse -= seg_cntr;
        if (cacheMemoryDecoupledStats.numSegInUse.value() > cacheMemoryDecoupledStats.numSegInUse_max.value()) {
            cacheMemoryDecoupledStats.numSegInUse_max = cacheMemoryDecoupledStats.numSegInUse.value();
        }
    }
    else {
        removeFromList(m_data_head_tag_ptr[dataSet][dataSeg], tagEntry);
        m_tag_data_ptr[tagSet][tagWay] = NULL; //tag to data
        DPRINTF(RubyCacheBDIXOR, "  1.other tag still points to this data,address=%llx\n", m_data_head_tag_ptr[dataSet][dataSeg]->m_Address);
        m_data_index.erase(address);
        m_tag_seg_cntr[tagSet][tagWay] = 0; 
    }
    //decrement data cntr
    m_data_cntr[dataSet][dataSeg] -= 1;
}

AbstractCacheEntry* 
CacheMemoryBDIXOR::unlinkDataToTag_existing(Addr address) {
    DPRINTF(RubyCacheBDIXOR, "=====unlinkDataToTag_existing() in CacheMemoryBDIXOR: %#x=====\n", address);
    AbstractCacheEntry* tagEntry = CacheMemory::lookup(address);
    assert(tagEntry != nullptr);
    uint32_t tagSet = tagEntry->getSet();
    uint32_t tagWay = tagEntry->getWay();
    AbstractCacheEntry* dataEntry = m_tag_data_ptr[tagSet][tagWay];
    assert(dataEntry != NULL);
    
    //locate data entry's index
    uint32_t dataSet = dataEntry->getSet();
    uint32_t dataSeg = dataEntry->getWay();
    assert(dataSeg < m_num_seg_per_set);

    DPRINTF(RubyCacheBDIXOR, "  0.data is at [%d,%d]\n", dataSet, dataSeg);

    assert (m_data_cntr[dataSet][dataSeg] == 2);
    removeFromList(m_data_head_tag_ptr[dataSet][dataSeg], tagEntry);
    m_tag_data_ptr[tagSet][tagWay] = NULL; //tag to data
    DPRINTF(RubyCacheBDIXOR, "  1.other tag still points to this data\n");
    m_data_index.erase(address);
    m_tag_seg_cntr[tagSet][tagWay] = 0; 
    //decrement data cntr
    m_data_cntr[dataSet][dataSeg] -= 1;
    return dataEntry;
}

void
CacheMemoryBDIXOR::linkDataToTag(Addr address, AbstractCacheEntry* new_dataEntry, int data_size) {
    DPRINTF(RubyCacheBDIXOR, "=====linkDataToTag() in CacheMemoryBDIXOR=====\n");
    int num_seg_per_data = divCeil(data_size,m_segment_size);
    DPRINTF(RubyCacheBDIXOR, "0.linkDataToTag:data_size=%dB, equivalent to %d segment\n", data_size, num_seg_per_data);

    assert(address == makeLineAddress(address));
    assert(CacheMemory::isTagPresent(address));
    assert(cacheAvailData(address, data_size));
    DPRINTF(RubyCacheBDIXOR, "   1.address: %#x data filing...\n", address);
    
    //lookup tag
    AbstractCacheEntry* tagEntry = lookup(address);
    assert(tagEntry != nullptr);
    uint32_t tagSet = tagEntry->getSet();
    uint32_t tagWay = tagEntry->getWay();
    assert(m_cache[tagSet][tagWay]->m_Address == address);

    // Find the first open slot in data array
    int64_t dataSet = addressToCacheSetData(address);
    int free = m_data_set_vacancy[dataSet];
    if (free >= num_seg_per_data) {
        DPRINTF(RubyCacheBDIXOR, "   2.tag[%d,%d] will be linked to %d segments in data[%d]\n", 
            tagSet, tagWay, num_seg_per_data,dataSet);
    }
    else {
        DPRINTF(RubyCacheBDIXOR, "free(%d)<num_seg_per_data(%d)\n", free, num_seg_per_data);
        assert(false);
    }

    new_dataEntry->setLastAccess(curTick());
    m_tag_data_ptr[tagSet][tagWay] = new_dataEntry; //tag to data

    for (int j = 0; j < m_num_seg_per_set; j++) {
        if (m_cache_data[dataSet][j] == NULL) {
            DPRINTF(RubyCacheBDIXOR, "   3.tag[%d,%d] linking to data[%d,%d]\n", 
            tagSet, tagWay, dataSet, j);
            m_cache_data[dataSet][j] = new_dataEntry;  // Init entry
            m_tag_seg_cntr[tagSet][tagWay] += num_seg_per_data;
            m_data_head_tag_ptr[dataSet][j] = m_cache[tagSet][tagWay]; //data to tag
            m_data_cntr[dataSet][j] += 1;
            assert(m_data_cntr[dataSet][j] <= 1);
            m_data_set_vacancy[dataSet] -= num_seg_per_data;
            new_dataEntry->replacementData = replacement_data_for_data[dataSet][j];
            m_replacementPolicy_ptr_data->reset(new_dataEntry->replacementData);
            m_data_index[address] = j;

            new_dataEntry->setPosition(dataSet, j);

            cacheMemoryDecoupledStats.numSegInUse += num_seg_per_data;
            if (cacheMemoryDecoupledStats.numSegInUse.value() > cacheMemoryDecoupledStats.numSegInUse_max.value()) {
                cacheMemoryDecoupledStats.numSegInUse_max = cacheMemoryDecoupledStats.numSegInUse.value();
            }
            return;
        }
    }
    panic("linkDataToTag didn't find an available entry");
}

void
CacheMemoryBDIXOR::lockXOR(Addr address)
{
    AbstractCacheEntry* tagEntry = lookup(address);
    assert(tagEntry != nullptr);
    if (m_tag_can_xor[tagEntry->getSet()][tagEntry->getWay()] == false) {
        DPRINTF(RubyCacheBDIXOR, "%#x already xor locked!!! (set=%d,way=%d)\n", address, tagEntry->getSet(), tagEntry->getWay());
        assert(false);
    }
    m_tag_can_xor[tagEntry->getSet()][tagEntry->getWay()] = false;
    cacheMemoryBDIXORStats.numTagLocked += 1;
    DPRINTF(RubyCacheBDIXOR, "locked %#x, (set=%d,way=%d)\n", address, tagEntry->getSet(), tagEntry->getWay());
}
bool
CacheMemoryBDIXOR::isLockedXOR(Addr address)
{
    AbstractCacheEntry* tagEntry = lookup(address);
    assert(tagEntry != nullptr);
    return (!m_tag_can_xor[tagEntry->getSet()][tagEntry->getWay()]);
}

void
CacheMemoryBDIXOR::unlockXOR(Addr address)
{
    AbstractCacheEntry* tagEntry = lookup(address);
    assert(tagEntry != nullptr);
    if (m_tag_can_xor[tagEntry->getSet()][tagEntry->getWay()] == true) {
        DPRINTF(RubyCacheBDIXOR, "%#x already xor unlocked!!! (set=%d,way=%d)\n", address, tagEntry->getSet(), tagEntry->getWay());
        assert(false);
    }
    m_tag_can_xor[tagEntry->getSet()][tagEntry->getWay()] = true;
    cacheMemoryBDIXORStats.numTagLocked -= 1;
    DPRINTF(RubyCacheBDIXOR, "unlocked %#x, (set=%d,way=%d)\n", address, tagEntry->getSet(), tagEntry->getWay());
}

// Returns with the physical address of the conflicting cache line for data array
Addr
CacheMemoryBDIXOR::cacheProbeData(Addr address) const
{
    DPRINTF(RubyCacheBDIXOR, "cacheProbeData() in CacheMemoryBDIXOR\n");
    assert(address == makeLineAddress(address));
    assert(cacheAvail(address));

    int64_t dataSet = addressToCacheSetData(address);
    DPRINTF(RubyCacheBDIXOR, "  set in data: %d\n", dataSet);

    // collect replacement candidates
    std::vector<ReplaceableEntry*> candidates;
    for (int i = 0; i < m_num_seg_per_set; i++) {
        if (m_cache_data[dataSet][i] != NULL) {
            if (m_data_head_tag_ptr[dataSet][i]->m_Address != address) {
                    // if this entry is not null and not my own data, then consider as candidate
                    candidates.push_back(static_cast<ReplaceableEntry*>(
                                                                m_cache_data[dataSet][i]));
                    DPRINTF(RubyCacheBDIXOR, 
                    "       - data[%d,%d] added as candidate\n", dataSet, i);
            }
            else {
                DPRINTF(RubyCacheBDIXOR, 
                    "       - data[%d,%d] is myself, skipping\n", dataSet, i);
            }
        }
    }
    assert(candidates.size() > 0);
    DPRINTF(RubyCacheBDIXOR, "    arbitrating among %d candidates\n", candidates.size());

    ReplaceableEntry* victim = m_replacementPolicy_ptr_data->getVictim(candidates);
    assert(victim != NULL);
    uint32_t vSeg = m_num_seg_per_set;
    for (int j = 0; j < m_num_seg_per_set; j++) {
        if (m_cache_data[dataSet][j] != NULL && 
            victim == m_cache_data[dataSet][j]) {
            vSeg = j;
        }
    }
    assert(vSeg < m_num_seg_per_set);
    DPRINTF(RubyCacheBDIXOR, "  identified conflicting data[%d,%d]\n", 
    dataSet, vSeg);

    assert(m_data_head_tag_ptr[dataSet][vSeg] != NULL);
    DPRINTF(RubyCacheBDIXOR, "  identified its associated tag[%d,%d]\n", 
    m_data_head_tag_ptr[dataSet][vSeg]->getSet(),
    m_data_head_tag_ptr[dataSet][vSeg]->getWay());

    // I can not decide that i need to evict my own tag to make space for myself
    assert(m_data_head_tag_ptr[dataSet][vSeg]->m_Address != address);

    return m_data_head_tag_ptr[dataSet][vSeg]->m_Address;
}


// Returns with the physical address of the conflicting cache line
// excluding my own xor candidate
Addr
CacheMemoryBDIXOR::cacheProbeExcludePartner(Addr address) const
{
    DPRINTF(RubyCacheBDIXOR,"CacheMemoryBDIXOR::cacheProbeExcludePartner\n");
    assert(address == makeLineAddress(address));
    assert(!cacheAvail(address));

    bool look_for_partner = false;
    Addr partner_addr = 0;
    if (isPartnerReplBlocked(address)) {
        partner_addr = getExistingAddr(address);
        look_for_partner = true;
    }

    int64_t cacheSet = addressToCacheSet(address);
    std::vector<ReplaceableEntry*> candidates;
    for (int i = 0; i < m_cache_assoc; i++) {
        if (look_for_partner && partner_addr == m_cache[cacheSet][i]->m_Address) {
            DPRINTF(RubyCacheBDIXOR, 
                "this block at [%d,%d] has been selected as my xor partner, cannot select as candidate\n", 
                cacheSet,i);
            // assert(false);
            continue;
        }
        candidates.push_back(static_cast<ReplaceableEntry*>(
                                                       m_cache[cacheSet][i]));
    }
    return m_cache[cacheSet][m_replacementPolicy_ptr->
                        getVictim(candidates)->getWay()]->m_Address;
}

// Returns true if there is enough space to coallocate, i.e., no need to replace!
bool
CacheMemoryBDIXOR::cacheCanCoallocate(Addr address, int data_size) const
{
    DPRINTF(RubyCacheBDIXOR, "cacheCanCoallocate() in CacheMemoryBDIXOR: %#x\n",address);
    int num_seg_per_data = divCeil(data_size,m_segment_size);
    DPRINTF(RubyCacheBDIXOR, "cacheCanCoallocate:data_size=%dB, equivalent to %d segment\n", data_size, num_seg_per_data);
    assert(address == makeLineAddress(address));

    int64_t cacheSet = CacheMemory::addressToCacheSet(address);
    bool found_address_match = false;

    for (int i = 0; i < m_cache_assoc; i++) {
        AbstractCacheEntry* entry = m_cache[cacheSet][i];
        if (entry != NULL) {
            if (entry->m_Address == address) {
                found_address_match = true;
                uint32_t set = entry->getSet();
                uint32_t way = entry->getWay();
                int already_has = m_tag_seg_cntr[set][way];
                if (already_has >= num_seg_per_data) {
                    // Already in the cache and there is data
                    DPRINTF(RubyCacheBDIXOR, 
                        "   address %#x already exists and already has enough %d data segment(s)=>can coallocate\n",
                        address, already_has);
                    return true;
                }
                else {
                    // already incache but need to allocate more data
                    AbstractCacheEntry* dataEntry = m_tag_data_ptr[set][way];
                    uint32_t dataset = dataEntry->getSet();
                    int has_free = m_data_set_vacancy[dataset];
                    if ((already_has + has_free) >= num_seg_per_data) {
                        DPRINTF(RubyCacheBDIXOR, 
                        "   address %#x already exists, has %d data segment(s), also %d free.=>can coallocate\n",
                        address, already_has, has_free);
                        return true;
                    }
                    else {
                        DPRINTF(RubyCacheBDIXOR, 
                        "   address %#x already exists but only has %d data segment(s) now and %d free.\n",
                        address, already_has, has_free);
                    }
                }
            }
        }
    }
    assert(found_address_match);

    int64_t dataSet = addressToCacheSetData(address);
    int has_free = m_data_set_vacancy[dataSet];
    if (has_free >= num_seg_per_data) {
        DPRINTF(RubyCacheBDIXOR, 
            "   address %#x data array has enough (%d>=%d) space in set %d.=>can coallocate\n",
            address,has_free,num_seg_per_data,dataSet);
        return true;
    }
    DPRINTF(RubyCacheBDIXOR, "   no more space in data array in set %d.=>cannot coallocate\n",dataSet);
    return false;
}

void
CacheMemoryBDIXOR::addPendingEviction(Addr initiate, Addr toEvict)
{
    auto it = m_pendingEvictionMap.find(initiate);
    if (it == m_pendingEvictionMap.end()) {
        DPRINTF(RubyCacheBDIXOR, "adding a new vec to m_pendingEvictionMap[%llx]=%llx\n",initiate,toEvict);
        m_pendingEvictionMap[initiate] = std::vector<Addr> {toEvict};
    }
    else {
        DPRINTF(RubyCacheBDIXOR, "appending to vec in m_pendingEvictionMap[%llx]=%llx\n",initiate,toEvict);
        m_pendingEvictionMap[initiate].push_back(toEvict);
    }
}
Addr
CacheMemoryBDIXOR::getPendingEviction(Addr initiate) const
{
    auto it = m_pendingEvictionMap.find(initiate);
    if (it != m_pendingEvictionMap.end()) {
        return it->second.front();
    }
    panic("no matched initiate address");
}
bool
CacheMemoryBDIXOR::noPendingEviction(Addr initiate) const
{
    auto it = m_pendingEvictionMap.find(initiate);
    if (it != m_pendingEvictionMap.end()) {
        return false;
    }
    else {
        return true;
    }
}
void
CacheMemoryBDIXOR::rmPendingEviction(Addr toEvict)
{
    for (auto it = m_pendingEvictionMap.begin(); it != m_pendingEvictionMap.end(); it++) {
        DPRINTF(RubyCacheBDIXOR, "m_pendingEvictionMap[%llx],size=%d\n",it->first,it->second.size());
        assert(!it->second.empty());
        for (auto iter = (it->second).begin(); iter != (it->second).end(); iter++) {
            DPRINTF(RubyCacheBDIXOR, "  %llx\n",*iter);
            if (*iter == toEvict) {
                (it->second).erase(iter);
                break;
            }
        }
        if (it->second.size() == 0) {
            m_pendingEvictionMap.erase(it);
            break;
        }
    }
}

void
CacheMemoryBDIXOR::addBlockedHitBlock(Addr toInv, Addr blockedHit)
{
    auto it = m_blockedHitMap.find(toInv);
    if (it == m_blockedHitMap.end()) {
        DPRINTF(RubyCacheBDIXOR, "adding a new vec to m_blockedHitMap[%llx]=%llx\n",toInv,blockedHit);
        m_blockedHitMap[toInv] = std::vector<Addr> {blockedHit};
    }
    else {
        DPRINTF(RubyCacheBDIXOR, "appending to vec in m_blockedHitMap[%llx]=%llx\n",toInv,blockedHit);
        m_blockedHitMap[toInv].push_back(blockedHit);
    }
}
Addr
CacheMemoryBDIXOR::getBlockedHitAddress(Addr toInv) const
{
    auto it = m_blockedHitMap.find(toInv);
    if (it != m_blockedHitMap.end()) {
        DPRINTF(RubyCacheBDIXOR, "blockedhitaddress=%llx\n",it->second.front());
        return it->second.front();
    }
    panic("no matched toInv address");
}
bool
CacheMemoryBDIXOR::noBlockedHitBlock(Addr toInv) const
{
    auto it = m_blockedHitMap.find(toInv);
    if (it != m_blockedHitMap.end()) {
        return false;
    }
    else {
        return true;
    }
}
void
CacheMemoryBDIXOR::rmBlockedHitBlock(Addr blockedHit)
{
    for (auto it = m_blockedHitMap.begin(); it != m_blockedHitMap.end(); it++) {
        DPRINTF(RubyCacheBDIXOR, "m_blockedHitMap[%llx],size=%d\n",it->first,it->second.size());
        assert(!it->second.empty());
        for (auto iter = (it->second).begin(); iter != (it->second).end(); iter++) {
            DPRINTF(RubyCacheBDIXOR, "  %llx\n",*iter);
            if (*iter == blockedHit) {
                (it->second).erase(iter);
                break;
            }
        }
        if (it->second.size() == 0) {
            m_blockedHitMap.erase(it);
            break;
        }
    }
}


bool
CacheMemoryBDIXOR::includeProactiveEviction() const
{
    return m_includeProactiveEviction;
}

CacheMemoryBDIXOR::FWDTYPE
CacheMemoryBDIXOR::determineForwardingType(Addr address, MachineID requestor)
{
    AbstractCacheEntry* tagEntry = lookup(address);
    assert(tagEntry != nullptr);
    L2Cache_Entry * this_tag_cast = dynamic_cast<L2Cache_Entry *>(tagEntry);
    assert(this_tag_cast != nullptr);
    if (this_tag_cast->getCacheState() == L2Cache_State::L2Cache_State_NP || 
        this_tag_cast->getCacheState() == L2Cache_State::L2Cache_State_IS_existing ||
        this_tag_cast->getCacheState() == L2Cache_State::L2Cache_State_ISS_existing) {
        // DPRINTF(RubyCacheBDIXORFwd,"demand miss\n");
        return MemoryDirectFwd;
    }

    Addr partnerAddr;
    if (hasNextTag(tagEntry)) {
        partnerAddr = getNextTagAddress(address);
    }
    else if (hasPrevTag(tagEntry)) {
        partnerAddr = getPrevTagAddress(address);
    }
    else { assert(false);}

    AbstractCacheEntry* partnerTagEntry = lookup(partnerAddr);
    
    bool isSharer = false;
    int numSharers_pat = -1;
    MachineID owner;
    // bool isOwner = false;
    L2Cache_Entry * partner_tag_cast = dynamic_cast<L2Cache_Entry *>(partnerTagEntry);
    if (partner_tag_cast != nullptr) {
        isSharer = partner_tag_cast->m_Sharers.isElement(requestor);
        numSharers_pat = partner_tag_cast->m_Sharers.count();
        owner = partner_tag_cast->m_Exclusive;
        // isOwner = (owner == requestor);
    }
    else {
        assert(false);
    }

    DPRINTF(RubyCacheBDIXORFwd,"partner(%llx):%s, this(%llx):%s\n", 
        partnerAddr,
        partner_tag_cast->getCacheState(), 
        address,
        this_tag_cast->getCacheState()
    );

    
    if (isSharer == true && partner_tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT &&
        partner_tag_cast->getCacheState() != L2Cache_State::L2Cache_State_MT_MB &&
        partner_tag_cast->getCacheState() != L2Cache_State::L2Cache_State_SS_MB) {
        return SamecoreFwd;
    }
    else {
        // This block should have sharers
        int numSharers_this = this_tag_cast->m_Sharers.count();
        DPRINTF(RubyCacheBDIXORFwd,"crossCoreForwarding, partner#choices=%d, this#choices=%d\n",
            numSharers_pat, numSharers_this
        );
        if (m_includeProactiveEviction == true) {
            assert(numSharers_pat+numSharers_this > 0); // needs to have at least one sharer
        }
        return CrosscoreFwd;
    }

}

bool
CacheMemoryBDIXOR::canDoSameCoreForwarding(Addr address, MachineID requestor)
{
    FWDTYPE type = determineForwardingType(address,requestor);
    return (type == SamecoreFwd);
}
bool
CacheMemoryBDIXOR::noSpecialFwdNeeded(Addr address, MachineID requestor)
{
    FWDTYPE type = determineForwardingType(address,requestor);
    return (type == SamecoreFwd || type == MemoryDirectFwd);
}

void
CacheMemoryBDIXOR::profileCompressedAccess(Addr address, MachineID requestor)
{
    cacheMemoryBDIXORStats.accessToCompressedBlock+=1;

    FWDTYPE type = determineForwardingType(address,requestor);
    
    if (type == MemoryDirectFwd) {
        // DPRINTF(RubyCacheBDIXORFwd,"demand miss\n");
        cacheMemoryBDIXORStats.directForwarding+=1;
        return;
    }
    else if (type == SamecoreFwd) {
        DPRINTF(RubyCacheBDIXORFwd,"sameCoreForwarding\n");
        cacheMemoryBDIXORStats.sameCoreForwarding+=1;
    }
    else if (type == CrosscoreFwd) {
        DPRINTF(RubyCacheBDIXORFwd,"crossCoreForwarding\n");
        cacheMemoryBDIXORStats.crossCoreForwarding+=1;
    }
    else {
        assert(false);
    }
}
void
CacheMemoryBDIXOR::profileUncompressedAccess()
{
    cacheMemoryBDIXORStats.accessToUncompressedBlock+=1;
}
void
CacheMemoryBDIXOR::profileFillNonXOR()
{
    cacheMemoryBDIXORStats.fillNonXOR+=1;
}
void
CacheMemoryBDIXOR::profileFillNonXOR_noGoodCandidate()
{
    cacheMemoryBDIXORStats.fillNonXOR_noGoodCandidate+=1;
}
void
CacheMemoryBDIXOR::profileFillNonXOR_noSingular()
{
    cacheMemoryBDIXORStats.fillNonXOR_noSingular+=1;
}

void
CacheMemoryBDIXOR::profileFillXOR()
{
    cacheMemoryBDIXORStats.fillXOR+=1;
}

void
CacheMemoryBDIXOR::profileXORDecompReason_notRecoverable_putx()
{
    cacheMemoryBDIXORStats.XORDecompReason_notRecoverable+=1;
    cacheMemoryBDIXORStats.XORDecompReason_notRecoverable_putx+=1;
}
void
CacheMemoryBDIXOR::profileXORDecompReason_notRecoverable_get()
{
    cacheMemoryBDIXORStats.XORDecompReason_notRecoverable+=1;
    cacheMemoryBDIXORStats.XORDecompReason_notRecoverable_get+=1;
}
void
CacheMemoryBDIXOR::profileXORDecompReason_noSharer()
{
    cacheMemoryBDIXORStats.XORDecompReason_noSharer+=1;
}
void
CacheMemoryBDIXOR::profileXORDecompReason_tM()
{
    cacheMemoryBDIXORStats.XORDecompReason_tM+=1;
}
void
CacheMemoryBDIXOR::profileXORDecompReason_tag()
{
    cacheMemoryBDIXORStats.XORDecompReason_tag+=1;
}
void
CacheMemoryBDIXOR::profileXORDecompReason_data()
{
    cacheMemoryBDIXORStats.XORDecompReason_data+=1;
}


CacheMemoryBDIXOR::
CacheMemoryBDIXORStats::CacheMemoryBDIXORStats(statistics::Group *parent)
    : statistics::Group(parent),
      ADD_STAT(numReplXOR, "Number of replacment due to xor compression"),
      ADD_STAT(XORChoice_sameCore, "Number of XOR chosen with same core"),
      ADD_STAT(XORChoice_pureRandom, "Number of XOR chosen purely randomly"),
      ADD_STAT(numXOR, "Number of XOR actually done"),
      ADD_STAT(accessToCompressedBlock, "Number of access to compressed blk"),
      ADD_STAT(accessToUncompressedBlock, "Number of access to uncompressed blk"),
      ADD_STAT(sameCoreForwarding, "Number of same core forwarding"),
      ADD_STAT(crossCoreForwarding, "Number of same core forwarding"),
      ADD_STAT(directForwarding, "Number of direct forwarding from L2 to L1"),
      ADD_STAT(patnerHasNoSharer, "Number of times when access a block, its partner does not have any sharer"),
      ADD_STAT(partnerSharerCt, "Histogram of partner's sharer ct when access a block"),
      ADD_STAT(xorChoiceCt, "Histogram of xor choice ct when filling in a blk"),
      ADD_STAT(xorChoiceCt_sameCore, "Histogram of xor choice ct when filling in a blk, if same core xor is achievable"),
      ADD_STAT(fillNonXOR, "number of fill that is not xor"),
      ADD_STAT(fillNonXOR_noGoodCandidate, "number of fill that is not xor just because no good candidate"),
      ADD_STAT(fillNonXOR_noSingular, "number of fill that is not xor just because no singular block"),
      ADD_STAT(fillXOR, "number of fill that is xor"),
      ADD_STAT(XORDecompReason_notRecoverable, "XOR decompress reason is data not recoverable"),
      ADD_STAT(XORDecompReason_notRecoverable_putx, "XOR decompress reason is data not recoverable, putx incured"),
      ADD_STAT(XORDecompReason_notRecoverable_get, "XOR decompress reason is data not recoverable, gets/instr incured"),
      ADD_STAT(XORDecompReason_tM, "XOR decompress reason is transitiioning to M"),
      ADD_STAT(XORDecompReason_tag, "XOR decompress reason is partner tag replacing"),
      ADD_STAT(XORDecompReason_data, "XOR decompress reason is partner data replacing"),
      ADD_STAT(XORDecompReason_noSharer, "XOR decompress reason is data not enough sharers"),
      ADD_STAT(numTagLocked, statistics::units::Rate<
                statistics::units::Count, statistics::units::Tick>::get(),
                "Number of tags xor locked (average)")

{
    numReplXOR
        .flags(statistics::nonan);
    XORChoice_sameCore
        .flags(statistics::nonan);
    XORChoice_pureRandom
        .flags(statistics::nonan);
    numXOR
        .flags(statistics::nonan);
    accessToCompressedBlock
        .flags(statistics::nonan);
    accessToUncompressedBlock
        .flags(statistics::nonan);
    sameCoreForwarding
        .flags(statistics::nonan);
    crossCoreForwarding
        .flags(statistics::nonan);
    directForwarding
        .flags(statistics::nonan);
    patnerHasNoSharer
        .flags(statistics::nonan);
    partnerSharerCt
        .init(0,64,1)
        .flags(statistics::pdf);
    xorChoiceCt
        .init(0,64,1)
        .flags(statistics::pdf);
    xorChoiceCt_sameCore
        .init(0,64,1)
        .flags(statistics::pdf);
    fillNonXOR
        .flags(statistics::nonan);
    fillXOR
        .flags(statistics::nonan);
    XORDecompReason_notRecoverable
        .flags(statistics::nonan);
    XORDecompReason_notRecoverable_putx
        .flags(statistics::nonan);
    XORDecompReason_notRecoverable_get
        .flags(statistics::nonan);
    XORDecompReason_tM
        .flags(statistics::nonan);
    XORDecompReason_tag
        .flags(statistics::nonan);
    XORDecompReason_data
        .flags(statistics::nonan);
    numTagLocked
        .flags(statistics::nonan);
}



}
}