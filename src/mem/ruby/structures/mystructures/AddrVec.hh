#ifndef __MEM_RUBY_STRUCTURES_MYSTRUCTURES_ADDRVEC_HH__
#define __MEM_RUBY_STRUCTURES_MYSTRUCTURES_ADDRVEC_HH__

#include <ostream>
#include <vector>
#include "base/types.hh"

namespace gem5
{

namespace ruby
{

typedef std::vector<Addr> AddrVec;

std::ostream& operator<<(std::ostream& os, const std::vector<Addr>& myvector);

} // namespace ruby
} // namespace gem5

#endif //__MEM_RUBY_COMMON_BOOLVEC_HH__
