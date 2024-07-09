#ifndef __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_LSHCOMPUTER_HH__
#define __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_LSHCOMPUTER_HH__

#include "base/statistics.hh"
#include "params/RubyLSHComputer.hh"
#include "mem/ruby/common/DataBlock.hh"
#include "sim/sim_object.hh"
// #include "enums/Compress.hh"
#include <queue>
namespace gem5
{

namespace ruby
{

class LSHComputer : public SimObject
{
  public:
    typedef RubyLSHComputerParams Params;
    LSHComputer(const Params &p);
    ~LSHComputer();

    void init();
    void print(std::ostream& out) const;
    int getNumberOfBins() const;
    uint64_t peek_compute(DataBlock blk) const;
    uint64_t compute(DataBlock blk);
    Addr castToAddr(uint64_t fingerprint) const;
    Addr computeLSHBaseTableAddr(DataBlock blk) const;

  protected:
    int m_block_size;
    void gen_lsh_matrix();

  private:
    int m_fingerprint_bits;
    std::vector<int *> m_lsh_matrix;
    Addr m_basetable_start_addr;

    struct LSHComputerStats : public statistics::Group
    {
        LSHComputerStats(statistics::Group *parent, int numBins);
        statistics::Scalar numComp;
        statistics::Vector binLSH;
        
    } lshComputerStats;
};

std::ostream& operator<<(std::ostream& out, const LSHComputer& obj);

} // namespace ruby

} // namespace gem5
#endif