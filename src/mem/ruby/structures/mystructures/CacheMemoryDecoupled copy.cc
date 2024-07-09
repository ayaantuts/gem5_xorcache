#include "debug/RubyCacheDecoupled.hh"
#include "mem/ruby/structures/mystructures/CacheMemoryDecoupled.hh"
#include "mem/ruby/system/RubySystem.hh"

#include <iostream>

namespace gem5
{

namespace ruby
{

CacheMemoryDecoupled::CacheMemoryDecoupled(const Params &p)
    : CacheMemory(p),
    cacheMemoryDecoupledStats(this)
{
    std::cout << "Hello World! From a CacheMemoryDecoupled!" << std::endl;
    m_data_array_assoc = p.dataArrayAssoc;
    m_data_array_set = p.dataArraySet;
    m_num_seg_per_blk = p.numSegPerBlk;
    m_replacementPolicy_ptr_data = p.replacement_policy_data;
}

void
CacheMemoryDecoupled::init()
{
    CacheMemory::init();
    if (m_data_array_set == 0) {
        m_data_array_set = m_cache_num_sets;
    }
    m_data_num_set_bits = floorLog2(m_data_array_set);
    assert(m_data_num_set_bits > 0);

    m_segment_size = m_block_size / m_num_seg_per_blk;

    cacheMemoryDecoupledStats.block_size = m_block_size;
    cacheMemoryDecoupledStats.segment_size = m_segment_size;

    // === ALLOCATE DATA ARR ===
    // 3d
    // allocate max amount of space for logical data -> 1 segment per logical data
    m_cache_data.resize(m_data_array_set,std::vector<std::vector<AbstractCacheEntry*> >(
        m_data_array_assoc,std::vector<AbstractCacheEntry*>(m_num_seg_per_blk, nullptr)));
    // 3d
    replacement_data_for_data.resize(m_data_array_set,std::vector<std::vector<ReplData> >(
        m_data_array_assoc,std::vector<ReplData>(m_num_seg_per_blk, nullptr)));

    // instantiate all data replacement_data here
    // 3d
    for (int i = 0; i < m_data_array_set; i++) {
        for ( int j = 0; j < m_data_array_assoc; j++) {
            for ( int k = 0; k < m_num_seg_per_blk; k++) {
                replacement_data_for_data[i][j][k] =
                                    m_replacementPolicy_ptr_data->instantiateEntry();
            }
        }
    }

    // === allocate all connection management ptrs ===
    m_data_head_tag_ptr.resize(m_data_array_set,std::vector<std::vector<AbstractCacheEntry*> >(
        m_data_array_assoc,std::vector<AbstractCacheEntry*>(m_num_seg_per_blk, nullptr)));
    m_data_cntr.resize(m_data_array_set,std::vector<std::vector<int> >(
        m_data_array_assoc,std::vector<int>(m_num_seg_per_blk, 0)));
    m_data_blk_vacancy.resize(m_data_array_set,
                    std::vector<int>(m_data_array_assoc, m_num_seg_per_blk));

    m_tag_next_tag_ptr.resize(m_cache_num_sets,
                    std::vector<AbstractCacheEntry*>(m_cache_assoc, nullptr));
    m_tag_prev_tag_ptr.resize(m_cache_num_sets,
                    std::vector<AbstractCacheEntry*>(m_cache_assoc, nullptr));
    m_tag_data_ptr.resize(m_cache_num_sets,
                    std::vector<AbstractCacheEntry*>(m_cache_assoc, nullptr));
    m_tag_seg_cntr.resize(m_cache_num_sets,
                    std::vector<int>(m_cache_assoc, 0));

}

CacheMemoryDecoupled::~CacheMemoryDecoupled()
{
    // CacheMemory::~CacheMemory();
    if (m_replacementPolicy_ptr_data)
        delete m_replacementPolicy_ptr_data;
    // DELETE DATA ARR
    for (int i = 0; i < m_data_array_set; i++) {
        for (int j = 0; j < m_data_array_assoc; j++) {
            for (int k = 0; k < m_num_seg_per_blk; j++) {
                delete m_cache_data[i][j][k];
                delete m_data_head_tag_ptr[i][j][k];
            }
        }
    }
    for (int i = 0; i < m_cache_num_sets; i++) {
        for (int j = 0; j < m_cache_assoc; j++) {
            delete m_tag_next_tag_ptr[i][j];
            delete m_tag_prev_tag_ptr[i][j];
            delete m_tag_data_ptr[i][j];
        }
    }
}

// convert a Address to its location in the cache
int64_t
CacheMemoryDecoupled::addressToCacheSetData(Addr address) const
{
    assert(address == makeLineAddress(address));
    return bitSelect(address, m_start_index_bit,
                     m_start_index_bit + m_data_num_set_bits - 1);
}

int
CacheMemoryDecoupled::findDataSegIdx(Addr address) const {
    int seg = -1;
    auto it = m_data_index.find(address);
    if (it != m_data_index.end()) {
            seg = it->second;
    }
    assert(seg>=0);
    return seg;
}

int
CacheMemoryDecoupled::findEmptyDataSegIdx(int dataSet, int dataWay) const {
    int seg_empty = -1;
    for (int i = 0; i < m_num_seg_per_blk; i++) {
        if (!m_cache_data[dataSet][dataWay][i]) {
            seg_empty = i;
            break;
        }
    }
    assert(seg_empty >= 0);
    return seg_empty;
}

void
CacheMemoryDecoupled::profileReplacmentDataArray() {
    cacheMemoryDecoupledStats.numReplDataArr++;
}

// tests to see if an address is present in the cache data array
bool
CacheMemoryDecoupled::isDataPresent(Addr address) const
{
    const AbstractCacheEntry* const tagEntry = CacheMemory::lookup(address);
    if (tagEntry == nullptr) {
        // We didn't find the tag, therefore no data as well
        DPRINTF(RubyCacheDecoupled, "   No tag (nor data) match for address: %#x\n", address);
        return false;
    }
    uint32_t set = tagEntry->getSet();
    uint32_t way = tagEntry->getWay();

    if (m_tag_data_ptr[set][way] == nullptr) {
        // There is tag but no data
        DPRINTF(RubyCacheDecoupled, "   tag match for address: %#x, but no data\n", address);
        return false;
    }
    DPRINTF(RubyCacheDecoupled, "   address: %#x with data found\n", address);
    return true;
}

// Returns true if there is:
//   a) a tag match on this address with allocated data entry or there is
//   b) an unused space in the same cache set for data array
bool
CacheMemoryDecoupled::cacheAvailData(Addr address, int data_size) const
{
    DPRINTF(RubyCacheDecoupled, "cacheAvailData() in CacheMemoryDecoupled: %#x\n",address);
    int num_seg_per_data = divCeil(data_size,m_segment_size);
    DPRINTF(RubyCacheDecoupled, "cacheAvailData:data_size=%dB, equivalent to %d segment\n", data_size, num_seg_per_data);
    // std::cout << "cacheAvailData:data size=" << data_size << ", equivalent to " << num_seg_per_data << " segs." <<std::endl;
    assert(address == makeLineAddress(address));

    int64_t cacheSet = CacheMemory::addressToCacheSet(address);

    for (int i = 0; i < m_cache_assoc; i++) {
        AbstractCacheEntry* entry = m_cache[cacheSet][i];
        if (entry != NULL) {
            if (entry->m_Address == address) {
                uint32_t set = entry->getSet();
                uint32_t way = entry->getWay();
                int has = m_tag_seg_cntr[set][way];
                if (has >= num_seg_per_data) {
                    // Already in the cache and there is data
                    DPRINTF(RubyCacheDecoupled, "   address %#x already exists and has %d data segment(s)\n",address, has);
                    return true;
                }
            }
        }
    }
    int64_t dataSet = addressToCacheSetData(address);
    for (int i = 0; i < m_data_array_assoc; i++) {
        int has_free = m_data_blk_vacancy[dataSet][i];
        if (has_free >= num_seg_per_data) {
            DPRINTF(RubyCacheDecoupled, 
                "   address %#x data array has enough (%d>=%d) space in set %d way %d\n",
                address,has_free,num_seg_per_data,dataSet,i);
            return true;
        }
    }
    DPRINTF(RubyCacheDecoupled, "   no more space in data array in set %d\n",dataSet);
    return false;
}

// Returns true if there is enough space to coallocate, i.e., no need to replace!
bool
CacheMemoryDecoupled::cacheCanCoallocate(Addr address, int data_size) const
{
    DPRINTF(RubyCacheDecoupled, "cacheCanCoallocate() in CacheMemoryDecoupled: %#x\n",address);
    int num_seg_per_data = divCeil(data_size,m_segment_size);
    DPRINTF(RubyCacheDecoupled, "cacheCanCoallocate:data_size=%dB, equivalent to %d segment\n", data_size, num_seg_per_data);
    // std::cout << "cacheAvailData:data size=" << data_size << ", equivalent to " << num_seg_per_data << " segs." <<std::endl;
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
                    DPRINTF(RubyCacheDecoupled, 
                        "   address %#x already exists and already has enough %d data segment(s)=>can coallocate\n",
                        address, already_has);
                    return true;
                }
                else {
                    // already incache but need to allocate more data
                    
                    AbstractCacheEntry* dataEntry = m_tag_data_ptr[set][way];
                    uint32_t dataset = dataEntry->getSet();
                    uint32_t dataway = dataEntry->getWay();
                    int has_free = m_data_blk_vacancy[dataset][dataway];
                    if ((already_has + has_free) >= num_seg_per_data) {
                        DPRINTF(RubyCacheDecoupled, 
                        "   address %#x already exists, has %d data segment(s), also %d free.=>can coallocate\n",
                        address, already_has, has_free);
                        return true;
                    }
                    else {
                        DPRINTF(RubyCacheDecoupled, 
                        "   address %#x already exists but only has %d data segment(s) now and %d free.\n",
                        address, already_has, has_free);
                    }
                }
            }
        }
    }
    assert(found_address_match);

    int64_t dataSet = addressToCacheSetData(address);
    for (int i = 0; i < m_data_array_assoc; i++) {
        int has_free = m_data_blk_vacancy[dataSet][i];
        if (has_free >= num_seg_per_data) {
            DPRINTF(RubyCacheDecoupled, 
                "   address %#x data array has enough (%d>=%d) space in set %d way %d.=>can coallocate\n",
                address,has_free,num_seg_per_data,dataSet,i);
            return true;
        }
    }
    DPRINTF(RubyCacheDecoupled, "   no more space in data array in set %d.=>cannot coallocate\n",dataSet);
    return false;
}

