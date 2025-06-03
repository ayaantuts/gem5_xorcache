#include "debug/RubyCacheCounter.hh"
#include "mem/ruby/structures/mystructures/msi/CacheMemoryCounter.hh"
#include "mem/ruby/system/RubySystem.hh"

#include <iostream>

namespace gem5
{

namespace ruby
{

CacheMemoryCounter::CacheMemoryCounter(const Params &p)
    : CacheMemory(p),
    cacheMemoryCounterStats(this)
{
}

void
CacheMemoryCounter::init()
{
    CacheMemory::init();
    std::cout << "Accounting cluster size per centroid from a CacheMemoryCounter! "<< std::endl;
    cacheMemoryCounterStats.m_avg_counter.reset();
}

CacheMemoryCounter::~CacheMemoryCounter()
{
}

AbstractCacheEntry*
CacheMemoryCounter::allocate(Addr address, AbstractCacheEntry* new_entry)
{
    // auto it = m_counter.find(address);
    assert (m_counter.find(address) == m_counter.end()); // counter not existed
    m_counter[address] = 1; //create now
    cacheMemoryCounterStats.m_avg_counter++;
    
    return CacheMemory::allocate(address, new_entry);
}

void
CacheMemoryCounter::deallocate(Addr address)
{
    auto it = m_counter.find(address);
    assert (it != m_counter.end()); // counter should exist
    assert (it->second == 0); // counter should be 0
    m_counter.erase(it); //remove now
    
    CacheMemory::deallocate(address);
}



int 
CacheMemoryCounter::getCounter(Addr address) const
{
    assert(address == makeLineAddress(address));
    auto it = m_counter.find(address);
    if (it != m_counter.end()) {
        return it->second;
    }
    return 0;
}

void
CacheMemoryCounter::incrementCounter(Addr address)
{
    assert(address == makeLineAddress(address));
    auto it = m_counter.find(address);
    assert (it != m_counter.end());
    it->second++;
    cacheMemoryCounterStats.m_avg_counter++;
}

void
CacheMemoryCounter::decrementCounter(Addr address)
{
    assert(address == makeLineAddress(address));
    auto it = m_counter.find(address);
    assert (it != m_counter.end());
    assert(it->second > 0);
    it->second--;
    cacheMemoryCounterStats.m_avg_counter--;
}


CacheMemoryCounter::
CacheMemoryCounterStats::CacheMemoryCounterStats(statistics::Group *parent)
    : statistics::Group(parent),
      ADD_STAT(m_avg_counter, statistics::units::Rate<
                statistics::units::Count, statistics::units::Tick>::get(),
                "counter value (average)")
{

    m_avg_counter
        .flags(statistics::nozero | statistics::nonan);
    
    
}

}
}