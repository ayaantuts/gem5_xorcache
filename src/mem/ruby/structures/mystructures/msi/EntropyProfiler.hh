#ifndef __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_ENTROPYPROFILER_HH__
#define __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_ENTROPYPROFILER_HH__

#include "base/statistics.hh"
#include "mem/ruby/common/DataBlock.hh"
#include "params/RubyEntropyProfiler.hh"
#include "sim/sim_object.hh"

namespace gem5
{

namespace ruby
{

class EntropyProfiler : public SimObject
{
  public:
    typedef RubyEntropyProfilerParams Params;
    EntropyProfiler(const Params &p);
    ~EntropyProfiler();

    void init();
    void print(std::ostream& out) const;

    void registerData(DataBlock blk);
    void removeData(DataBlock blk);

  protected:
    int m_block_size;
    int m_dedup_fingerprint_size_bits;
    bool m_compute_line_level_entropy;
    int m_xor_folding_scheme;

  private:
      struct EntropyProfilerStats : public statistics::Group
      {
          EntropyProfilerStats(statistics::Group *parent, int hash_bits);
          statistics::AverageVector bitDist;
          statistics::AverageVector byteDist;
          statistics::AverageVector hashLineDist;
          statistics::Average entropy_bit_level;
          statistics::Average entropy_byte_level;
          statistics::Average entropy_line_level_approx;
          statistics::Average hashLineCt;

      } entropyProfilerStats;

      // void updateEntropy(EntropyProfilerStats entropyProfilerStats);
};

std::ostream& operator<<(std::ostream& out, const EntropyProfiler& obj);

} // namespace ruby

} // namespace gem5
#endif