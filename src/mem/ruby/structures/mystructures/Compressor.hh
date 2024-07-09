#ifndef __MEM_RUBY_STRUCTURES_MYSTRUCTURES_COMPRESSOR_HH__
#define __MEM_RUBY_STRUCTURES_MYSTRUCTURES_COMPRESSOR_HH__

#include "base/statistics.hh"
#include "params/RubyCompressor.hh"
#include "mem/ruby/common/DataBlock.hh"
#include "sim/sim_object.hh"

namespace gem5
{

namespace ruby
{

class Compressor : public SimObject
{
  public:
    typedef RubyCompressorParams Params;
    Compressor(const Params &p);
    ~Compressor();

    void init();
    void print(std::ostream& out) const;
    int compress(DataBlock blk);
    int peek_compress(DataBlock blk);
    Cycles decompress();
    int get_min_achieveable_size()const;

    bool is_compressible_zero(DataBlock blk) const;
    bool is_compressible_repeatByte(DataBlock blk) const;
    template<typename T> bool int_fall_into_range(T int_num, int test_bit_width) const;
    template<typename T> bool is_compressible_bdi(DataBlock blk, int base_size, int delta_size) const;

    
  private:
      struct CompressorStats : public statistics::Group
      {
          CompressorStats(statistics::Group *parent);

          statistics::Scalar numCompression;
          statistics::Scalar numCompSuccess;
          statistics::Scalar numDecomp;
          statistics::Histogram compSizeinByte;
      } compressorStats;

  private:
    Cycles m_compress_latency;
    Cycles m_decompress_latency;
    int m_block_size;
};

std::ostream& operator<<(std::ostream& out, const Compressor& obj);

} // namespace ruby

} // namespace gem5
#endif