void
CacheMemoryDecoupled::cacheAvailData_set_way(Addr address, int data_size, int* ret_dataset, int* ret_dataway) const
{
    DPRINTF(RubyCacheDecoupled, "cacheAvailData_set_way() in CacheMemoryDecoupled: %#x\n",address);
    int num_seg_per_data = divCeil(data_size,m_segment_size);
    // DPRINTF(RubyCacheDecoupled, "cacheAvailData_set_way:data_size=%dB, equivalent to %d segment\n", data_size, num_seg_per_data);
    // std::cout << "cacheAvailData:data size=" << data_size << ", equivalent to " << num_seg_per_data << " segs." <<std::endl;
    assert(address == makeLineAddress(address));

    int64_t cacheSet = CacheMemory::addressToCacheSet(address);

    for (int i = 0; i < m_cache_assoc; i++) {
        AbstractCacheEntry* entry = m_cache[cacheSet][i];
        AbstractCacheEntry* dataEntry = m_tag_data_ptr[cacheSet][i];
        if (entry != NULL) {
            if (entry->m_Address == address) {
                uint32_t set = entry->getSet();
                uint32_t way = entry->getWay();
                int has = m_tag_seg_cntr[set][way];
                if (has >= num_seg_per_data) {
                    // Already in the cache and there is data
                    uint32_t s = dataEntry->getSet();
                    uint32_t w = dataEntry->getWay();
                    DPRINTF(RubyCacheDecoupled, 
                        "   address %#x data array already has %d data segment(s) in set %d way %d\n",
                        address, has, s, w);
                    *ret_dataset = s;
                    *ret_dataset = w;
                    return;
                }
            }
        }
    }
    int64_t dataSet = addressToCacheSetData(address);
    for (int i = 0; i < m_data_array_assoc; i++) {
        int has_free = m_data_blk_vacancy[dataSet][i];
        if (has_free >= num_seg_per_data) {
            DPRINTF(RubyCacheDecoupled, 
                "   address %#x data array has enough (%d>=%d) space in set %d way %d\n",
                address,has_free,num_seg_per_data,dataSet,i);
            *ret_dataset = dataSet;
            *ret_dataway = i;
            return;
        }
    }
    panic("no more space in data array in set %d\n",dataSet);
    return;
}

