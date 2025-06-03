#ifndef __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_CACHEMEMORYCOUNTER_HH__
#define __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_CACHEMEMORYCOUNTER_HH__

#include "params/RubyCacheCounter.hh"
#include "mem/ruby/structures/CacheMemory.hh"

namespace gem5
{

namespace ruby
{

class CacheMemoryCounter : public CacheMemory
{
  public:
    typedef RubyCacheCounterParams Params;
    CacheMemoryCounter(const Params &p);
    ~CacheMemoryCounter();

    void init() override;

    AbstractCacheEntry* allocate(Addr address, AbstractCacheEntry* new_entry); // increment counter to 1
    void deallocate(Addr address); // remove counter when equal to 0; if (getcounter == 0) deallocate
    
    int getCounter(Addr address) const; // return the counter value of the address
    void incrementCounter(Addr address); // increment counter by 1
    void decrementCounter(Addr address); // decrement counter by 1
    
    

  protected:
    std::unordered_map<Addr, int> m_counter; // couner value as extension to cachememory

    struct CacheMemoryCounterStats : public statistics::Group
    {
        CacheMemoryCounterStats(statistics::Group *parent);
        statistics::Average m_avg_counter;

    } cacheMemoryCounterStats;
};

} // namespace ruby

} // namespace gem5
#endif