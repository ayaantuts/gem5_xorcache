#include "debug/RubyCacheRegionSector.hh"
#include "mem/ruby/structures/mystructures/msi/CacheMemoryRegionSector.hh"
#include "mem/ruby/system/RubySystem.hh"
#include "base/random.hh"

#include <iostream>

//CacheMemoryRegionSector is adapted from CacheMemoryFASector
// it is partitioned with sector granularity and models fragmentation within regions

namespace gem5
{

namespace ruby
{

CacheMemoryRegionSector::CacheMemoryRegionSector(const Params &p)
    : CacheMemory(p),
    cacheMemoryRegionSectorStats(this)
{
    m_full_percentage = p.full_percentage;
    m_num_regions = p.num_regions;
    gem5::statistics::registerDumpCallback([this]() { calculateStatAtEnd(); });
}

void
CacheMemoryRegionSector::init()
{
    assert(m_cache_assoc == 0); //FA
    assert(m_num_regions >= 1);
    CacheMemory::init();
    m_num_bytes_in_use = 0;
    m_num_bytes_total = m_cache_num_sets * m_cache_assoc;
    cacheMemoryRegionSectorStats.numByteTotal = m_num_bytes_total;
    assert(m_num_regions <= m_num_bytes_total/8);
    std::cout << "Hello World! From a CacheMemoryRegionSector! num_regions=" << m_num_regions << ", numbytestotal=" 
    << m_num_bytes_total << std::endl;
    m_numbyteinuse_per_region.resize(m_num_regions, 0);
}

CacheMemoryRegionSector::~CacheMemoryRegionSector()
{
    m_size_map.clear();
    m_region_map.clear();
    m_numbyteinuse_per_region.clear();
}


void
CacheMemoryRegionSector::calculateStatAtEnd()
{
    cacheMemoryRegionSectorStats.util_byte = (float) cacheMemoryRegionSectorStats.numByteInUse.value() / (m_num_bytes_total) * 100;
    cacheMemoryRegionSectorStats.compression_ratio_intra = (float) 64 / ((float) cacheMemoryRegionSectorStats.numByteInUse.value() / (float) cacheMemoryStats.numTagInUse.value());
}

// rewriting the allocation function
AbstractCacheEntry*
CacheMemoryRegionSector::allocate(Addr address, AbstractCacheEntry *entry)
{
    return CacheMemoryRegionSector::allocate(address, entry, m_block_size);
}

AbstractCacheEntry*
CacheMemoryRegionSector::allocate(Addr address, AbstractCacheEntry *entry, int size)
{
    DPRINTF(RubyCacheRegionSector, "alloc 0x%llx size=%d\n", address, size);
    m_num_bytes_in_use += size;
    assert(m_num_bytes_in_use <= m_num_bytes_total);
    cacheMemoryRegionSectorStats.numByteInUse += size;
    m_size_map[address] = size;
    
    while (true) {
        int rand_region = random_mt.random<int>(0, m_num_regions - 1);
        if (m_numbyteinuse_per_region[rand_region] + size <= m_num_bytes_total / m_num_regions) {
            m_numbyteinuse_per_region[rand_region] += size;
            m_region_map[address] = rand_region;
            break;
        }
    }
    return CacheMemory::allocate(address, entry);
}

// rewriting the deallocation function
void
CacheMemoryRegionSector::deallocate(Addr address)
{
    int size;
    auto it = m_size_map.find(address);
    if (it != m_size_map.end()) {
        size = it->second;
    } else {
        panic("Address not found in size map");
    }

    auto it2 = m_region_map.find(address);
    if (it2 != m_region_map.end()) {
        m_numbyteinuse_per_region[it2->second] -= size;
        m_region_map.erase(address);
    } else {
        panic("Address not found in region map");
    }

    DPRINTF(RubyCacheRegionSector, "dealloc 0x%llx size=%d\n", address, size);
    
    cacheMemoryRegionSectorStats.numDataEviction++;
    m_num_bytes_in_use -= size;
    assert(m_num_bytes_in_use >= 0);
    cacheMemoryRegionSectorStats.numByteInUse -= size;
    CacheMemory::deallocate(address);
    m_size_map.erase(address);
}

void
CacheMemoryRegionSector::changeAddr(Addr original_addr, Addr new_addr)
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
    m_region_map[new_addr] = m_region_map[original_addr];
    m_region_map.erase(original_addr);

    assert(lookup(original_addr) == nullptr && lookup(new_addr) != nullptr);