AbstractCacheEntry*
CacheMemoryDecoupled::allocate(Addr address, AbstractCacheEntry *entry)
{
    DPRINTF(RubyCacheDecoupled, "allocate() in CacheMemoryDecoupled\n");
    AbstractCacheEntry *retEntry = CacheMemory::allocate(address, entry);
    cacheMemoryDecoupledStats.numTagInUse++;
    return retEntry;
}

void
CacheMemoryDecoupled::deallocate(Addr address)
{
    DPRINTF(RubyCacheDecoupled, "deallocate() in CacheMemoryDecoupled\n");
    CacheMemory::deallocate(address);
    cacheMemoryDecoupledStats.numTagInUse--;
}

// Returns with the physical address of the conflicting cache line for data array
Addr
CacheMemoryDecoupled::cacheProbeData(Addr address) const
{
    DPRINTF(RubyCacheDecoupled, "cacheProbeData() in CacheMemoryDecoupled\n");
    assert(address == makeLineAddress(address));
    assert(cacheAvail(address));

    int64_t dataSet = addressToCacheSetData(address);
    DPRINTF(RubyCacheDecoupled, "  set in data: %d\n", dataSet);

    // collect replacement candidates
    std::vector<ReplaceableEntry*> candidates;
    for (int i = 0; i < m_data_array_assoc; i++) {
        for (int j = 0; j < m_num_seg_per_blk; j++) {
            if (m_cache_data[dataSet][i][j] != NULL && 
            m_data_head_tag_ptr[dataSet][i][j]->m_Address != address) {
                // if this entry is not null and not my own data, then consider as candidate
                candidates.push_back(static_cast<ReplaceableEntry*>(
                                                            m_cache_data[dataSet][i][j]));
            }
        }
    }
    DPRINTF(RubyCacheDecoupled, "    arbitrating among %d candidates\n", candidates.size());

    ReplaceableEntry* victim = m_replacementPolicy_ptr_data->getVictim(candidates);
    assert(victim != NULL);
    uint32_t vWay = victim->getWay();
    uint32_t vSeg = m_num_seg_per_blk;
    for (int j = 0; j < m_num_seg_per_blk; j++) {
        if (m_cache_data[dataSet][vWay][j] != NULL && 
            victim == m_cache_data[dataSet][vWay][j]) {
            vSeg = j;
        }
    }
    assert(vSeg < m_num_seg_per_blk);
    DPRINTF(RubyCacheDecoupled, "  identified conflicting data[%d,%d,%d]\n", 
    dataSet, vWay, vSeg);

    assert(m_data_head_tag_ptr[dataSet][vWay][vSeg] != NULL);
    DPRINTF(RubyCacheDecoupled, "  identified its associated tag[%d,%d]\n", 
    m_data_head_tag_ptr[dataSet][vWay][vSeg]->getSet(),
    m_data_head_tag_ptr[dataSet][vWay][vSeg]->getWay());

    // I can not decide that i need to evict my own tag to make space for myself
    assert(m_data_head_tag_ptr[dataSet][vWay][vSeg]->m_Address != address);

    return m_data_head_tag_ptr[dataSet][vWay][vSeg]->m_Address;
}

