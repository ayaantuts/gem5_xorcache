#include "mem/ruby/structures/mystructures/msi/EntropyProfiler.hh"

#include "base/compiler.hh"
#include "base/intmath.hh"
#include "base/logging.hh"
#include "debug/RubyEntropyProfiler.hh"
#include "mem/ruby/system/RubySystem.hh"

#include <bits/stdc++.h>
#include <iostream>

namespace gem5
{

namespace ruby
{

std::ostream&
operator<<(std::ostream& out, const EntropyProfiler& obj)
{
    obj.print(out);
    out << std::flush;
    return out;
}

EntropyProfiler::EntropyProfiler(const Params &p)
    : SimObject(p),
    entropyProfilerStats(this, p.dedup_fingerprint_size_bits)
{
    // std::cout << "0 or 1?! From a EntropyProfiler! " << std::endl;
    m_block_size = p.block_size;  // may be 0 at this point. Updated in init()
    m_dedup_fingerprint_size_bits = p.dedup_fingerprint_size_bits;
    m_compute_line_level_entropy = p.compute_line_level_entropy;
    m_xor_folding_scheme = p.xor_folding_scheme;
}

void
EntropyProfiler::init()
{
    if (m_block_size == 0) {
        m_block_size = RubySystem::getBlockSizeBytes();
    }
}

EntropyProfiler::~EntropyProfiler()
{
}

void
EntropyProfiler::registerData(DataBlock blk)
{
    // calculate number of 0 and 1 in the blk
    int num_1 = 0;
    int num_0 = 0;
    for (int i = 0; i < m_block_size; i++) {
        uint8_t * chunk8 = reinterpret_cast<uint8_t*>(blk.getDataMod(i));
        // count number of zeros in the byte
        int ct1 = __builtin_popcount(chunk8[0]);
        num_1 += ct1;
        num_0 += (8 - ct1);

        entropyProfilerStats.byteDist[chunk8[0]]++;
    }
    entropyProfilerStats.bitDist[0] += num_0;
    entropyProfilerStats.bitDist[1] += num_1;
    
    // bit level entropy calculation
    int total_bits = entropyProfilerStats.bitDist[0].value() + entropyProfilerStats.bitDist[1].value();
    float zero_count = entropyProfilerStats.bitDist[0].value();
    float one_count = entropyProfilerStats.bitDist[1].value();
    float prob_0 = 0;
    float prob_1 = 0;
    double entropy_bit_level = 0;
    if (zero_count == 0 || one_count == 0) {
        entropy_bit_level = 0;
    }
    else {
        prob_0 = zero_count/total_bits;
        prob_1 = one_count/total_bits;
        entropy_bit_level = 0 - (prob_0 * log2(prob_0) + prob_1 * log2(prob_1));
        assert (!std::isnan(entropy_bit_level));
    }
    entropyProfilerStats.entropy_bit_level = entropy_bit_level;
    DPRINTF(RubyEntropyProfiler, "EntropyProfiler: bit level entropy: %f\n", entropyProfilerStats.entropy_bit_level.value());

    // byte level entropy calculation
    int total_bytes = 0;
    for (int i = 0; i < 256; i++) {
        total_bytes += entropyProfilerStats.byteDist[i].value();
    }
    float sum = 0;
    if (total_bytes == 0) {
        entropyProfilerStats.entropy_byte_level = 0;
    } else {
        for (int i = 0; i < 256; i++) {
            float prob = entropyProfilerStats.byteDist[i].value()/total_bytes;
            if (prob != 0) {
                sum += prob * log2(prob);
            }
        }
        assert(!std::isnan(sum));
        entropyProfilerStats.entropy_byte_level = 0-sum;
    }
    DPRINTF(RubyEntropyProfiler, "EntropyProfiler: byte level entropy: %f\n", entropyProfilerStats.entropy_byte_level.value());

    
    // hashed line level entropy calculation
    entropyProfilerStats.hashLineCt++;
    if (m_compute_line_level_entropy) {
        int hash = blk.xor_folding(blk, m_dedup_fingerprint_size_bits, m_block_size, m_xor_folding_scheme);
        entropyProfilerStats.hashLineDist[hash] += 1;

        int total_hashes = 0;
        for (int i = 0; i < pow(2, m_dedup_fingerprint_size_bits); i++) {
            total_hashes += entropyProfilerStats.hashLineDist[i].value();
        }
        DPRINTF(RubyEntropyProfiler, "EntropyProfiler: total hashed line ct %d\n", total_hashes);
        float sum_line = 0;
        for (int i = 0; i < pow(2, m_dedup_fingerprint_size_bits); i++) {
            float prob = entropyProfilerStats.hashLineDist[i].value()/total_hashes;
            if (prob != 0) {
                sum_line += prob * log2(prob);
            }
        }
        if (!std::isnan(sum_line)) {
            entropyProfilerStats.entropy_line_level_approx = 0-sum_line;
            DPRINTF(RubyEntropyProfiler, "EntropyProfiler: line level entropy: %f\n", entropyProfilerStats.entropy_line_level_approx.value());
        }
    }
}

void
EntropyProfiler::removeData(DataBlock blk)
{
    // calculate number of 0 and 1 in the blk
    int num_1 = 0;
    int num_0 = 0;
    for (int i = 0; i < m_block_size; i++) {
        uint8_t * chunk8 = reinterpret_cast<uint8_t*>(blk.getDataMod(i));
        // count number of zeros in the byte
        int ct1 = __builtin_popcount(chunk8[0]);
        num_1 += ct1;
        num_0 += (8 - ct1);

        if (entropyProfilerStats.byteDist[chunk8[0]].value() <= 0) {
            DPRINTF(RubyEntropyProfiler, "EntropyProfiler: trying to remove non-existing byte %llx\n", chunk8[0]);
        }
        assert(entropyProfilerStats.byteDist[chunk8[0]].value() > 0);
        entropyProfilerStats.byteDist[chunk8[0]]--;
    }
    assert(entropyProfilerStats.bitDist[0].value() >= num_0);
    assert(entropyProfilerStats.bitDist[1].value() >= num_1);
    entropyProfilerStats.bitDist[0] -= num_0;
    entropyProfilerStats.bitDist[1] -= num_1;

    // bit level entropy calculation
    int total_bits = entropyProfilerStats.bitDist[0].value() + entropyProfilerStats.bitDist[1].value();
    float zero_count = entropyProfilerStats.bitDist[0].value();
    float one_count = entropyProfilerStats.bitDist[1].value();
    float prob_0 = 0;
    float prob_1 = 0;
    double entropy_bit_level = 0;
    if (zero_count == 0 || one_count == 0) {
        entropy_bit_level = 0;
    }
    else {
        prob_0 = zero_count/total_bits;
        prob_1 = one_count/total_bits;
        entropy_bit_level = 0 - (prob_0 * log2(prob_0) + prob_1 * log2(prob_1));
        assert (!std::isnan(entropy_bit_level));
    }
    entropyProfilerStats.entropy_bit_level = entropy_bit_level;
    DPRINTF(RubyEntropyProfiler, "EntropyProfiler: bit level entropy: %f\n", entropyProfilerStats.entropy_bit_level.value());

    // byte level entropy calculation
    int total_bytes = 0;
    for (int i = 0; i < 256; i++) {
        total_bytes += entropyProfilerStats.byteDist[i].value();
    }
    float sum = 0;
    if (total_bytes == 0) {
        entropyProfilerStats.entropy_byte_level = 0;
    } else {
        for (int i = 0; i < 256; i++) {
            float prob = entropyProfilerStats.byteDist[i].value()/total_bytes;
            if (prob != 0) {
                sum += prob * log2(prob);
            }
        }
        assert(!std::isnan(sum));
        entropyProfilerStats.entropy_byte_level = 0-sum;
    }
    DPRINTF(RubyEntropyProfiler, "EntropyProfiler: byte level entropy: %f\n", entropyProfilerStats.entropy_byte_level.value());

    // hashed line level entropy calculation
    entropyProfilerStats.hashLineCt--;
    if (m_compute_line_level_entropy) {
        uint64_t hash = blk.xor_folding(blk, m_dedup_fingerprint_size_bits, m_block_size, m_xor_folding_scheme);
        assert(hash < pow(2, m_dedup_fingerprint_size_bits));
        if (entropyProfilerStats.hashLineDist[hash].value() <= 0) {
            DPRINTF(RubyEntropyProfiler, "EntropyProfiler: trying to remove non-existing hashedline hash=%llx, line=%s\n", hash,blk);
        }
        assert(entropyProfilerStats.hashLineDist[hash].value() > 0);
        entropyProfilerStats.hashLineDist[hash] -= 1;


        int total_hashes = 0;
        for (int i = 0; i < pow(2, m_dedup_fingerprint_size_bits); i++) {
            total_hashes += entropyProfilerStats.hashLineDist[i].value();
        }
        DPRINTF(RubyEntropyProfiler, "EntropyProfiler: total hashed line ct %d\n", total_hashes);
        float sum_line = 0;
        for (int i = 0; i < pow(2, m_dedup_fingerprint_size_bits); i++) {
            float prob = entropyProfilerStats.hashLineDist[i].value()/total_hashes;
            if (prob != 0) {
                sum_line += prob * log2(prob);
            }
        }
        if (!std::isnan(sum_line)) {
            entropyProfilerStats.entropy_line_level_approx = 0-sum_line;
            DPRINTF(RubyEntropyProfiler, "EntropyProfiler: line level entropy: %f\n", entropyProfilerStats.entropy_line_level_approx.value());
        }
    }
}

// void
// EntropyProfiler::updateEntropy(EntropyProfilerStats entropyProfilerStats)
// {
//     // bit level entropy calculation
//     int total_bits = entropyProfilerStats.bitDist[0].value() + entropyProfilerStats.bitDist[1].value();
//     float prob_0 = entropyProfilerStats.bitDist[0].value()/total_bits;
//     float prob_1 = entropyProfilerStats.bitDist[1].value()/total_bits;
//     entropyProfilerStats.entropy_bit_level = 0- (prob_0 * log2(prob_0) + prob_1 * log2(prob_1));

//     // byte level entropy calculation
//     int total_bytes = 0;
//     for (int i = 0; i < 256; i++) {
//         total_bytes += entropyProfilerStats.byteDist[i].value();
//     }
//     float sum = 0;
//     for (int i = 0; i < 256; i++) {
//         float prob = entropyProfilerStats.byteDist[i].value()/total_bytes;
//         if (prob != 0) {
//             sum += prob * log2(prob);
//         }
//     }
//     entropyProfilerStats.entropy_byte_level = 0-sum;
// }



// =========== Other ===========
void
EntropyProfiler::print(std::ostream& out) const
{
    out << "EntropyProfiler dump: " << name() << std::endl;
    
}

EntropyProfiler::
EntropyProfilerStats::EntropyProfilerStats(statistics::Group *parent, int hash_bits)
    : statistics::Group(parent),
      ADD_STAT(bitDist, "Bit distribution of entire cache"),
      ADD_STAT(byteDist, "Byte distribution of entire cache"),
      ADD_STAT(hashLineDist, "Hash distribution of lines in the entire cache"),
      ADD_STAT(entropy_bit_level, "Entropy of bit level"),
      ADD_STAT(entropy_byte_level, "Entropy of byte level"),
      ADD_STAT(entropy_line_level_approx, "Approximate entropy of line level"),
      ADD_STAT(hashLineCt, "Number of hashed lines in the entire cache")
{
    bitDist
    .init(2)
    .flags(statistics::total | statistics::nozero | statistics::nonan | statistics::dist | statistics::pdf)
    ;
    byteDist
    .init(256)
    .flags(statistics::total | statistics::nozero | statistics::nonan | statistics::dist | statistics::pdf)
    ;
    hashLineDist
    .init(pow(2, hash_bits))
    .flags(statistics::total | statistics::nozero | statistics::nonan | statistics::dist | statistics::pdf)
    ;

    entropy_bit_level
        .flags(statistics::nozero | statistics::nonan);
    
    entropy_byte_level
        .flags(statistics::nozero | statistics::nonan);
    
    entropy_line_level_approx
        .flags(statistics::nozero | statistics::nonan);
    
    hashLineCt
        .flags(statistics::nonan);
}

} // namespace ruby
} // namespace gem5
