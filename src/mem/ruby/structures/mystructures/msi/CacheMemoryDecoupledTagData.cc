#include "debug/RubyCacheDecoupledTagData.hh"
#include "debug/RubyCacheUtil.hh"
#include "mem/ruby/structures/mystructures/msi/CacheMemoryDecoupledTagData.hh"
#include "mem/ruby/system/RubySystem.hh"

#include <iostream>

namespace gem5
{

namespace ruby
{

CacheMemoryDecoupledTagData::CacheMemoryDecoupledTagData(const Params &p)
    : CacheMemory(p),
    cacheMemoryDecoupledStats(this)
{
    m_data_array_assoc = p.dataArrayAssoc;
    m_data_array_set = p.dataArraySet;
    m_num_seg_per_blk = p.numSegPerBlk;
    m_replacementPolicy_ptr_data = p.replacement_policy_data;
    m_num_seg_per_set = m_num_seg_per_blk * m_data_array_assoc;
    m_print_util_interval_tick = p.print_util_interval_tick;
    
}

void
CacheMemoryDecoupledTagData::init()
{
    CacheMemory::init();
    if (m_data_array_set == 0) {
        m_data_array_set = m_cache_num_sets;
    }
    if (m_data_array_assoc == 0) {
        m_data_array_assoc = m_cache_assoc * m_cache_num_sets / 2; // a haved data cache
        m_num_seg_per_set = m_num_seg_per_blk * m_data_array_assoc; // set this again
    }
    std::cout << "Hello World! From a CacheMemoryDecoupledTagData! "<<m_num_seg_per_set <<
        " segs per set" << std::endl;
    m_data_num_set_bits = floorLog2(m_data_array_set);
    assert(m_data_num_set_bits >= 0);

    m_segment_size = m_block_size / m_num_seg_per_blk;

    cacheMemoryDecoupledStats.block_size = m_block_size;
    cacheMemoryDecoupledStats.segment_size = m_segment_size;

    // === ALLOCATE DATA ARR ===
    // 2d
    // allocate max amount of space for logical data -> 1 segment per logical data
    m_cache_data.resize(m_data_array_set,
                    std::vector<AbstractCacheEntry*>(m_num_seg_per_set, nullptr));
    // 2d
    replacement_data_for_data.resize(m_data_array_set,
                               std::vector<ReplData>(m_num_seg_per_set, nullptr));

    // instantiate all data replacement_data here
    // 2d
    for (int i = 0; i < m_data_array_set; i++) {
        for ( int j = 0; j < m_num_seg_per_set; j++) {
            replacement_data_for_data[i][j] =
                                m_replacementPolicy_ptr_data->instantiateEntry();
        }
    }

    // === allocate all connection management ptrs ===
    m_data_head_tag_ptr.resize(m_data_array_set, std::vector<AbstractCacheEntry*>(
        m_num_seg_per_set, nullptr));
    m_data_cntr.resize(m_data_array_set, std::vector<int>(m_num_seg_per_set, 0));
    
    m_data_set_vacancy.resize(m_data_array_set, int(m_num_seg_per_set));

    m_tag_next_tag_ptr.resize(m_cache_num_sets,
                    std::vector<AbstractCacheEntry*>(m_cache_assoc, nullptr));
    m_tag_prev_tag_ptr.resize(m_cache_num_sets,
                    std::vector<AbstractCacheEntry*>(m_cache_assoc, nullptr));
    m_tag_data_ptr.resize(m_cache_num_sets,
                    std::vector<AbstractCacheEntry*>(m_cache_assoc, nullptr));
    m_tag_seg_cntr.resize(m_cache_num_sets,
                    std::vector<int>(m_cache_assoc, 0));

    //stats
    cacheMemoryDecoupledStats.numSegInUse_max = 0;
    cacheMemoryDecoupledStats.numTagInUse_dc_max = 0;
    cacheMemoryDecoupledStats.numTagInUse_dc.reset();
    cacheMemoryDecoupledStats.numSegInUse.reset();

    std::cout << name() << "CacheMemoryDecoupledTagData::tag(set,way)=(" << m_cache_num_sets << "," << m_cache_assoc << ")" << std::endl;
    std::cout << name() << "CacheMemoryDecoupledTagData::data(set,way)=(" << m_data_array_set << "," << m_data_array_assoc << ")" << std::endl;
}

CacheMemoryDecoupledTagData::~CacheMemoryDecoupledTagData()
{
    // CacheMemory::~CacheMemory();
    m_data_cntr.clear();
    m_tag_seg_cntr.clear();
    m_data_set_vacancy.clear();
    if (m_replacementPolicy_ptr_data)
        delete m_replacementPolicy_ptr_data;
    // DELETE DATA ARR
    for (int i = 0; i < m_data_array_set; i++) {
        for (int j = 0; j < m_num_seg_per_set; j++) {
            delete m_cache_data[i][j];
            delete m_data_head_tag_ptr[i][j];
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


// Sets the most recently used bit for a cache block
void
CacheMemoryDecoupledTagData::setMRU(Addr address)
{
    CacheMemory::setMRU(address);
    AbstractCacheEntry* tagEntry = lookup(makeLineAddress(address));
    if (tagEntry != nullptr) {
        AbstractCacheEntry* dataEntry = m_tag_data_ptr[tagEntry->getSet()][tagEntry->getWay()];
        if (dataEntry != nullptr) {
            m_replacementPolicy_ptr_data->touch(dataEntry->replacementData);
            dataEntry->setLastAccess(curTick());
        }
    }
}

// convert a Address to its location in the cache
int64_t
CacheMemoryDecoupledTagData::addressToCacheSetData(Addr address) const
{
    assert(address == makeLineAddress(address));
    if (m_data_num_set_bits == 0){
        return 0;
    }
    return bitSelect(address, m_start_index_bit,
                     m_start_index_bit + m_data_num_set_bits - 1);
}

int
CacheMemoryDecoupledTagData::findDataSegIdx(Addr address) const {
    int seg = -1;
    auto it = m_data_index.find(address);
    if (it != m_data_index.end()) {
            seg = it->second;
    }
    assert(seg>=0);
    return seg;
}

int
CacheMemoryDecoupledTagData::findEmptyDataSegIdx(int dataSet) const {
    int seg_empty = -1;
    for (int i = 0; i < m_num_seg_per_set; i++) {
        if (!m_cache_data[dataSet][i]) {
            seg_empty = i;
            break;
        }
    }
    assert(seg_empty >= 0);
    return seg_empty;
}

void
CacheMemoryDecoupledTagData::profileReplacementDataArray() {
    cacheMemoryDecoupledStats.numReplDataArr++;
}

// tests to see if an address is present in the cache data array
bool
CacheMemoryDecoupledTagData::isDataPresent(Addr address) const
{
    const AbstractCacheEntry* const tagEntry = CacheMemory::lookup(address);
    if (tagEntry == nullptr) {
        // We didn't find the tag, therefore no data as well
        DPRINTF(RubyCacheDecoupledTagData, "   No tag (nor data) match for address: %#x\n", address);
        return false;
    }
    uint32_t set = tagEntry->getSet();
    uint32_t way = tagEntry->getWay();

    if (m_tag_data_ptr[set][way] == nullptr) {
        // There is tag but no data
        DPRINTF(RubyCacheDecoupledTagData, "   tag match for address: %#x, but no data\n", address);
        return false;
    }
    DPRINTF(RubyCacheDecoupledTagData, "   address: %#x with data found\n", address);
    return true;
}

AbstractCacheEntry* 
CacheMemoryDecoupledTagData::lookupData(Addr address) const
{
    const AbstractCacheEntry* const tagEntry = CacheMemory::lookup(address);
    assert(tagEntry != nullptr);
    uint32_t set = tagEntry->getSet();
    uint32_t way = tagEntry->getWay();
    assert (m_tag_data_ptr[set][way] != nullptr);
    return m_tag_data_ptr[set][way];
}


// Returns true if there is:
//   a) a tag match on this address with allocated data entry or there is
//   b) an unused space in the same cache set for data array
bool
CacheMemoryDecoupledTagData::cacheAvailData(Addr address, int data_size) const
{
    DPRINTF(RubyCacheDecoupledTagData, "cacheAvailData() in CacheMemoryDecoupledTagData: %#x\n",address);
    int num_seg_per_data = divCeil(data_size,m_segment_size);
    DPRINTF(RubyCacheDecoupledTagData, "cacheAvailData:data_size=%dB, equivalent to %d segment\n", data_size, num_seg_per_data);
    // std::cout << "cacheAvailData:data size=" << data_size << ", equivalent to " << num_seg_per_data << " segs." <<std::endl;
    assert(address == makeLineAddress(address));

    int64_t cacheSet = CacheMemory::addressToCacheSet(address);
    for (int i = 0; i < m_cache_assoc; i++) {
        AbstractCacheEntry* tagEntry = m_cache[cacheSet][i];
        if (tagEntry != NULL) {
            if (tagEntry->m_Address == address) {
                uint32_t set = tagEntry->getSet();
                uint32_t way = tagEntry->getWay();
                int has = m_tag_seg_cntr[set][way];
                if (has >= num_seg_per_data) {
                    // Already in the cache and there is data
                    DPRINTF(RubyCacheDecoupledTagData, "   address %#x already exists and has %d data segment(s)\n",address, has);
                    return true;
                }
            }
        }
    }

    int64_t dataSet = addressToCacheSetData(address);
    int has_free = m_data_set_vacancy[dataSet];
    if (has_free >= num_seg_per_data) {
        DPRINTF(RubyCacheDecoupledTagData, 
            "   address %#x data array has enough (%d>=%d) space in set %d\n",
            address,has_free,num_seg_per_data,dataSet);
        return true;
    }
    DPRINTF(RubyCacheDecoupledTagData, "   no more space in data array in set %d, has_free=%d\n",dataSet,has_free);
    return false;
}

bool
CacheMemoryDecoupledTagData::cacheAvailData(Addr address) const
{
    return cacheAvailData(address, m_block_size);
}

// Returns true if there is enough space to coallocate, i.e., no need to replace!
bool
CacheMemoryDecoupledTagData::cacheCanCoallocate(Addr address, int data_size) const
{
    DPRINTF(RubyCacheDecoupledTagData, "cacheCanCoallocate() in CacheMemoryDecoupledTagData: %#x\n",address);
    int num_seg_per_data = divCeil(data_size,m_segment_size);
    DPRINTF(RubyCacheDecoupledTagData, "cacheCanCoallocate:data_size=%dB, equivalent to %d segment\n", data_size, num_seg_per_data);
    assert(address == makeLineAddress(address));

    int64_t cacheSet = CacheMemory::addressToCacheSet(address);
    // bool found_address_match = false;

    for (int i = 0; i < m_cache_assoc; i++) {
        AbstractCacheEntry* entry = m_cache[cacheSet][i];
        if (entry != NULL) {
            if (entry->m_Address == address) {
                // found_address_match = true;
                uint32_t set = entry->getSet();
                uint32_t way = entry->getWay();
                int already_has = m_tag_seg_cntr[set][way];
                if (already_has >= num_seg_per_data) {
                    // Already in the cache and there is data
                    DPRINTF(RubyCacheDecoupledTagData, 
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
                        DPRINTF(RubyCacheDecoupledTagData, 
                        "   address %#x already exists, has %d data segment(s), also %d free.=>can coallocate\n",
                        address, already_has, has_free);
                        return true;
                    }
                    else {
                        DPRINTF(RubyCacheDecoupledTagData, 
                        "   address %#x already exists but only has %d data segment(s) now and %d free.\n",
                        address, already_has, has_free);
                    }
                }
            }
        }
    }
    // assert(found_address_match);

    int64_t dataSet = addressToCacheSetData(address);
    int has_free = m_data_set_vacancy[dataSet];
    if (has_free >= num_seg_per_data) {
        DPRINTF(RubyCacheDecoupledTagData, 
            "   address %#x data array has enough (%d>=%d) space in set %d.=>can coallocate\n",
            address,has_free,num_seg_per_data,dataSet);
        return true;
    }
    DPRINTF(RubyCacheDecoupledTagData, "   no more space in data array in set %d.=>cannot coallocate\n",dataSet);
    return false;
}

AbstractCacheEntry*
CacheMemoryDecoupledTagData::allocateTagData(Addr address, AbstractCacheEntry *new_tag_entry, AbstractCacheEntry *new_data_entry)
{
    DPRINTF(RubyCacheDecoupledTagData, "allocateTagData(%#x) in CacheMemoryDecoupledTagData\n",address);
    AbstractCacheEntry *retEntry = CacheMemory::allocate(address, new_tag_entry);
    cacheMemoryDecoupledStats.numTagInUse_dc++;
    if (cacheMemoryDecoupledStats.numTagInUse_dc.value() > cacheMemoryDecoupledStats.numTagInUse_dc_max.value()) {
        cacheMemoryDecoupledStats.numTagInUse_dc_max = cacheMemoryDecoupledStats.numTagInUse_dc.value();
    }
    DPRINTF(RubyCacheDecoupledTagData, "in tag[%d,%d]\n",retEntry->getSet(), retEntry->getWay());

    // print out the number of tags in use every interval (10 billion) ticks
    if (curTick() - last_print_tick >= m_print_util_interval_tick) {
        last_print_tick = curTick();
        float tag_util = 100.0 * cacheMemoryStats.numTagInUse.value() / (float)(m_cache_num_sets * m_cache_assoc);
        float data_util = 100.0 * cacheMemoryDecoupledStats.numSegInUse.value() / (float)(m_num_seg_per_blk * m_data_array_set * m_data_array_assoc);
        DPRINTF(RubyCacheUtil, "%d: numTagInUse=%d(%.2f%%), numSegInUse=%d(%.2f%%)\n", 
            curTick()/m_print_util_interval_tick, 
            cacheMemoryStats.numTagInUse.value(),
            tag_util,
            cacheMemoryDecoupledStats.numSegInUse.value(),
            data_util
            );
    }

    linkDataToTag(retEntry, new_data_entry, m_block_size);

    return retEntry;
}

void
CacheMemoryDecoupledTagData::deallocateTagData(Addr address)
{
    DPRINTF(RubyCacheDecoupledTagData, "deallocateTagData(%#x) in CacheMemoryDecoupledTagData\n", address);
    unlinkDataToTag(address);
    CacheMemory::deallocate(address);
    cacheMemoryDecoupledStats.numTagInUse_dc--;
    if (cacheMemoryDecoupledStats.numTagInUse_dc.value() > cacheMemoryDecoupledStats.numTagInUse_dc_max.value()) {
        cacheMemoryDecoupledStats.numTagInUse_dc_max = cacheMemoryDecoupledStats.numTagInUse_dc.value();
    }
}

// Returns with the physical address of the conflicting cache line for data array
Addr
CacheMemoryDecoupledTagData::cacheProbeData(Addr address) const
{
    DPRINTF(RubyCacheDecoupledTagData, "cacheProbeData() in CacheMemoryDecoupledTagData\n");
    assert(address == makeLineAddress(address));
    assert(cacheAvail(address));

    int64_t dataSet = addressToCacheSetData(address);
    DPRINTF(RubyCacheDecoupledTagData, "  set in data: %d\n", dataSet);

    // collect replacement candidates
    std::vector<ReplaceableEntry*> candidates;
    for (int i = 0; i < m_num_seg_per_set; i++) {
        if (m_cache_data[dataSet][i] != NULL) {
            if (m_data_head_tag_ptr[dataSet][i]->m_Address != address) {
                    // if this entry is not null and not my own data, then consider as candidate
                    candidates.push_back(static_cast<ReplaceableEntry*>(
                                                                m_cache_data[dataSet][i]));
                    DPRINTF(RubyCacheDecoupledTagData, 
                    "       - data[%d,%d] added as candidate\n", dataSet, i);
            }
            else {
                DPRINTF(RubyCacheDecoupledTagData, 
                    "       - data[%d,%d] is myself, skipping\n", dataSet, i);
            }
        }
    }
    assert(candidates.size() > 0);
    DPRINTF(RubyCacheDecoupledTagData, "    arbitrating among %d candidates\n", candidates.size());

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
    DPRINTF(RubyCacheDecoupledTagData, "  identified conflicting data[%d,%d]\n", 
    dataSet, vSeg);

    assert(m_data_head_tag_ptr[dataSet][vSeg] != NULL);
    DPRINTF(RubyCacheDecoupledTagData, "  identified its associated tag[%d,%d]\n", 
    m_data_head_tag_ptr[dataSet][vSeg]->getSet(),
    m_data_head_tag_ptr[dataSet][vSeg]->getWay());

    // I can not decide that i need to evict my own tag to make space for myself
    assert(m_data_head_tag_ptr[dataSet][vSeg]->m_Address != address);

    return m_data_head_tag_ptr[dataSet][vSeg]->m_Address;
}

void
CacheMemoryDecoupledTagData::linkDataToTag(Addr address, AbstractCacheEntry* new_dataEntry) 
{
    linkDataToTag(address, new_dataEntry, m_block_size);
}

void
CacheMemoryDecoupledTagData::linkDataToTag(Addr address, AbstractCacheEntry* new_dataEntry, int data_size) {
    DPRINTF(RubyCacheDecoupledTagData, "=====linkDataToTag() in CacheMemoryDecoupledTagData=====\n");
    int num_seg_per_data = divCeil(data_size,m_segment_size);
    DPRINTF(RubyCacheDecoupledTagData, "0.linkDataToTag:data_size=%dB, equivalent to %d segment\n", data_size, num_seg_per_data);

    assert(address == makeLineAddress(address));
    assert(CacheMemory::isTagPresent(address));
    assert(cacheAvailData(address, data_size));
    DPRINTF(RubyCacheDecoupledTagData, "   1.address: %#x data filing...\n", address);
    
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
        DPRINTF(RubyCacheDecoupledTagData, "   2.tag[%d,%d] will be linked to %d segments in data[%d]\n", 
            tagSet, tagWay, num_seg_per_data,dataSet);
    }
    else {
        assert(false);
    }

    new_dataEntry->setLastAccess(curTick());
    m_tag_data_ptr[tagSet][tagWay] = new_dataEntry; //tag to data

    for (int j = 0; j < m_num_seg_per_set; j++) {
        if (m_cache_data[dataSet][j] == NULL) {
            DPRINTF(RubyCacheDecoupledTagData, "   3.tag[%d,%d] linking to data[%d,%d]\n", 
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
CacheMemoryDecoupledTagData::linkDataToTag(AbstractCacheEntry *tagEntry, AbstractCacheEntry* new_dataEntry, int data_size) {
    DPRINTF(RubyCacheDecoupledTagData, "=====linkDataToTag() in CacheMemoryDecoupledTagData=====\n");
    int num_seg_per_data = divCeil(data_size,m_segment_size);
    DPRINTF(RubyCacheDecoupledTagData, "0.linkDataToTag:data_size=%dB, equivalent to %d segment\n", data_size, num_seg_per_data);

    assert(tagEntry != nullptr);
    uint32_t tagSet = tagEntry->getSet();
    uint32_t tagWay = tagEntry->getWay();

    // Find the first open slot in data array
    Addr address = tagEntry->m_Address;
    int64_t dataSet = addressToCacheSetData(address);
    int free = m_data_set_vacancy[dataSet];
    if (free >= num_seg_per_data) {
        DPRINTF(RubyCacheDecoupledTagData, "   2.tag[%d,%d] will be linked to %d segments in data[%d]\n", 
            tagSet, tagWay, num_seg_per_data,dataSet);
    }
    else {
        assert(false);
    }

    new_dataEntry->setLastAccess(curTick());
    m_tag_data_ptr[tagSet][tagWay] = new_dataEntry; //tag to data

    for (int j = 0; j < m_num_seg_per_set; j++) {
        if (m_cache_data[dataSet][j] == NULL) {
            DPRINTF(RubyCacheDecoupledTagData, "   3.tag[%d,%d] linking to data[%d,%d]\n", 
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
CacheMemoryDecoupledTagData::unlinkDataToTag(Addr address) {
    DPRINTF(RubyCacheDecoupledTagData, "=====unlinkDataToTag() in CacheMemoryDecoupledTagData: %#x=====\n", address);
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

    DPRINTF(RubyCacheDecoupledTagData, "  0.data is at [%d,%d]\n", dataSet, dataSeg);

    //decrement data cntr
    m_data_cntr[dataSet][dataSeg] -= 1;
    if (m_data_cntr[dataSet][dataSeg] == 0) {
        DPRINTF(RubyCacheDecoupledTagData, "  1.no tag points to this data, deallocating...\n");
        //reset data's replacement data
        m_replacementPolicy_ptr_data->invalidate(dataEntry->replacementData);
        //delete data entry
        delete dataEntry;
        m_data_index.erase(address);
        
        //reset ptrs
        DPRINTF(RubyCacheDecoupledTagData, "  1a.freeing up %d segs in data[%d]\n", 
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
        m_tag_data_ptr[tagSet][tagWay] = NULL; //tag to data
        DPRINTF(RubyCacheDecoupledTagData, "  1.other tag still points to this data\n");
        assert(false);
    }
}

void
CacheMemoryDecoupledTagData::profileDataUpdate(Addr address, int data_size)
{
    int num_seg_per_data = divCeil(data_size,m_segment_size);
    // lookup tag
    AbstractCacheEntry* tagEntry = lookup(address);
    assert(tagEntry != nullptr);
    int tagSet = tagEntry->getSet();
    int tagWay = tagEntry->getWay();
    assert(m_cache[tagSet][tagWay]->m_Address == address);
    int has = m_tag_seg_cntr[tagSet][tagWay];
    int num_more_seg_needed = num_seg_per_data - has;
    if (num_more_seg_needed > 0) {
        cacheMemoryDecoupledStats.numExpansion++;
        DPRINTF(RubyCacheDecoupledTagData, "expansion detected\n");
    }
    else if (num_more_seg_needed < 0) {
        cacheMemoryDecoupledStats.numContraction++;
        DPRINTF(RubyCacheDecoupledTagData, "contraction detected\n");
    }
}

void
CacheMemoryDecoupledTagData::profileDataOverprovision()
{
    cacheMemoryDecoupledStats.numOverprovisioned += 1;
}

void
CacheMemoryDecoupledTagData::updateLinkDataToTag(Addr address, int data_size) {
    DPRINTF(RubyCacheDecoupledTagData, "updateLinkDataToTag() in CacheMemoryDecoupledTagData: %#x\n", 
    address);
    int num_seg_per_data = divCeil(data_size,m_segment_size);
    DPRINTF(RubyCacheDecoupledTagData, "updateLinkDataToTag:data_size=%dB, equivalent to %d segment\n", data_size, num_seg_per_data);
    // std::cout << "updateLinkDataToTag:data size=" << data_size << ", equivalent to " << num_seg_per_data << " segs." <<std::endl;

    AbstractCacheEntry* tagEntry = CacheMemory::lookup(address);
    assert(tagEntry != nullptr);
    uint32_t tagSet = tagEntry->getSet();
    uint32_t tagWay = tagEntry->getWay();

    AbstractCacheEntry* dataEntry = m_tag_data_ptr[tagSet][tagWay];
    assert(dataEntry != NULL);

    //locate data entry's index
    uint32_t dataSet = dataEntry->getSet();

    DPRINTF(RubyCacheDecoupledTagData, "   touching data's repl data\n");
    m_replacementPolicy_ptr_data->touch(dataEntry->replacementData);
    dataEntry->setLastAccess(curTick());

    // check if contraction/expansion needed due to write data size change
    int need_more_seg = num_seg_per_data - m_tag_seg_cntr[tagSet][tagWay];
    if (need_more_seg < 0) {
        DPRINTF(RubyCacheDecoupledTagData, "updateLinkDataToTag: contraction needed.\n");
        cacheMemoryDecoupledStats.numContraction++;

        // release unused part of original data
        DPRINTF(RubyCacheDecoupledTagData, "  decreasing vancancy at original data[%d] by %d\n",dataSet,need_more_seg);
        m_data_set_vacancy[dataSet] -= need_more_seg; 
        DPRINTF(RubyCacheDecoupledTagData, "  now %d\n",m_data_set_vacancy[dataSet]);

        m_tag_seg_cntr[tagSet][tagWay] = num_seg_per_data;

        cacheMemoryDecoupledStats.numSegInUse += need_more_seg; // add negative number
        if (cacheMemoryDecoupledStats.numSegInUse.value() > cacheMemoryDecoupledStats.numSegInUse_max.value()) {
            cacheMemoryDecoupledStats.numSegInUse_max = cacheMemoryDecoupledStats.numSegInUse.value();
        }
        

    } else if (need_more_seg > 0) {
        DPRINTF(RubyCacheDecoupledTagData, "updateLinkDataToTag: expansion needed. should be enough space\n");
        // assert(cacheAvailData(address, data_size));
        cacheMemoryDecoupledStats.numExpansion++;

        // allocate more in original data
        DPRINTF(RubyCacheDecoupledTagData, "  decreasing vancancy at original data[%d] by %d\n",dataSet,need_more_seg);
        m_data_set_vacancy[dataSet] -= need_more_seg; 
        DPRINTF(RubyCacheDecoupledTagData, "  now %d\n",m_data_set_vacancy[dataSet]);

        m_tag_seg_cntr[tagSet][tagWay] = num_seg_per_data;
        
        cacheMemoryDecoupledStats.numSegInUse += need_more_seg; // add positive number
        if (cacheMemoryDecoupledStats.numSegInUse.value() > cacheMemoryDecoupledStats.numSegInUse_max.value()) {
            cacheMemoryDecoupledStats.numSegInUse_max = cacheMemoryDecoupledStats.numSegInUse.value();
        }
    }
    else {
        DPRINTF(RubyCacheDecoupledTagData, "updateLinkDataToTag: ok.\n");
    }
    
    assert(m_data_set_vacancy[dataSet]<=m_num_seg_per_set); 
    assert(m_data_set_vacancy[dataSet]>=0); 
    
}

void
CacheMemoryDecoupledTagData::addToTail(AbstractCacheEntry* tagHead, AbstractCacheEntry* tagEntry)
{
    int tagHeadSet = tagHead->getSet();
    int tagHeadWay = tagHead->getWay();
    assert(m_tag_prev_tag_ptr[tagHeadSet][tagHeadWay] == nullptr); // head should not have previous tag

    assert(m_tag_data_ptr[tagHeadSet][tagHeadWay] != nullptr);
    // std::cout << "addToTail(" << m_data_cntr[dataSet][dataWay] << ")";


    assert(tagEntry != nullptr);
    int tagNewSet = tagEntry->getSet();
    int tagNewWay = tagEntry->getWay();
    assert(m_tag_next_tag_ptr[tagNewSet][tagNewWay] == nullptr); //float
    assert(m_tag_prev_tag_ptr[tagNewSet][tagNewWay] == nullptr); //float
    // DPRINTF(RubyCacheDecoupledTagData, "addToTail:<head>tag[%d,%d]->", tagHeadSet, tagHeadWay);
    // std::cout << "<head>tag["<< tagHeadSet<< "," <<tagHeadWay<< "]-> ";

    if (m_tag_next_tag_ptr[tagHeadSet][tagHeadWay] == nullptr) {
        assert(m_data_cntr[m_tag_data_ptr[tagHeadSet][tagHeadWay]->getSet()][m_tag_data_ptr[tagHeadSet][tagHeadWay]->getWay()] == 1);
        // forward
        m_tag_next_tag_ptr[tagHeadSet][tagHeadWay] = tagEntry;
        //backward
        m_tag_prev_tag_ptr[tagNewSet][tagNewWay] = tagHead;
        // DPRINTF(RubyCacheDecoupledTagData, "<new>tag[%d,%d]\n", tagNewSet, tagNewWay);
        // std::cout << "<new>tag["<< tagNewSet<< "," <<tagNewWay << "]" << std::endl;
    }
    else {
        AbstractCacheEntry* tagCur = m_tag_next_tag_ptr[tagHeadSet][tagHeadWay];
        int tagCurSet = tagCur->getSet();
        int tagCurWay = tagCur->getWay();
        // std::cout << "tag["<< tagCurSet<< "," <<tagCurWay << "]-> ";
        while (m_tag_next_tag_ptr[tagCurSet][tagCurWay] != nullptr) {
            tagCur = m_tag_next_tag_ptr[tagCurSet][tagCurWay];
            tagCurSet = tagCur->getSet();
            tagCurWay = tagCur->getWay();
            // DPRINTF(RubyCacheDecoupledTagData, "tag[%d,%d]->", tagCurSet, tagCurWay);
            // std::cout << "tag["<< tagCurSet<< "," <<tagCurWay << "]-> ";
        }
        // add to tail
        //fwd
        m_tag_next_tag_ptr[tagCurSet][tagCurWay] = tagEntry;
        //backward
        m_tag_prev_tag_ptr[tagNewSet][tagNewWay] = tagCur;
        // DPRINTF(RubyCacheDecoupledTagData, "<new>tag[%d,%d]\n", tagNewSet, tagNewWay);
        // std::cout << "<new>tag["<< tagNewSet<< "," <<tagNewWay << "]" << std::endl;
    }
}

void
CacheMemoryDecoupledTagData::removeFromList(AbstractCacheEntry* tagHead, AbstractCacheEntry* tagEntry)
{
    int tagHeadSet = tagHead->getSet();
    int tagHeadWay = tagHead->getWay();
    assert(m_tag_prev_tag_ptr[tagHeadSet][tagHeadWay] == nullptr); // head should not have previous tag

    AbstractCacheEntry* dataEntry = m_tag_data_ptr[tagHeadSet][tagHeadWay];
    assert(dataEntry != nullptr);
    int dataSet = dataEntry->getSet();
    int dataWay = dataEntry->getWay();
    assert(m_data_cntr[dataSet][dataWay]>1);
    // std::cout << "removeFromList(" << m_data_cntr[dataSet][dataWay] << ")";

    assert(tagEntry != nullptr);
    int tagNewSet = tagEntry->getSet();
    int tagNewWay = tagEntry->getWay();

    if (tagHead == tagEntry) {
        // what needs to be removed is the head itself
        AbstractCacheEntry* new_head = m_tag_next_tag_ptr[tagNewSet][tagNewWay];
        // clear new head's prev
        m_tag_prev_tag_ptr[new_head->getSet()][new_head->getWay()] = nullptr;
        // data to head tag pointer update
        m_data_head_tag_ptr[dataSet][dataWay] = new_head;
        // std::cout << ", the head"<<std::endl;

    }
    else if (m_tag_next_tag_ptr[tagNewSet][tagNewWay] == nullptr) {
        // what needs to be removed is the tail itself
        AbstractCacheEntry* new_tail = m_tag_prev_tag_ptr[tagNewSet][tagNewWay];
        // clear new tail's next
        m_tag_next_tag_ptr[new_tail->getSet()][new_tail->getWay()] = nullptr;
        // std::cout << ", the tail"<<std::endl;
    }
    else {
        // a body needs to be removed
        AbstractCacheEntry* prev_tag = m_tag_prev_tag_ptr[tagNewSet][tagNewWay];
        AbstractCacheEntry* next_tag = m_tag_next_tag_ptr[tagNewSet][tagNewWay];
        // link prev's next to next
        m_tag_next_tag_ptr[prev_tag->getSet()][prev_tag->getWay()] = next_tag;
        // link next's prev to prev
        m_tag_prev_tag_ptr[next_tag->getSet()][next_tag->getWay()] = prev_tag;
        // std::cout << ", a body"<<std::endl;
    }
    // make the removed one float
    m_tag_prev_tag_ptr[tagNewSet][tagNewWay] = nullptr;
    m_tag_next_tag_ptr[tagNewSet][tagNewWay] = nullptr;
}


CacheMemoryDecoupledTagData::
CacheMemoryDecoupledTagDataStats::CacheMemoryDecoupledTagDataStats(statistics::Group *parent)
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
      ADD_STAT(numTagInUse_dc, statistics::units::Rate<
                statistics::units::Count, statistics::units::Tick>::get(),
                "Number of tags in use (average)"),
      ADD_STAT(compRatio, statistics::units::Rate<
                statistics::units::Ratio, statistics::units::Tick>::get(),
                "Compression ratio"),
      ADD_STAT(numOverprovisioned,"Number of times data array segments overprovisioned"),
      ADD_STAT(numSegInUse_max, "numSegInUse max value"),
      ADD_STAT(numTagInUse_dc_max, "numTagInUse_dc max value")
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

    numTagInUse_dc
        .flags(statistics::nozero);

    compRatio
        .flags(statistics::nozero | statistics::nonan);
    
    block_size
        .flags(statistics::none);
    
    segment_size
        .flags(statistics::none);

    compRatio = numTagInUse_dc * block_size / (numSegInUse * segment_size);

    numOverprovisioned
        .flags(statistics::nozero);

    numSegInUse_max
        .flags(statistics::nozero | statistics::nonan);
    

    numTagInUse_dc_max
        .flags(statistics::nozero | statistics::nonan);
}

}
}