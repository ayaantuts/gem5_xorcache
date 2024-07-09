#include "mem/ruby/structures/mystructures/AbstractDataEntry.hh"

namespace gem5
{

namespace ruby
{

AbstractDataEntry::AbstractDataEntry()
    : AbstractCacheEntry()
{
    std::cout << "Hello World! From a AbstractDataEntry!" << std::endl;
}


AbstractDataEntry::~AbstractDataEntry()
{
    
}

void
AbstractDataEntry::setPosition(const uint32_t set, const uint32_t way, const uint32_t seg)
{
    _set = set;
    _way = way;
    _seg = seg;
}

}
}