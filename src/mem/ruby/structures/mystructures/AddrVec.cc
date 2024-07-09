#include "mem/ruby/structures/mystructures/AddrVec.hh"

#include <iostream>
#include <vector>

namespace gem5
{

namespace ruby
{

std::ostream& operator<<(std::ostream& os, const AddrVec& myvector) {
    for (const Addr e: myvector) {
        os << "[" << std::hex << "0x" << e << std::dec << "]";
    }
    return os;
}

} // namespace ruby
} // namespace gem5
