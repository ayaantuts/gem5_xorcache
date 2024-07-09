#include "debug/RubyCacheDualAddr.hh"
#include "debug/RubyCacheUtil.hh"
#include "mem/ruby/structures/mystructures/msi/CacheMemoryDualAddr.hh"
#include "mem/ruby/system/RubySystem.hh"

#include <iostream>

namespace gem5
{

namespace ruby
{

CacheMemoryDualAddr::CacheMemoryDualAddr(const Params &p)
    : CacheMemory(p),
    cacheMemoryDualAddrStats(this)
{
    
}

void
CacheMemoryDualAddr::init()
{
    CacheMemory::init();
    assert(m_cache_num_sets == 1); // has to be fully associative
    std::cout << "Hello World! From a CacheMemoryDualAddr! "<< std::endl;
}

CacheMemoryDualAddr::~CacheMemoryDualAddr()
{
    m_map_addr2entry.clear();
}

// looks an address up in the cache
AbstractCacheEntry*
CacheMemoryDualAddr::lookup(Addr address)
{   
    AbstractCacheEntry* entry = CacheMemory::lookup(address);
    if (entry != NULL) return entry;
    
    // search in m_map_addr2entry
    auto it = m_map_addr2entry.find(address);
    if (it != m_map_addr2entry.end()) {
        return it->second;
    } else {
        return NULL;
    }
}

void 
CacheMemoryDualAddr::pair(Addr addr1, Addr addr2)
{
    AbstractCacheEntry* entry = CacheMemory::lookup(addr1);
    assert(entry != NULL);
    m_map_addr2entry[addr2] = entry;
    cacheMemoryDualAddrStats.numPair++;
    DPRINTF(RubyCacheDualAddr, "pairing 0x%llx with 0x%llx\n", addr1, addr2);
}

// addr could be either primary or secondary addr
void 
CacheMemoryDualAddr::unpair(Addr addr)
{
    cacheMemoryDualAddrStats.numUnpair++;
    
    auto it = m_map_addr2entry.find(addr);
    if (it != m_map_addr2entry.end()) {
        // addr is secondary
        m_map_addr2entry.erase(it); 
        DPRINTF(RubyCacheDualAddr, "unpairing 0x%llx with 0x%llx\n", it->second->m_Address, addr);
        return;
    }
    else {
        // addr is primary
        AbstractCacheEntry* entry = CacheMemory::lookup(addr);
        assert(entry != NULL);
        // search match in m_map_addr2entry
        for (auto it = m_map_addr2entry.begin(); it != m_map_addr2entry.end(); it++) {
            if (it->second == entry) {
                m_map_addr2entry.erase(it);
                DPRINTF(RubyCacheDualAddr, "unpairing 0x%llx with 0x%llx\n", addr, it->first);
                return;
            }
        }
        panic("unpair: addr is neither primary nor secondary addr");
    }
}

bool 
CacheMemoryDualAddr::isSecondaryAddr(Addr addr)
{
    // search in m_map_addr2entry
    auto it = m_map_addr2entry.find(addr);
    if (it != m_map_addr2entry.end()) {
        return true; //in the map => secondary
    } else {
        return false;
    }
}

Addr 
CacheMemoryDualAddr::getPrimaryAddr(Addr addr)
{
    if (!isSecondaryAddr(addr)) return addr;
    else {
        auto it = m_map_addr2entry.find(addr);
        assert (it != m_map_addr2entry.end());
        return it->second->m_Address;
    }
}

bool 
CacheMemoryDualAddr::hasSecondaryAddr(Addr addr)
{   
    assert(CacheMemoryDualAddr::lookup(addr) != NULL);
    if (isSecondaryAddr(addr)) {
        return true; // this is already secondary addr
    }
    else {
        // this is primary addr
        AbstractCacheEntry* entry = CacheMemory::lookup(addr);
        assert(entry != NULL);
        // search match in m_map_addr2entry
        for (auto it = m_map_addr2entry.begin(); it != m_map_addr2entry.end(); it++) {
            if (it->second == entry) {
                return true;;
            }
        }
        return false; // not present in cache
    }
}

Addr 
CacheMemoryDualAddr::getSecondaryAddr(Addr addr)
{   
    assert(CacheMemoryDualAddr::lookup(addr) != NULL);
    if (isSecondaryAddr(addr)) {
        return addr; // this is already secondary addr
    }
    else {
        // this is primary addr
        AbstractCacheEntry* entry = CacheMemory::lookup(addr);
        assert(entry != NULL);
        // search match in m_map_addr2entry
        for (auto it = m_map_addr2entry.begin(); it != m_map_addr2entry.end(); it++) {
            if (it->second == entry) {
                return it->first;
            }
        }
        assert(false); // not present in cache
        return addr;
    }
}

CacheMemoryDualAddr::
CacheMemoryDualAddrStats::CacheMemoryDualAddrStats(statistics::Group *parent)
    : statistics::Group(parent),
      ADD_STAT(numPair, "Number of pair"),
      ADD_STAT(numUnpair, "Number of unpair")
{
    numPair
        .flags(statistics::nozero);
    numUnpair
        .flags(statistics::nozero);
    
}

}
}