void
CacheMemoryDecoupled::linkDataToTag(Addr address, AbstractCacheEntry* new_dataEntry, int data_size) {
    DPRINTF(RubyCacheDecoupled, "linkDataToTag() in CacheMemoryDecoupled\n");
    int num_seg_per_data = divCeil(data_size,m_segment_size);
    DPRINTF(RubyCacheDecoupled, "linkDataToTag:data_size=%dB, equivalent to %d segment\n", data_size, num_seg_per_data);
    // std::cout << "linkDataToTag:data size=" << data_size << ", equivalent to " << num_seg_per_data << " segs." <<std::endl;

    assert(address == makeLineAddress(address));
    assert(CacheMemory::isTagPresent(address));
    assert(cacheAvailData(address, data_size));
    DPRINTF(RubyCacheDecoupled, "   address: %#x data filing...\n", address);
    // Find the first open slot in data array
    int64_t dataSet = addressToCacheSetData(address);
    int64_t tagSet = addressToCacheSet(address);
    int64_t tagWay = m_tag_index[address];
    std::vector<std::vector<AbstractCacheEntry*>> &set = m_cache_data[dataSet];
    int dataWay = -1;
    for (int i = 0; i < m_data_array_assoc; i++) {
        int free = m_data_blk_vacancy[dataSet][i];
        if (free >= num_seg_per_data) {
            dataWay = i;
            DPRINTF(RubyCacheDecoupled, "   tag[%d,%d] will be linked to %d segments in data[%d,%d]\n", 
                tagSet, tagWay, num_seg_per_data,dataSet, dataWay);
            break;
        }
    }
    assert(dataWay >= 0);

    new_dataEntry->setPosition(dataSet, dataWay);
    new_dataEntry->setLastAccess(curTick());
    m_tag_data_ptr[tagSet][tagWay] = new_dataEntry; //tag to data

    for (int j = 0; j < m_num_seg_per_blk; j++) {
        if (!set[dataWay][j]) {
            DPRINTF(RubyCacheDecoupled, "   tag[%d,%d] linked to data[%d,%d,%d]\n", 
            tagSet, tagWay, dataSet, dataWay, j);
            set[dataWay][j] = new_dataEntry;  // Init entry
            m_tag_seg_cntr[tagSet][tagWay] += num_seg_per_data;
            m_data_head_tag_ptr[dataSet][dataWay][j] = m_cache[tagSet][tagWay]; //data to tag
            m_data_cntr[dataSet][dataWay][j] += 1;
            assert(m_data_cntr[dataSet][dataWay][j] <= 1);
            m_data_blk_vacancy[dataSet][dataWay] -= num_seg_per_data;
            new_dataEntry->replacementData = replacement_data_for_data[dataSet][dataWay][j];
            m_replacementPolicy_ptr_data->reset(new_dataEntry->replacementData);
            m_data_index[address] = j;

            cacheMemoryDecoupledStats.numSegInUse += num_seg_per_data;
            return;
        }
    }
    panic("linkDataToTag didn't find an available entry");
}

