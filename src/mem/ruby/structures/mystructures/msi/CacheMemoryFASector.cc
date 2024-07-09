#include "debug/RubyCacheFASector.hh"
#include "mem/ruby/structures/mystructures/msi/CacheMemoryFASector.hh"
#include "mem/ruby/system/RubySystem.hh"

#include <iostream>

//CacheMemoryFASector is fully associative cache with sector granularity

namespace gem5
{

namespace ruby
{

CacheMemoryFASector::CacheMemoryFASector(const Params &p)
    : CacheMemory(p),
    cacheMemoryFASectorStats(this)
{
    m_full_percentage = p.full_percentage;
    gem5::statistics::registerDumpCallback([this]() { calculateStatAtEnd(); });
}

void
CacheMemoryFASector::init()
{
    assert(m_cache_assoc == 0); //FA
    CacheMemory::init();
    m_num_bytes_in_use = 0;
    std::cout << "Hello World! From a CacheMemoryFASector! "<< std::endl;
}

CacheMemoryFASector::~CacheMemoryFASector()
{
    m_size_map.clear();
}


void
CacheMemoryFASector::calculateStatAtEnd()
{
    cacheMemoryFASectorStats.util_byte = (float) cacheMemoryFASectorStats.numByteInUse.value() / (m_cache_num_sets * m_cache_assoc) * 100;
    cacheMemoryFASectorStats.compression_ratio_intra = (float) 64 / ((float) cacheMemoryFASectorStats.numByteInUse.value() / (float) cacheMemoryStats.numTagInUse.value());
}

// rewriting the allocation function
AbstractCacheEntry*
CacheMemoryFASector::allocate(Addr address, AbstractCacheEntry *entry)
{
    m_num_bytes_in_use += m_block_size;
    assert(m_num_bytes_in_use <= m_cache_num_sets * m_cache_assoc);
    cacheMemoryFASectorStats.numByteInUse += m_block_size;
    m_size_map[address] = m_block_size;
    return CacheMemory::allocate(address, entry);
}

AbstractCacheEntry*
CacheMemoryFASector::allocate(Addr address, AbstractCacheEntry *entry, int size)
{
    DPRINTF(RubyCacheFASector, "alloc 0x%llx size=%d\n", address, size);
    m_num_bytes_in_use += size;
    assert(m_num_bytes_in_use <= m_cache_num_sets * m_cache_assoc);
    cacheMemoryFASectorStats.numByteInUse += size;
    m_size_map[address] = size;
    return CacheMemory::allocate(address, entry);
}

// rewriting the deallocation function
void
CacheMemoryFASector::deallocate(Addr address)
{
    int size;
    auto it = m_size_map.find(address);
    if (it != m_size_map.end()) {
        size = it->second;
    } else {
        panic("Address not found in size map");
    }

    DPRINTF(RubyCacheFASector, "dealloc 0x%llx size=%d\n", address, size);

    m_num_bytes_in_use -= size;
    assert(m_num_bytes_in_use >= 0);
    cacheMemoryFASectorStats.numByteInUse -= size;
    CacheMemory::deallocate(address);
    m_size_map.erase(address);
}

void
CacheMemoryFASector::changeAddr(Addr original_addr, Addr new_addr)
{
    // get the original entry
    AbstractCacheEntry* original_entry = lookup(original_addr);
    assert(original_entry != nullptr);
    // modify addr (FA address change does not really impact mapping)
    original_entry->m_Address = new_addr;

    m_tag_index[new_addr] = m_tag_index[original_addr];
    m_tag_index.erase(original_addr);
    m_size_map[new_addr] = m_size_map[original_addr];
    m_size_map.erase(original_addr);

    assert(lookup(original_addr) == nullptr && lookup(new_addr) != nullptr);

    DPRINTF(RubyCacheFASector, "change 0x%llx to 0x%llx, size=%d\n", 
        original_addr, new_addr, m_size_map[new_addr]);
}


// rewriting the cacheProbe function
Addr
CacheMemoryFASector::candidateProbe(Addr address) const
{
    assert(address == makeLineAddress(address));
    // assert(!cacheAvail(address)); // we are using this function to probe 
    // the xor candidate so we dont need this check

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
    assert(candidates.size() > 0);
    return m_cache[cacheSet][m_replacementPolicy_ptr->
                        getVictim(candidates)->getWay()]->m_Address;
}

int
CacheMemoryFASector::candidateCount(Addr address) const
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
//   a) a tag match on this address or there is
//   b) an unused **space** and an entry in the same cache "way"
bool
CacheMemoryFASector::cacheAvail(Addr address, int size) const
{
    int already_in_cache = 0;
    auto it = m_size_map.find(address);
    if (it != m_size_map.end()) {
        already_in_cache = it->second;
    }

    DPRINTF(RubyCacheFASector, "already_in_cache=%d\n",already_in_cache);
    // byte capacity exceeded
    if (m_num_bytes_in_use - already_in_cache + size > m_cache_num_sets * m_cache_assoc) {
        DPRINTF(RubyCacheFASector, "Cache is full as m_num_bytes_in_use(%d)+already_in_cache(%d)>set(%d)*way(%d)\n",
            m_num_bytes_in_use, already_in_cache, m_cache_num_sets, m_cache_assoc);
        return false;
    }
    // if (cacheMemoryStats.numTagInUse.value() >= m_cache_num_sets * m_cache_assoc / m_block_size) {
    //     DPRINTF(RubyCacheFASector, "Cache is full as numTagInUse(%d)>numBlock(%d)\n",
    //         cacheMemoryStats.numTagInUse.value(), m_cache_num_sets * m_cache_assoc / m_block_size);
    //     return false;
    // }
    return true;

    // assert(address == makeLineAddress(address));

    // int64_t cacheSet = addressToCacheSet(address);

    // for (int i = 0; i < m_cache_assoc; i++) {
    //     AbstractCacheEntry* entry = m_cache[cacheSet][i];
    //     if (entry != NULL) {
    //         if (entry->m_Address == address ||
    //             entry->m_Permission == AccessPermission_NotPresent) {
    //             // Already in the cache or we found an empty entry
    //             return true;
    //         }
    //     } else {
    //         return true;
    //     }
    // }
    // return false;
}

bool
CacheMemoryFASector::cacheAvail(Addr address) const 
{
    return cacheAvail(address, m_block_size);
}


bool
CacheMemoryFASector::cacheFull() const
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
CacheMemoryFASector::updateDataSize(Addr address, int size) {
    int original_size;
    auto it = m_size_map.find(address);
    if (it != m_size_map.end()) {
        original_size = it->second;
        it->second = size;
    } else {
        panic("Address not found in size map");
    }
    assert(m_num_bytes_in_use - original_size + size <= m_cache_num_sets * m_cache_assoc);

    m_num_bytes_in_use -= original_size;
    m_num_bytes_in_use += size;
    assert(m_num_bytes_in_use <= m_cache_num_sets * m_cache_assoc);
    
    cacheMemoryFASectorStats.numByteInUse -= original_size;
    cacheMemoryFASectorStats.numByteInUse += size;

    DPRINTF(RubyCacheFASector, "update 0x%llx size=%d->%s, now remaining %d B\n", 
        address, original_size, size, m_cache_num_sets * m_cache_assoc - m_num_bytes_in_use);

    if (original_size > size) {
        cacheMemoryFASectorStats.numDataContraction++;
    } else if (original_size < size) {
        cacheMemoryFASectorStats.numDataExpansion++;
    }
}

int
CacheMemoryFASector::getDataSize(Addr address) const {
    auto it = m_size_map.find(address);
    if (it != m_size_map.end()) {
        return it->second;
    } else {
        panic("Address not found in size map");
    }
}


CacheMemoryFASector::
CacheMemoryFASectorStats::CacheMemoryFASectorStats(statistics::Group *parent)
    : statistics::Group(parent),
      ADD_STAT(numByteInUse, statistics::units::Rate<
                statistics::units::Count, statistics::units::Tick>::get(),
                "Number of bytes in use (average)"),
      ADD_STAT(numDataContraction,"Number of data contractions"),
      ADD_STAT(numDataExpansion,"Number of data expansions"),
      ADD_STAT(util_byte,"byte utilization"), 
      ADD_STAT(compression_ratio_intra,"compression ratio intra")
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
}

}
}