    DPRINTF(RubyCacheRegionSector, "change 0x%llx to 0x%llx, size=%d\n", 
        original_addr, new_addr, m_size_map[new_addr]);
}


// rewriting the cacheProbe function
Addr
CacheMemoryRegionSector::candidateProbe(Addr address) const
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
CacheMemoryRegionSector::candidateCount(Addr address) const
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
CacheMemoryRegionSector::cacheAvail(Addr address, int size) const
{
    int already_in_cache = 0;
    auto it = m_size_map.find(address);
    if (it != m_size_map.end()) {
        already_in_cache = it->second;
    }

    DPRINTF(RubyCacheRegionSector, "already_in_cache bytes=%d\n",already_in_cache);
    // byte capacity exceeded
    if (m_num_bytes_in_use - already_in_cache + size > m_num_bytes_total) {
        DPRINTF(RubyCacheRegionSector, "Cache is full as m_num_bytes_in_use(%d)+already_in_cache(%d)>set(%d)*way(%d)\n",
            m_num_bytes_in_use, already_in_cache, m_cache_num_sets, m_cache_assoc);
        return false;
    }

    auto it2 = m_region_map.find(address);
    int current_region;
    if (it2 != m_region_map.end()) {
        current_region = it2->second;
    } else {
        current_region = -1;
    }

    for (int i = 0; i < m_num_regions; i++) {
        if (i == current_region) {
            if (m_numbyteinuse_per_region[i] - already_in_cache + size <= m_num_bytes_total / m_num_regions) {
                return true;
            }
        } else {
            if (m_numbyteinuse_per_region[i] + size <= m_num_bytes_total / m_num_regions) {
                return true;
            }
        }
    }
    return false;
}

bool
CacheMemoryRegionSector::cacheAvail(Addr address) const 
{
    return cacheAvail(address, m_block_size);
}


bool
CacheMemoryRegionSector::cacheFull() const
{
    if (m_num_bytes_in_use / (m_num_bytes_total) * 100 >= m_full_percentage) {
        return true;
    }
    else {
        return false;
    }
}

void 
CacheMemoryRegionSector::updateDataSize(Addr address, int size) {
    int original_size;

    auto it = m_size_map.find(address);
    if (it != m_size_map.end()) {
        original_size = it->second;
        it->second = size;
    } else {
        panic("Address not found in size map");
    }
    assert(m_num_bytes_in_use - original_size + size <= m_num_bytes_total);
    
    if (size == original_size) {
        return;
    }

    // get current region
    int region;
    auto it2 = m_region_map.find(address);
    if (it2 != m_region_map.end()) {
        region = it2->second;
    } else {
        panic("Address not found in region map");
    }

    // if current region can accommodate the new size, simply update the size
    if (m_numbyteinuse_per_region[region] - original_size + size <= m_num_bytes_total / m_num_regions) {
        m_numbyteinuse_per_region[region] -= original_size;
        m_numbyteinuse_per_region[region] += size;
    } 
    // else, find a new region that can accommodate the new size
    else {
        while (true) {
            int rand_region = random_mt.random<int>(0, m_num_regions - 1);
            if (m_numbyteinuse_per_region[rand_region] + size <= m_num_bytes_total / m_num_regions) {
                m_numbyteinuse_per_region[region] -= original_size;
                m_numbyteinuse_per_region[rand_region] += size;
                m_region_map[address] = rand_region;
                break;
            }
        }
    }

    m_num_bytes_in_use -= original_size;
    m_num_bytes_in_use += size;
    assert(m_num_bytes_in_use <= m_num_bytes_total);
    
    cacheMemoryRegionSectorStats.numByteInUse -= original_size;
    cacheMemoryRegionSectorStats.numByteInUse += size;

    DPRINTF(RubyCacheRegionSector, "update 0x%llx size=%d->%s, now remaining %d B\n", 
        address, original_size, size, m_num_bytes_total - m_num_bytes_in_use);

    if (original_size > size) {
        cacheMemoryRegionSectorStats.numDataContraction++;
    } else if (original_size < size) {
        cacheMemoryRegionSectorStats.numDataExpansion++;
    }
}

int
CacheMemoryRegionSector::getDataSize(Addr address) const {
    auto it = m_size_map.find(address);
    if (it != m_size_map.end()) {
        return it->second;
    } else {
        panic("Address not found in size map");
    }
}


CacheMemoryRegionSector::
CacheMemoryRegionSectorStats::CacheMemoryRegionSectorStats(statistics::Group *parent)
    : statistics::Group(parent),
      ADD_STAT(numByteInUse, statistics::units::Rate<
                statistics::units::Count, statistics::units::Tick>::get(),
                "Number of bytes in use (average)"),
      ADD_STAT(numDataEviction,"Number of data evictions"),
      ADD_STAT(numDataContraction,"Number of data contractions"),
      ADD_STAT(numDataExpansion,"Number of data expansions"),
      ADD_STAT(util_byte,"byte utilization"), 
      ADD_STAT(compression_ratio_intra,"compression ratio intra"),
      ADD_STAT(numByteTotal, statistics::units::Count::get(), "Total number of bytes")
{
    numByteInUse
        .flags(statistics::nozero | statistics::nonan);
    
    numDataEviction
        .flags(statistics::nozero | statistics::nonan);
    
    numDataContraction
        .flags(statistics::nozero | statistics::nonan);

    numDataExpansion
        .flags(statistics::nozero | statistics::nonan);

    util_byte
        .flags(statistics::nozero | statistics::nonan);

    compression_ratio_intra
        .flags(statistics::nozero | statistics::nonan);
    
    numByteTotal
        .flags(statistics::nozero | statistics::nonan);
}

}
}