void
CacheMemoryDecoupled::unlinkDataToTag(Addr address) {
    DPRINTF(RubyCacheDecoupled, "unlinkDataToTag() in CacheMemoryDecoupled: %#x\n", address);
    AbstractCacheEntry* tagEntry = CacheMemory::lookup(address);
    assert(tagEntry != nullptr);
    uint32_t tagSet = tagEntry->getSet();
    uint32_t tagWay = tagEntry->getWay();
    AbstractCacheEntry* dataEntry = m_tag_data_ptr[tagSet][tagWay];
    assert(dataEntry != NULL);
    
    //locate data entry's index
    uint32_t dataSet = dataEntry->getSet();
    uint32_t dataWay = dataEntry->getWay();
    uint32_t dataSeg = m_num_seg_per_blk;
    for (int j = 0; j < m_num_seg_per_blk; j++) {
        if (dataEntry == m_cache_data[dataSet][dataWay][j]) {
            dataSeg = j;
            break;
        }
    }
    assert(dataSeg < m_num_seg_per_blk);

    DPRINTF(RubyCacheDecoupled, "  data is at [%d,%d,%d]\n", dataSet, dataWay, dataSeg);

    //decrement data cntr
    m_data_cntr[dataSet][dataWay][dataSeg] -= 1;
    if (m_data_cntr[dataSet][dataWay][dataSeg] == 0) {
        DPRINTF(RubyCacheDecoupled, "  no tag points to this data, deallocating...\n");
        //reset data's replacement data
        m_replacementPolicy_ptr_data->invalidate(dataEntry->replacementData);
        //delete data entry
        delete dataEntry;
        m_data_index.erase(address);
        
        //reset ptrs
        DPRINTF(RubyCacheDecoupled, "  freeing up %d segs in data[%d,%d]\n", 
            m_tag_seg_cntr[tagSet][tagWay], dataSet, dataWay);
        m_data_blk_vacancy[dataSet][dataWay] += m_tag_seg_cntr[tagSet][tagWay]; // now vacant
        m_cache_data[dataSet][dataWay][dataSeg] = NULL;
        m_tag_data_ptr[tagSet][tagWay] = NULL; //tag to data
        int seg_cntr = m_tag_seg_cntr[tagSet][tagWay];
        m_tag_seg_cntr[tagSet][tagWay] = 0; 
        m_data_head_tag_ptr[dataSet][dataWay][dataSeg] = NULL;
        cacheMemoryDecoupledStats.numSegInUse -= seg_cntr;
    }
    else {
        m_tag_data_ptr[tagSet][tagWay] = NULL; //tag to data
        DPRINTF(RubyCacheDecoupled, "  other tag still points to this data\n");
        assert(false);
    }
}

