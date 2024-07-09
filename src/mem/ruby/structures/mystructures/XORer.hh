#ifndef __MEM_RUBY_STRUCTURES_MYSTRUCTURES_XORER_HH__
#define __MEM_RUBY_STRUCTURES_MYSTRUCTURES_XORER_HH__

#include "base/statistics.hh"
#include "params/RubyXORer.hh"
#include "mem/ruby/common/DataBlock.hh"
#include "sim/sim_object.hh"

namespace gem5
{

namespace ruby
{

class XORer : public SimObject
{
  public:
    typedef RubyXORerParams Params;
    XORer(const Params &p);
    ~XORer();

    void init();
    void print(std::ostream& out) const;
    
  private:
      struct XORerStats : public statistics::Group
      {
          XORerStats(statistics::Group *parent);
      } XORerStats;

  private:
    int m_block_size;
};

std::ostream& operator<<(std::ostream& out, const XORer& obj);

} // namespace ruby

} // namespace gem5
#endif