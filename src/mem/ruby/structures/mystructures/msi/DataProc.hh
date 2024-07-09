#ifndef __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_DATAPROC_HH__
#define __MEM_RUBY_STRUCTURES_MYSTRUCTURES_MSI_DATAPROC_HH__

#include "base/statistics.hh"
#include "params/RubyDataProc.hh"
#include "mem/ruby/common/DataBlock.hh"
#include "sim/sim_object.hh"
#include "enums/Preproc.hh"
#include "enums/Compress.hh"

namespace gem5
{

namespace ruby
{

class DataProc : public SimObject
{
  public:
    typedef RubyDataProcParams Params;
    DataProc(const Params &p);
    ~DataProc();

    void init();
    void print(std::ostream& out) const;

    // =========== Compression ===========
    int compress(DataBlock blk);
    int compress(DataBlock blk, DataBlock ref);
    int peek_compress(DataBlock blk);
    int peek_compress(DataBlock blk, DataBlock ref);
    int peek_compress_intra_bdi(DataBlock blk);
    int peek_compress_intra(DataBlock blk);
    int peek_compress_inter(DataBlock blk, DataBlock ref=DataBlock());
    Cycles decompress();
    int get_min_achieveable_size()const;

    bool is_compressible_zero(DataBlock blk) const;
    bool is_compressible_repeatByte(DataBlock blk) const;
    template<typename T> bool int_fall_into_range(T int_num, int test_bit_width) const;
    template<typename T> bool is_compressible_bdi(DataBlock blk, int base_size, int delta_size) const;

    // =========== Preprocessing ===========
    DataBlock preprocess(DataBlock blk1, DataBlock blk2);
    DataBlock peek_preproc(DataBlock blk1, DataBlock blk2);
    void profilePreproc(DataBlock preprocResult);
    Cycles reverse_proc();

    enums::Preproc get_preproc()const {return m_preproc;}
    enums::Compress get_compress()const {return m_compress;}
    bool has_compression_scheme()const {return m_compress != enums::Compress::no_compress;}
    bool has_preproc_scheme()const {return m_preproc != enums::Preproc::no_preproc;}
    bool do_xor()const {return m_preproc == enums::Preproc::xor_preproc;}

  protected:
    const enums::Preproc m_preproc;
    const enums::Compress m_compress;

    Cycles m_compress_latency;
    Cycles m_decompress_latency;
    Cycles m_preproc_latency;
    Cycles m_rev_preproc_latency;
    int m_block_size;
    int m_segment_size_in_byte;

  private:
      struct DataProcStats : public statistics::Group
      {
          DataProcStats(statistics::Group *parent);

          statistics::Scalar numCompressionIntra;
          statistics::Scalar numCompressionInter;
          statistics::Scalar numCompIntraSuccess;
          statistics::Scalar numCompInterSuccess;
          statistics::Scalar numDecomp;
          statistics::Scalar numReverseProc;
          statistics::Histogram compSizeinByte;
          statistics::Histogram compSizeinByteReal;
          statistics::Scalar numPreproc;
          statistics::Scalar numRevPreproc;
      } dataProcStats;
};

std::ostream& operator<<(std::ostream& out, const DataProc& obj);

} // namespace ruby

} // namespace gem5
#endif