void
CacheMemoryDecoupled::updateLinkDataToTag(Addr address, int data_size) {
    DPRINTF(RubyCacheDecoupled, "updateLinkDataToTag() in CacheMemoryDecoupled: %#x\n", 
    address);
    int num_seg_per_data = divCeil(data_size,m_segment_size);
    DPRINTF(RubyCacheDecoupled, "updateLinkDataToTag:data_size=%dB, equivalent to %d segment\n", data_size, num_seg_per_data);
    // std::cout << "updateLinkDataToTag:data size=" << data_size << ", equivalent to " << num_seg_per_data << " segs." <<std::endl;

    AbstractCacheEntry* tagEntry = CacheMemory::lookup(address);
    assert(tagEntry != nullptr);
    uint32_t tagSet = tagEntry->getSet();
    uint32_t tagWay = tagEntry->getWay();

    AbstractCacheEntry* dataEntry = m_tag_data_ptr[tagSet][tagWay];
    assert(dataEntry != NULL);

    //locate data entry's index
    uint32_t dataSet = dataEntry->getSet();
    uint32_t dataWay = dataEntry->getWay();

    DPRINTF(RubyCacheDecoupled, "   touching data's repl data\n");
    m_replacementPolicy_ptr_data->touch(dataEntry->replacementData);
    dataEntry->setLastAccess(curTick());

    // check if contraction/expansion needed due to write data size change
    int need_more_seg = num_seg_per_data - m_tag_seg_cntr[tagSet][tagWay];
    if (need_more_seg < 0) {
        DPRINTF(RubyCacheDecoupled, "updateLinkDataToTag: contraction needed.\n");
        cacheMemoryDecoupledStats.numContraction++;

        // release unused part of original data
        DPRINTF(RubyCacheDecoupled, "  decreasing vancancy at original data[%d,%d] by %d\n",dataSet,dataWay,need_more_seg);
        m_data_blk_vacancy[dataSet][dataWay] -= need_more_seg; 
        DPRINTF(RubyCacheDecoupled, "  now %d\n",m_data_blk_vacancy[dataSet][dataWay]);

        m_tag_seg_cntr[tagSet][tagWay] = num_seg_per_data;

        cacheMemoryDecoupledStats.numSegInUse += need_more_seg; // add negative number

    } else if (need_more_seg > 0) {
        DPRINTF(RubyCacheDecoupled, "updateLinkDataToTag: expansion needed. should be enough space\n");
        // assert(cacheAvailData(address, data_size));
        cacheMemoryDecoupledStats.numExpansion++;

        // release original data
        DPRINTF(RubyCacheDecoupled, "  increasing vancancy at original data[%d,%d] by %d\n",dataSet,dataWay,m_tag_seg_cntr[tagSet][tagWay]);
        m_data_blk_vacancy[dataSet][dataWay] += m_tag_seg_cntr[tagSet][tagWay]; 
        DPRINTF(RubyCacheDecoupled, "  now %d\n",m_data_blk_vacancy[dataSet][dataWay]);

        int dataset_avail = -1;
        int dataway_avail = -1;
        cacheAvailData_set_way(address, data_size, &dataset_avail, &dataway_avail);
        assert(dataset_avail >= 0);
        assert(dataway_avail >= 0);

        // allocate new data
        DPRINTF(RubyCacheDecoupled, "  decreasing vancancy at avail data[%d,%d] by %d\n",dataset_avail,dataway_avail,num_seg_per_data);
        m_data_blk_vacancy[dataset_avail][dataway_avail] -= num_seg_per_data; 
        DPRINTF(RubyCacheDecoupled, "  now %d\n",m_data_blk_vacancy[dataset_avail][dataway_avail]);
        assert(m_data_blk_vacancy[dataset_avail][dataway_avail]<=m_num_seg_per_blk); 
        assert(m_data_blk_vacancy[dataset_avail][dataway_avail]>=0); 
        
        m_tag_seg_cntr[tagSet][tagWay] = num_seg_per_data;
        
        if (dataset_avail != dataSet || dataway_avail != dataWay) {
            DPRINTF(RubyCacheDecoupled, "migration due to expansion\n");
            cacheMemoryDecoupledStats.numExpMigration++;

            // === which ever pointer in m_cache_data that points to me, now need to migrate ===
            int seg_orig = findDataSegIdx(address);
            m_cache_data[dataSet][dataWay][seg_orig] = nullptr;
            DPRINTF(RubyCacheDecoupled, "data[%d,%d,%d] gone\n", dataSet, dataWay, seg_orig);
            //m_data_head_tag_ptr and m_data_cntr need to migrate
            assert(m_data_head_tag_ptr[dataSet][dataWay][seg_orig] == tagEntry);
            m_data_head_tag_ptr[dataSet][dataWay][seg_orig] = nullptr;
            int dcntr = m_data_cntr[dataSet][dataWay][seg_orig];
            m_data_cntr[dataSet][dataWay][seg_orig] = 0;

            int seg_avail = findEmptyDataSegIdx(dataset_avail, dataway_avail);
            m_cache_data[dataset_avail][dataway_avail][seg_avail] = dataEntry;
            m_data_index[address] = seg_avail;
            DPRINTF(RubyCacheDecoupled, "data[%d,%d,%d] added\n", dataset_avail, dataway_avail, seg_avail);
            assert(m_data_head_tag_ptr[dataset_avail][dataway_avail][seg_avail] == nullptr);
            m_data_head_tag_ptr[dataset_avail][dataway_avail][seg_avail] = tagEntry;
            assert(m_data_cntr[dataset_avail][dataway_avail][seg_avail] == 0);
            m_data_cntr[dataset_avail][dataway_avail][seg_avail] = dcntr;

            dataEntry->setPosition(dataset_avail, dataway_avail);
        }
        
        cacheMemoryDecoupledStats.numSegInUse += need_more_seg; // add positive number
    }
    else {
        DPRINTF(RubyCacheDecoupled, "updateLinkDataToTag: ok.\n");
    }
    
    assert(m_data_blk_vacancy[dataSet][dataWay]<=m_num_seg_per_blk); 
    assert(m_data_blk_vacancy[dataSet][dataWay]>=0); 
    
}

