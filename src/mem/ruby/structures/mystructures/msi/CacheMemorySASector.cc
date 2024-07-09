#include "debug/RubyCacheSASector.hh"
#include "mem/ruby/structures/mystructures/msi/CacheMemorySASector.hh"
#include "mem/ruby/system/RubySystem.hh"

#include <iostream>

//CacheMemorySASector is SET associative cache with sector granularity

namespace gem5
{

namespace ruby
{

CacheMemorySASector::CacheMemorySASector(const Params &p)
    : CacheMemory(p),
    cacheMemorySASectorStats(this)
{
    m_full_percentage = p.full_percentage;
    gem5::statistics::registerDumpCallback([this]() { calculateStatAtEnd(); });
}

void
CacheMemorySASector::init()
{
    CacheMemory::init();
    m_num_bytes_in_use = 0;
    std::cout << "Hello World! From a CacheMemorySASector! "<< std::endl;
    m_size_in_set_vec = std::vector<int>(m_cache_num_sets, 0);
}

CacheMemorySASector::~CacheMemorySASector()
{
    m_size_map.clear();
    m_size_in_set_vec.clear();
}


void
CacheMemorySASector::calculateStatAtEnd()
{
    cacheMemorySASectorStats.util_byte = (float) cacheMemorySASectorStats.numByteInUse.value() / (m_cache_num_sets * m_cache_assoc) * 100;
    cacheMemorySASectorStats.compression_ratio_intra = (float) 64 / ((float) cacheMemorySASectorStats.numByteInUse.value() / (float) cacheMemoryStats.numTagInUse.value());
}

// rewriting the allocation function
AbstractCacheEntry*
CacheMemorySASector::allocate(Addr address, AbstractCacheEntry *entry)
{
    return CacheMemorySASector::allocate(address, entry, m_block_size);
}

AbstractCacheEntry*
CacheMemorySASector::allocate(Addr address, AbstractCacheEntry *entry, int size)
{
    int64_t set = addressToCacheSet(address);
    assert(m_cache_assoc - m_size_in_set_vec[set] >= size);

    m_num_bytes_in_use += size;
    cacheMemorySASectorStats.numByteInUse += size;
    m_size_map[address] = size;
    
    m_size_in_set_vec[set] += size;
    DPRINTF(RubyCacheSASector, "alloc 0x%llx size=%d, set[%d] now remaining %d\n", 
        address, size, set, m_cache_assoc-m_size_in_set_vec[set]);
    return CacheMemory::allocate(address, entry);
}

// rewriting the deallocation function
void
CacheMemorySASector::deallocate(Addr address)
{
    int size;
    auto it = m_size_map.find(address);
    if (it != m_size_map.end()) {
        size = it->second;
    } else {
        panic("Address not found in size map");
    }

    DPRINTF(RubyCacheSASector, "dealloc 0x%llx size=%d\n", address, size);

    m_num_bytes_in_use -= size;
    cacheMemorySASectorStats.numByteInUse -= size;
    CacheMemory::deallocate(address);
    m_size_map.erase(address);
    m_size_in_set_vec[addressToCacheSet(address)] -= size;
}

void
CacheMemorySASector::changeAddr(Addr original_addr, Addr new_addr)
{
    // get the original entry
    AbstractCacheEntry* original_entry = lookup(original_addr);
    assert(original_entry != nullptr);
    original_entry->m_Address = new_addr;

    uint32_t original_cacheSet = original_entry->getSet();
    uint32_t original_cacheWay = original_entry->getWay();
    ReplData original_repldata = m_cache[original_cacheSet][original_cacheWay]->replacementData;

    // Find the first open slot
    int64_t new_cacheSet = addressToCacheSet(new_addr);

    if (new_cacheSet != original_cacheSet) {
        cacheMemorySASectorStats.numBlockMigrationAcrossSet++;
        DPRINTF(RubyCacheSASector, "change 0x%llx to 0x%llx, from set [%d] to set [%d]\n", 
            original_addr, new_addr, original_cacheSet, new_cacheSet);
        assert(m_cache_assoc - m_size_in_set_vec[new_cacheSet] >= m_size_map[original_addr]);
    } else {
        return; // no need to actually swap
    }

    bool found_open_slot = false;
    int new_cacheWay = -1;
    std::vector<AbstractCacheEntry*> &set = m_cache[new_cacheSet];
    for (int i = 0; i < m_cache_assoc; i++) {
        if (!set[i] || set[i]->m_Permission == AccessPermission_NotPresent) {
            if (set[i] && (set[i] != original_entry)) {
                assert(false);
            }
            found_open_slot = true;
            new_cacheWay = i;
        }
    }
    assert(found_open_slot);
    DPRINTF(RubyCacheSASector, "found_open_slot=%d\n", found_open_slot);

    AbstractCacheEntry* new_entry = set[new_cacheWay];

    // swap m_cache
    set[new_cacheWay] = original_entry;
    m_cache[original_cacheSet][original_cacheWay] = new_entry;
    // swap replacementData
    replacement_data[new_cacheSet][new_cacheWay] = original_repldata;
    if (new_entry != nullptr) {
        replacement_data[original_cacheSet][original_cacheWay] = new_entry->replacementData;
        new_entry->setPosition(original_cacheSet, original_cacheWay);
    }

    original_entry->setPosition(new_cacheSet, new_cacheWay);

    m_tag_index.erase(original_addr);
    m_tag_index[new_addr] = new_cacheWay;
    m_size_map[new_addr] = m_size_map[original_addr];
    m_size_map.erase(original_addr);
    m_size_in_set_vec[original_cacheSet] -= m_size_map[new_addr];
    m_size_in_set_vec[new_cacheSet] += m_size_map[new_addr];

    assert(lookup(original_addr) == nullptr && lookup(new_addr) != nullptr);

    DPRINTF(RubyCacheSASector, "change 0x%llx to 0x%llx, size=%d\n", 
        original_addr, new_addr, m_size_map[new_addr]);
}


// rewriting the cacheProbe function
Addr
CacheMemorySASector::candidateProbe(Addr address) const
{
    assert(address == makeLineAddress(address));
    // assert(!cacheAvail(address)); // we are using this function to probe 
    // the xor candidate so we dont need this check

    int64_t cacheSet = addressToCacheSet(address);
    std::vector<ReplaceableEntry*> candidates;
    candidates.clear();
    for (int i = 0; i < m_cache_assoc; i++) {
        if (m_cache[cacheSet][i] != nullptr) {
            if (m_cache[cacheSet][i]->m_Address != address) {
                candidates.push_back(static_cast<ReplaceableEntry*>(
                                                            m_cache[cacheSet][i]));
                DPRINTF(RubyCacheSASector, "candidateProbe added 0x%llx, way %d\n", 
                    m_cache[cacheSet][i]->m_Address, m_cache[cacheSet][i]->getWay());
            }
        }
    }
    assert(candidates.size() > 0);
    Addr ret_addr = m_cache[cacheSet][m_replacementPolicy_ptr->
                        getVictim(candidates)->getWay()]->m_Address;
    DPRINTF(RubyCacheSASector, "candidateProbe found victim 0x%llx among %d candidates\n", 
        ret_addr, candidates.size());
    return ret_addr;
}

int
CacheMemorySASector::candidateCount(Addr address) const
{
    assert(address == makeLineAddress(address));

    int64_t cacheSet = addressToCacheSet(address);
    std::vector<ReplaceableEntry*> candidates;
    for (int i = 0; i < m_cache_assoc; i++) {
        if (m_cache[cacheSet][i] != nullptr) {
            if (m_cache[cacheSet][i]->m_Address == address) {
                continue;
            }
            candidates.push_back(static_cast<ReplaceableEntry*>(
                                                        m_cache[cacheSet][i]));
        }
    }
    return (candidates.size());
}

// Returns true if there is:
//   a) a tag match on this address or 
//   b) an unused **space** and an entry in the same cache "way"
bool
CacheMemorySASector::cacheAvail(Addr address, int size) const
{
    int already_in_cache = 0;
    auto it = m_size_map.find(address);
    if (it != m_size_map.end()) {
        already_in_cache = it->second;
    }

    // byte capacity in this set exceeded
    int64_t cacheset = addressToCacheSet(address);
    if (m_size_in_set_vec[cacheset] - already_in_cache + size > m_cache_assoc) {
        DPRINTF(RubyCacheSASector, "Cache set [%d] is full as set_in_use(%d)+already_in_cache(%d)+size(%d)>way(%d)\n",
            cacheset, m_size_in_set_vec[cacheset], already_in_cache, size, m_cache_assoc);
        return false;
    }
    return true;
}

bool
CacheMemorySASector::cacheAvail(Addr address) const 
{
    return CacheMemorySASector::cacheAvail(address, m_block_size);
}


bool
CacheMemorySASector::cacheFull() const
{
    if (m_num_bytes_in_use / (m_cache_num_sets * m_cache_assoc) * 100 >= m_full_percentage) {
        return true;
    } 
    // else if (cacheMemoryStats.numTagInUse.value() >= m_cache_num_sets * m_cache_assoc) {
    //     return true;
    // }
    else {
        return false;
    }
}

void 
CacheMemorySASector::updateDataSize(Addr address, int size) {
    int original_size;
    auto it = m_size_map.find(address);
    if (it != m_size_map.end()) {
        original_size = it->second;
        it->second = size;
    } else {
        panic("Address not found in size map");
    }
    
    int64_t set = addressToCacheSet(address);
    DPRINTF(RubyCacheSASector, "update 0x%llx size=%d->%s, this set [%d] remaining %d\n", 
        address, original_size, size, set, m_cache_assoc-m_size_in_set_vec[set]);
    assert(m_num_bytes_in_use - original_size + size <= m_cache_num_sets * m_cache_assoc);
    assert(m_size_in_set_vec[set] - original_size + size <= m_cache_assoc);

    m_num_bytes_in_use -= original_size;
    m_num_bytes_in_use += size;
    cacheMemorySASectorStats.numByteInUse -= original_size;
    cacheMemorySASectorStats.numByteInUse += size;
    m_size_in_set_vec[set] -= original_size;
    m_size_in_set_vec[set] += size;

    DPRINTF(RubyCacheSASector, "updated! entire cache now remaining %dB, this set [%d] now remaining %d\n", 
        m_cache_num_sets * m_cache_assoc - m_num_bytes_in_use, set, m_cache_assoc-m_size_in_set_vec[set]);

    if (original_size > size) {
        cacheMemorySASectorStats.numDataContraction++;
    } else if (original_size < size) {
        cacheMemorySASectorStats.numDataExpansion++;
    }
}

int
CacheMemorySASector::getDataSize(Addr address) const {
    auto it = m_size_map.find(address);
    if (it != m_size_map.end()) {
        return it->second;
    } else {
        panic("Address not found in size map");
    }
}


CacheMemorySASector::
CacheMemorySASectorStats::CacheMemorySASectorStats(statistics::Group *parent)
    : statistics::Group(parent),
      ADD_STAT(numByteInUse, statistics::units::Rate<
                statistics::units::Count, statistics::units::Tick>::get(),
                "Number of bytes in use (average)"),
      ADD_STAT(numDataContraction,"Number of data contractions"),
      ADD_STAT(numDataExpansion,"Number of data expansions"),
      ADD_STAT(util_byte,"byte utilization"), 
      ADD_STAT(compression_ratio_intra,"compression ratio intra"),
      ADD_STAT(numBlockMigrationAcrossSet,"Number of block migration across set")
{
    numByteInUse
        .flags(statistics::nozero | statistics::nonan);
    
    numDataContraction
        .flags(statistics::nozero | statistics::nonan);

    numDataExpansion
        .flags(statistics::nozero | statistics::nonan);

    util_byte
        .flags(statistics::nozero | statistics::nonan);

    compression_ratio_intra
        .flags(statistics::nozero | statistics::nonan);

    numBlockMigrationAcrossSet
        .flags(statistics::nozero | statistics::nonan);
}

}
}