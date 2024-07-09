#include "debug/RubyCacheXOR.hh"
#include "debug/RubyCacheUtil.hh"
#include "mem/ruby/structures/mystructures/msi/CacheMemoryXOR.hh"
#include "mem/ruby/system/RubySystem.hh"
#include "mem/ruby/protocol/L2Cache_Entry.hh"

#include <iostream>

namespace gem5
{

namespace ruby
{

CacheMemoryXOR::CacheMemoryXOR(const Params &p)
    : CacheMemoryDecoupledTagData(p),
    m_search_scope(p.search_scope),
    m_enforce(p.enforce),
    m_rank_criteria(p.rank_criteria),
    cacheMemoryXORStats(this)
{
    std::cout << "Hello World xor! From a CacheMemoryXOR! "<<std::endl;
    m_valid_candidate_ct_threshold = p.valid_candidate_ct_threshold;
}

void
CacheMemoryXOR::init()
{
    CacheMemoryDecoupledTagData::init();
    // === ALLOCATE ===
    // 2d
    m_xored.resize(m_cache_num_sets,
                    std::vector<bool>(m_cache_assoc, false));
}

CacheMemoryXOR::~CacheMemoryXOR()
{
    m_xored.clear();
}

bool
CacheMemoryXOR::shouldDoXOR(Addr address, MachineID requestingCore)
{
    AbstractCacheEntry* tagEntry = lookup(address);
    if (tagEntry != nullptr) {
        bool should_this_block_xor = shouldThisBlockDoXOR(tagEntry);
        if (!should_this_block_xor) return false;
    }


    std::vector<AbstractCacheEntry*> candidates;
    getFinalCandidates(candidates, address, requestingCore);
    if (candidates.size() == 0) {
        return false;
    } else {
        candidates.clear();
        return true;
    }
}

bool
CacheMemoryXOR::shouldThisBlockDoXOR(AbstractCacheEntry* thisTag)
{
    // if already xored, cannot xor again
    if (m_xored[thisTag->getSet()][thisTag->getWay()] == true) {
        return false;
    }
    // if enforce clean, this block needs to be clean
    if (m_enforce == enums::clean) {
        L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(thisTag);
        if (tag_cast != nullptr) {
            if (tag_cast->m_Dirty) return false;
        } else assert(false);
    }
    return true;
}

Addr
CacheMemoryXOR::probeXORPartner(Addr address, MachineID requestingCore)
{
    std::vector<AbstractCacheEntry*> candidates;
    getFinalCandidates(candidates, address, requestingCore);
    AbstractCacheEntry* partner = rankFinalCandidates(candidates);
    Addr retAddr = partner->m_Address;
    candidates.clear();
    map_partner_address[address] = retAddr;
    map_partner_address[retAddr] = address;
    return retAddr;
}

AbstractCacheEntry*
CacheMemoryXOR::rankFinalCandidates(std::vector<AbstractCacheEntry*> candidates)
{
    cacheMemoryXORStats.xor_candidate_ct.sample(candidates.size());

    if (candidates.size() == 1) {
        return candidates[0];
    } else if (candidates.size() == 0) {
        panic("No candidates to rank");
    } else {
        if (m_rank_criteria == enums::random) {
            int candidate_ind = rand() % candidates.size();
            return candidates[candidate_ind];
        }
        else if (m_rank_criteria == enums::lru) {
            panic("lru not implemented yet");
        }
        else if (m_rank_criteria == enums::mru) {
            panic("mru not implemented yet");
        }
        else if (m_rank_criteria == enums::similarity) {
            panic("Similarity not implemented yet");
        } else {
            panic("Invalid rank criteria");
        }
    }
}

void
CacheMemoryXOR::getFinalCandidates(std::vector<AbstractCacheEntry*> &candidates, Addr address, MachineID requestingCore)
{
    assert(address == makeLineAddress(address));

    // put all unxored blocks in the scope of consideration into the vector
    populateAllCandidates(candidates, address);
    if (candidates.size() == 0) {
        return;
    }
    DPRINTF(RubyCacheXOR, "all cand: %d\n", candidates.size());
    

    // if candidates present, do the second pass filtering
    filterCandidates(candidates, address, requestingCore);
    DPRINTF(RubyCacheXOR, "filtered cand: %d\n", candidates.size());
    return;
}

void
CacheMemoryXOR::populateAllCandidates(std::vector<AbstractCacheEntry*> &candidates, Addr address)
{

    // ======= - SCOPE=SET - =======
    if (m_search_scope == enums::set) {
        int64_t cacheSet = addressToCacheSet(address);
        for (int i = 0; i < m_cache_assoc; i++) {
            if (m_xored[cacheSet][i] == false && m_cache[cacheSet][i] != nullptr) {
                candidates.push_back(m_cache[cacheSet][i]);
            }
        }
        return;
    } 
    // ======= - SCOPE=BANK - =======
    else if (m_search_scope == enums::bank) {
        for (int i = 0; i < m_cache_num_sets; i++) {
            for (int j = 0; j < m_cache_assoc; j++) {
                if (m_xored[i][j] == false && m_cache[i][j] != nullptr) {
                    candidates.push_back(m_cache[i][j]);
                }
            }
        }
        return;
    }
    panic("Invalid search scope");
}

void
CacheMemoryXOR::filterCandidates(std::vector<AbstractCacheEntry*> &candidates, Addr address, MachineID requestingCore)
{
    if (m_enforce == enums::null) {
        return;
    } 
    // ======= - force same core - =======
    else if (m_enforce == enums::same_core) {
        auto it = candidates.begin();
        while(it != candidates.end()) {
            L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(*it);
            if (tag_cast != nullptr) {
                if (tag_cast->m_Sharers.count() > 0) {
                    if (!tag_cast->m_Sharers.isElement(requestingCore)) {
                        it = candidates.erase(it);
                    } else {
                        it++;
                    }
                } else {
                    it++;
                }
            } else assert(false);
        }
    }
    // ======= - force no sharer block - =======
    else if (m_enforce == enums::no_sharer) {
        auto it = candidates.begin();
        while(it != candidates.end()) {
            L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(*it);
            if (tag_cast != nullptr) {
                if (tag_cast->m_Sharers.count() > 0) {
                    it = candidates.erase(it);
                } else {
                    it++;
                }
            } else assert(false);
        }
    }
    // ======= - force many valid candidates - =======
    else if (m_enforce == enums::many_valid_candidates) {
        if (candidates.size() < m_valid_candidate_ct_threshold) {
            candidates.clear();
        }
    }
    // ======= - force clean - =======
    else if (m_enforce == enums::clean) {
        DPRINTF(RubyCacheXOR, "filterCandidates(clean)\n");
        auto it = candidates.begin();
        while(it != candidates.end()) {
            L2Cache_Entry * tag_cast = dynamic_cast<L2Cache_Entry *>(*it);
            if (tag_cast != nullptr) {
                if (tag_cast->m_Dirty == true) {
                    DPRINTF(RubyCacheXOR, " filtered out dirty candidates 0x%llx\n", tag_cast->m_Address);
                    it = candidates.erase(it);
                } else {
                    it++;
                }
            } else assert(false);
        }
    } else {
        panic("Invalid enforce");
    }
}

bool
CacheMemoryXOR::hasPartnerFromMap(Addr address) const
{
    auto it = map_partner_address.find(address);
    if (it != map_partner_address.end()) {
            return true;
    }
    return false;
}

// bool
// CacheMemoryXOR::hasPartner(Addr address) const
// {
// }

Addr
CacheMemoryXOR::getPartnerTagAddressFromMap(Addr address) const
{
    auto it = map_partner_address.find(address);
    assert(it != map_partner_address.end()); 
    return it->second;
}
// Addr
// CacheMemoryXOR::getPartnerTagAddress(Addr address) const
// {
// }

void
CacheMemoryXOR::removePartnerFromMap(Addr address)
{   
    auto it1 = map_partner_address.find(address);
    assert(it1 != map_partner_address.end()); 
    Addr paddress = it1->second;
    map_partner_address.erase(it1->first);
    auto it2 = map_partner_address.find(paddress);
    assert(it2 != map_partner_address.end()); 
    map_partner_address.erase(paddress);
}

void
CacheMemoryXOR::setXORed(Addr address) 
{
    AbstractCacheEntry* entry = lookup(address);
    assert (entry != nullptr);
    m_xored[entry->getSet()][entry->getWay()] = true;
}

void
CacheMemoryXOR::clearXORed(Addr address) 
{
    AbstractCacheEntry* entry = lookup(address);
    assert (entry != nullptr);
    m_xored[entry->getSet()][entry->getWay()] = false;
}

void
CacheMemoryXOR::linkToPartner(Addr address, Addr partnerAddr) {
    linkToPartner(address, partnerAddr, m_block_size);
}
void
CacheMemoryXOR::linkToPartner(Addr address, Addr partnerAddr, int data_size) {
    DPRINTF(RubyCacheXOR, "=====linkToPartner(this:%llx, p:%llx) in CacheMemoryXOR=====\n", address, partnerAddr);
    int num_seg_per_data = divCeil(data_size,m_segment_size);
    DPRINTF(RubyCacheXOR, "0.linkToPartner:data_size=%dB, equivalent to %d segment\n", data_size, num_seg_per_data);

    assert(address == makeLineAddress(address));
    assert(CacheMemory::isTagPresent(address));

    assert(partnerAddr == makeLineAddress(partnerAddr));
    assert(CacheMemory::isTagPresent(partnerAddr));
    assert(cacheAvailData(partnerAddr, data_size)); // make sure partner has enough space

    //lookup tag
    AbstractCacheEntry* tagEntry = lookup(address);
    assert(tagEntry != nullptr);
    uint32_t tagSet = tagEntry->getSet();
    uint32_t tagWay = tagEntry->getWay();
    assert(m_cache[tagSet][tagWay]->m_Address == address);

    //lookup partner tag
    AbstractCacheEntry* ptagEntry = lookup(partnerAddr);
    assert(ptagEntry != nullptr);
    uint32_t ptagSet = ptagEntry->getSet();
    uint32_t ptagWay = ptagEntry->getWay();
    assert(m_cache[ptagSet][ptagWay]->m_Address == partnerAddr);
    
    AbstractCacheEntry* existing_dataEntry = m_tag_data_ptr[ptagEntry->getSet()][ptagEntry->getWay()];
    assert(existing_dataEntry != nullptr);

    existing_dataEntry->setLastAccess(curTick());
    m_replacementPolicy_ptr_data->touch(existing_dataEntry->replacementData);
    DPRINTF(RubyCacheXOR, "   1.touched existing data block's repl\n");
    m_tag_data_ptr[tagSet][tagWay] = existing_dataEntry; //tag to data
    DPRINTF(RubyCacheXOR, "   2.set tag to data pointer: tag[%d,%d]->data[%d,%d]\n", 
        tagSet,tagWay, existing_dataEntry->getSet(), existing_dataEntry->getWay());

    addToTail(ptagEntry, tagEntry);
    DPRINTF(RubyCacheXOR, "   3.added tag to tag list\n");
    m_data_index[address] = existing_dataEntry->getWay();
    DPRINTF(RubyCacheXOR, "   4.updated data_index\n");
    m_data_cntr[existing_dataEntry->getSet()][existing_dataEntry->getWay()] += 1;
    assert(m_data_cntr[existing_dataEntry->getSet()][existing_dataEntry->getWay()] == 2);
    
    DPRINTF(RubyCacheXOR, "   5.set tag->seg cntr\n");
    m_tag_seg_cntr[tagSet][tagWay] = m_tag_seg_cntr[ptagEntry->getSet()][ptagEntry->getWay()];
}

void
CacheMemoryXOR::unlinkDataToTag(Addr address) {
    DPRINTF(RubyCacheXOR, "=====unlinkDataToTag() in CacheMemoryXOR: %#x=====\n", address);
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

    DPRINTF(RubyCacheXOR, "  0.data is at [%d,%d]\n", dataSet, dataSeg);

    if (m_data_cntr[dataSet][dataSeg] == 1) {
        DPRINTF(RubyCacheXOR, "  1.no tag points to this data, deallocating...\n");
        //reset data's replacement data
        m_replacementPolicy_ptr_data->invalidate(dataEntry->replacementData);
        //delete data entry
        delete dataEntry;
        m_data_index.erase(address);
        
        //reset ptrs
        DPRINTF(RubyCacheXOR, "  1a.freeing up %d segs in data[%d]\n", 
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
        DPRINTF(RubyCacheXOR, "  1.other tag still points to this data,address=%llx\n", m_data_head_tag_ptr[dataSet][dataSeg]->m_Address);
        m_data_index.erase(address);
        m_tag_seg_cntr[tagSet][tagWay] = 0; 
    }
    //decrement data cntr
    m_data_cntr[dataSet][dataSeg] -= 1;
}

// Note: this function is exactly the same as the one in CacheMemoryDecoupledTagData
void
CacheMemoryXOR::deallocateTagData(Addr address)
{
    DPRINTF(RubyCacheXOR, "deallocateTagData(%#x) in CacheMemoryXOR\n", address);
    unlinkDataToTag(address);
    CacheMemory::deallocate(address);
    cacheMemoryDecoupledStats.numTagInUse_dc--;
    if (cacheMemoryDecoupledStats.numTagInUse_dc.value() > cacheMemoryDecoupledStats.numTagInUse_dc_max.value()) {
        cacheMemoryDecoupledStats.numTagInUse_dc_max = cacheMemoryDecoupledStats.numTagInUse_dc.value();
    }
}

CacheMemoryXOR::
CacheMemoryXORStats::CacheMemoryXORStats(statistics::Group *parent)
    : statistics::Group(parent),
      ADD_STAT(xor_candidate_ct, "Distribution of xor candidate ct")
{
    xor_candidate_ct
        .init(0,128,1)
        .flags(statistics::pdf);
    
}

}
}