CacheMemoryDecoupled::
CacheMemoryDecoupledStats::CacheMemoryDecoupledStats(statistics::Group *parent)
    : statistics::Group(parent),
      ADD_STAT(block_size, "m_block_size"),
      ADD_STAT(segment_size, "m_segment_size"),
      ADD_STAT(numExpansion, "Number of write expansion"),
      ADD_STAT(numExpMigration, "Number of data migration due to write expansion"),
      ADD_STAT(numContraction, "Number of write contraction"),
      ADD_STAT(numReplDataArr, "Number of replacment due to data array"),
      ADD_STAT(numSegInUse, statistics::units::Rate<
                statistics::units::Count, statistics::units::Tick>::get(),
                "Number of data array segments in use (average)"),
      ADD_STAT(numTagInUse, statistics::units::Rate<
                statistics::units::Count, statistics::units::Tick>::get(),
                "Number of tags in use (average)"),
      ADD_STAT(compRatio, statistics::units::Rate<
                statistics::units::Ratio, statistics::units::Tick>::get(),
                "Compression ratio")
{
    numExpansion
        .flags(statistics::nozero);

    numExpMigration
        .flags(statistics::nozero);

    numContraction
        .flags(statistics::nozero);

    numReplDataArr
        .flags(statistics::nozero);

    numSegInUse
        .flags(statistics::nozero);

    numTagInUse
        .flags(statistics::nozero);

    compRatio
        .flags(statistics::nozero | statistics::nonan);
    
    block_size
        .flags(statistics::none);
    
    segment_size
        .flags(statistics::none);

    compRatio = numTagInUse * block_size / (numSegInUse * segment_size);

}

}
}