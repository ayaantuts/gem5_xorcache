#ifndef __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_CACHEMEMORYDUALADDR_HH__
#define __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_CACHEMEMORYDUALADDR_HH__

#include "params/RubyCacheDualAddr.hh"
#include "mem/ruby/structures/CacheMemory.hh"

namespace gem5
{

namespace ruby
{

class CacheMemoryDualAddr : public CacheMemory
{
  public:
    typedef RubyCacheDualAddrParams Params;
    CacheMemoryDualAddr(const Params &p);
    ~CacheMemoryDualAddr();

    void init() override;

    void pair(Addr addr1, Addr addr2);
    void unpair(Addr addr);
    bool isSecondaryAddr(Addr addr); // returns true if addr is primary addr
    AbstractCacheEntry* lookup(Addr address); // addressable by both m_Addr and m_Addr2
    Addr getPrimaryAddr(Addr addr); // returns primary addr of addr
    bool hasSecondaryAddr(Addr addr); // returns true if addr has secondary addr
    Addr getSecondaryAddr(Addr addr); // returns secondary addr of addr

  protected:
    std::unordered_map<Addr, AbstractCacheEntry*> m_map_addr2entry; // maps secondary addr to entry
    
  protected:
      struct CacheMemoryDualAddrStats : public statistics::Group
      {
          CacheMemoryDualAddrStats(statistics::Group *parent);
          statistics::Scalar numPair;
          statistics::Scalar numUnpair;

      } cacheMemoryDualAddrStats;
};

} // namespace ruby

} // namespace gem5
#endif