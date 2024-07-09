#ifndef __MEM_RUBY_STRUCTURES_MYSTRUCTURES_ABSTRACTDATAENTRY_HH__
#define __MEM_RUBY_STRUCTURES_MYSTRUCTURES_ABSTRACTDATAENTRY_HH__

#include "mem/ruby/slicc_interface/AbstractCacheEntry.hh"

namespace gem5
{

namespace ruby
{

class AbstractDataEntry : public AbstractCacheEntry
{
  public:
    AbstractDataEntry();
    virtual ~AbstractDataEntry() = 0;

    void setPosition(const uint32_t set, const uint32_t way, const uint32_t seg);

  protected:
    uint32_t _seg;
  

};

} // namespace ruby

} // namespace gem5
#endif