#ifndef __MEM_RUBY_STRUCTURES_MYSTRUCTURES_HASHTABLEENTRY_HH__
#define __MEM_RUBY_STRUCTURES_MYSTRUCTURES_HASHTABLEENTRY_HH__

#include <iostream>

#include "base/logging.hh"
#include "mem/cache/replacement_policies/replaceable_entry.hh"
#include "mem/ruby/common/Address.hh"
#include "mem/ruby/common/DataBlock.hh"
#include "mem/ruby/protocol/AccessPermission.hh"

namespace gem5
{

namespace ruby
{

class HashTableEntry : public ReplaceableEntry
{
  private:
    // The last access tick for the cache entry.
    Tick m_last_touch_tick;

  public:
    HashTableEntry();
    ~HashTableEntry() = default;

    
    std::string
    print() const override
    {
        return ReplaceableEntry::print();
    }

    uint32_t m_partial_hash;
    int m_dataSet;

    // Get the last access Tick.
    Tick getLastAccess() { return m_last_touch_tick; }

    // Set the last access Tick.
    void setLastAccess(Tick tick) { m_last_touch_tick = tick; }

    virtual void invalidateEntry() {}

};

} // namespace ruby
} // namespace gem5

#endif // __MEM_RUBY_STRUCTURES_MYSTRUCTURES_HASHTABLEENTRY_HH__
