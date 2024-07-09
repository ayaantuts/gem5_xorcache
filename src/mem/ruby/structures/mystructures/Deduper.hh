#ifndef __MEM_RUBY_STRUCTURES_MYSTRUCTURES_DEDUPER_HH__
#define __MEM_RUBY_STRUCTURES_MYSTRUCTURES_DEDUPER_HH__

#include "base/statistics.hh"
#include "params/RubyDeduper.hh"
#include "mem/ruby/common/DataBlock.hh"
#include "sim/sim_object.hh"

namespace gem5
{

namespace ruby
{

class Deduper : public SimObject
{
  public:
    typedef RubyDeduperParams Params;
    Deduper(const Params &p);
    ~Deduper();

    void init();
    void print(std::ostream& out) const;
    int compress(DataBlock blk);
    int peek_compress(DataBlock blk);
    Cycles decompress();
    uint32_t hash(DataBlock blk);
    uint32_t peek_hash(DataBlock blk);
    // uint16_t hash(DataBlock blk);
    bool isDataMatch(DataBlock blk1, DataBlock blk2);
    
  private:
      struct DeduperStats : public statistics::Group
      {
          DeduperStats(statistics::Group *parent);

          statistics::Scalar numHash;
          statistics::Scalar numCompression;
          statistics::Scalar numCompSuccess;
          statistics::Scalar numDecomp;
      } deduperStats;

  private:
    Cycles m_compress_latency;
    Cycles m_decompress_latency;
    int m_block_size;
};

std::ostream& operator<<(std::ostream& out, const Deduper& obj);

} // namespace ruby

} // namespace gem5
#endif