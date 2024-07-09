#include "mem/ruby/structures/mystructures/XORer.hh"

#include "base/compiler.hh"
#include "base/intmath.hh"
#include "base/logging.hh"
#include "debug/RubyXORer.hh"
#include "mem/ruby/system/RubySystem.hh"

#include <iostream>

namespace gem5
{

namespace ruby
{

std::ostream&
operator<<(std::ostream& out, const XORer& obj)
{
    obj.print(out);
    out << std::flush;
    return out;
}

XORer::XORer(const Params &p)
    : SimObject(p),
    XORerStats(this)
{
    std::cout << "XOR XORRRR! From a XORer!" << std::endl;
    m_block_size = p.block_size;  // may be 0 at this point. Updated in init()
}

void
XORer::init()
{
    if (m_block_size == 0) {
        m_block_size = RubySystem::getBlockSizeBytes();
    }
}

XORer::~XORer()
{
    
}

void
XORer::print(std::ostream& out) const
{
    out << "XORer dump: " << name() << std::endl;
    
}

XORer::
XORerStats::XORerStats(statistics::Group *parent)
    : statistics::Group(parent)
{

}

} // namespace ruby
} // namespace gem5
