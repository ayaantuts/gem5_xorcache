/*
 * Copyright (c) 2021 ARM Limited
 * All rights reserved.
 *
 * The license below extends only to copyright in the software and shall
 * not be construed as granting a license to any other intellectual
 * property including but not limited to intellectual property relating
 * to a hardware implementation of the functionality of the software
 * licensed hereunder.  You may use the software subject to the license
 * terms below provided that you ensure that this notice is replicated
 * unmodified and in its entirety in all distributions of the software,
 * modified or unmodified, in source code or in binary form.
 *
 * Copyright (c) 1999-2008 Mark D. Hill and David A. Wood
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met: redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer;
 * redistributions in binary form must reproduce the above copyright
 * notice, this list of conditions and the following disclaimer in the
 * documentation and/or other materials provided with the distribution;
 * neither the name of the copyright holders nor the names of its
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#include "mem/ruby/common/DataBlock.hh"

#include "mem/ruby/common/WriteMask.hh"
#include "mem/ruby/system/RubySystem.hh"
#include "config/dump_cache.hh"

#include <iostream>
#include <numeric>
#include <random>
#include <vector>
#include <algorithm>
namespace gem5
{

namespace ruby
{

DataBlock::DataBlock(const DataBlock &cp)
{
    m_data = new uint8_t[RubySystem::getBlockSizeBytes()];
    memcpy(m_data, cp.m_data, RubySystem::getBlockSizeBytes());
    m_alloc = true;
}

void
DataBlock::alloc()
{
    m_data = new uint8_t[RubySystem::getBlockSizeBytes()];
    m_alloc = true;
    DPRINTF(RubyDataBlock, "alloc() in DataBlock, %#x\n", reinterpret_cast<uintptr_t>(m_data));
    clear();
}

void
DataBlock::clear()
{
    DPRINTF(RubyDataBlock, "clear() in DataBlock, %#x\n", reinterpret_cast<uintptr_t>(m_data));
    memset(m_data, 0, RubySystem::getBlockSizeBytes());
}

bool
DataBlock::equal(const DataBlock& obj) const
{
    return !memcmp(m_data, obj.m_data, RubySystem::getBlockSizeBytes());
}

void
DataBlock::copyPartial(const DataBlock &dblk, const WriteMask &mask)
{
    DPRINTF(RubyDataBlock, "copyPartial() in DataBlock, %#x\n", reinterpret_cast<uintptr_t>(m_data));
    for (int i = 0; i < RubySystem::getBlockSizeBytes(); i++) {
        if (mask.getMask(i, 1)) {
            m_data[i] = dblk.m_data[i];
        }
    }
}

void
DataBlock::atomicPartial(const DataBlock &dblk, const WriteMask &mask)
{
    DPRINTF(RubyDataBlock, "atomicPartial() in DataBlock, %#x\n", reinterpret_cast<uintptr_t>(m_data));
    for (int i = 0; i < RubySystem::getBlockSizeBytes(); i++) {
        m_data[i] = dblk.m_data[i];
    }
    mask.performAtomic(m_data);
}

void
DataBlock::print(std::ostream& out) const
{
    int size = RubySystem::getBlockSizeBytes();
#if DUMP_CACHE
    out << "";
    for (int i = 0; i < size; i++) {
        out << (int)m_data[i] << " ";
    }
    out << "" << std::flush;
#else
    out << "[ ";
    for (int i = 0; i < size; i++) {
        out << std::setw(2) << std::setfill('0') << std::hex
            << "0x" << (int)m_data[i] << " " << std::setfill(' ');
    }
    // out << std::dec << "]" << std::flush;
    out << std::dec <<"] ("<< std::hex << reinterpret_cast<uintptr_t>(m_data) << std::dec <<")"  << std::flush;
#endif
}

const uint8_t*
DataBlock::getData(int offset, int len) const
{
    assert(offset + len <= RubySystem::getBlockSizeBytes());
    return &m_data[offset];
}

uint8_t*
DataBlock::getDataMod(int offset)
{
    return &m_data[offset];
}

void
DataBlock::setData(const uint8_t *data, int offset, int len)
{
    DPRINTF(RubyDataBlock, "setData1() in DataBlock, %#x\n", reinterpret_cast<uintptr_t>(m_data));
    memcpy(&m_data[offset], data, len);
}

void
DataBlock::setData(PacketPtr pkt)
{
    DPRINTF(RubyDataBlock, "setData2() in DataBlock, %#x\n", reinterpret_cast<uintptr_t>(m_data));
    int offset = getOffset(pkt->getAddr());
    assert(offset + pkt->getSize() <= RubySystem::getBlockSizeBytes());
    pkt->writeData(&m_data[offset]);
}

DataBlock &
DataBlock::operator=(const DataBlock & obj)
{
    DPRINTF(RubyDataBlock, "operator= in DataBlock, dest=%#x, src=%#x\n", reinterpret_cast<uintptr_t>(m_data),
        reinterpret_cast<uintptr_t>(obj.m_data));
    memcpy(m_data, obj.m_data, RubySystem::getBlockSizeBytes());
    return *this;
}

DataBlock
DataBlock::scramble() const
{
    // Create a new DataBlock for scrambled data
    DataBlock scrambled_blk = DataBlock();


    // Fixed seed for random number generator
    unsigned int fixed_seed = 12345; // Example fixed seed
    std::default_random_engine rng(fixed_seed);

    // Apply the shuffling pattern
    std::stringstream pattern_stream; // Using stringstream to build the pattern string
    pattern_stream << "Scramble pattern: "; // Starting the pattern description

    // Define a shuffling pattern
    std::vector<int> shuffle_pattern(RubySystem::getBlockSizeBytes() * 8);
    std::iota(shuffle_pattern.begin(), shuffle_pattern.end(), 0); // Fill with 0, 1, 2, ...
    std::shuffle(shuffle_pattern.begin(), shuffle_pattern.end(), rng); // Shuffle the pattern

    // Apply the shuffling pattern
    for (size_t i = 0; i < shuffle_pattern.size(); ++i) {
        int original_pos = shuffle_pattern[i];
        int byte_pos = original_pos / 8;
        int bit_pos = original_pos % 8;

        // Set bit i of scrambled_blk.m_data to bit original_pos of this->m_data
        if (this->m_data[byte_pos] & (1 << bit_pos))
            scrambled_blk.m_data[i / 8] |= (1 << (i % 8));
        else
            scrambled_blk.m_data[i / 8] &= ~(1 << (i % 8));
        
        // Build the pattern string with the specified format
        pattern_stream << "[" << original_pos << "]";
        if (i < shuffle_pattern.size() - 1) {
            pattern_stream << "^"; // Separator for readability
        }
    }
    // Use DPRINTF to print the pattern
    DPRINTF(RubyDataTransformation, "%s\n", pattern_stream.str().c_str());

    return scrambled_blk;
}

bool
DataBlock::bitExtractedAtIndex(uint8_t * number, int index) const
{
   int byte_index = index / 8;
   int bit_index = index % 8;
   uint8_t byte = number[byte_index];
   // printf("byte[%d]=%d\n", byte_index, byte);
   uint8_t shifted = byte >> bit_index;
   // printf("shifted=%d\n", shifted);
   uint8_t final = shifted & 1;
   // printf("bit[%d]=%d\n", index, final);
   return final;
}

uint8_t *
DataBlock::bit_xor_folding(uint8_t * data, int data_size_in_bit, int fingerprint_size_in_bit) const
{
    uint8_t * fingerprint;
    fingerprint = new uint8_t[int(ceil(fingerprint_size_in_bit / 8.0))]();
    // note that fingerprint_size_in_bit can be arbitrary, say non-power-of-2, so we may need to pad the data

    // compute the padding and number of times folding is needed
    int num_chunks = ceil((double)data_size_in_bit / (double)fingerprint_size_in_bit);
    // int totoal_size = fingerprint_size_in_bit * num_chunks; // in bit

    for (int i = 0; i < fingerprint_size_in_bit; i++)
    {
        int j = 0;
        int bit_index = i+j*(fingerprint_size_in_bit);
        bool bit;
        if (bit_index >= data_size_in_bit) {
            bit = 0;
        } else {
            bit = bitExtractedAtIndex(data, bit_index);
        }
        // printf("    0th chunk, bit[%d]=%d\n", bit_index, bit);

        for (int j = 1; j < num_chunks; j++)
        {
            int bit_index = i+j*(fingerprint_size_in_bit);
            bool new_bit;
            if (bit_index < data_size_in_bit) {
            new_bit = bitExtractedAtIndex(data, bit_index);
            bit = bit ^ new_bit;
            // printf("    %dth chunk, bit[%d]=%d\n", j, bit_index, bit);
            } 
            // else {
            //    new_bit = 0;
            // }
            // printf("XORing data[%d] with data[%d]\n", i+(j-1)*(fingerprint_size_in_bit), bit_index);  // Add this line

        }
        // set the bit at figerprint_size_in_bit-i to be bit
        int ind = i;
        int byte_set = (ind) / 8;
        int bit_set = (ind) % 8;
        // printf("setting bit %d to %d\n", ind, bit);
        fingerprint[byte_set] |= bit << bit_set;
        // printf("\n");
    }
    return fingerprint;
}


// hash functions
uint64_t
DataBlock::xor_folding(DataBlock & blk, int fingerprint_bits, int m_block_size, int scheme) const
{
    if (scheme == 0) { // dense byte label
        return dense_byte_label_shuffle_fold(blk, fingerprint_bits, m_block_size);
    } else if (scheme == 1) { // sparse byte label
        return sparse_byte_label_shuffle_fold(blk, fingerprint_bits, m_block_size);
    } else {
        panic("scheme = %d is not supported\n", scheme);
    }
}
uint64_t
DataBlock::regular_xor_folding(const DataBlock & blk, int fingerprint_bits, int m_block_size) const
{
    DPRINTF(RubyDataTransformation, "regular_xor_folding() in DataBlock, %s\n", blk);
    int cache_block_size_in_bits = 8 * m_block_size;
    int times_xor_folding = floorLog2(cache_block_size_in_bits / fingerprint_bits);

    DataBlock xor_folding_result = DataBlock();
    xor_folding_result.clear();
    DataBlock ping = blk;
    // DataBlock ping = DataBlock();
    // ping.assign(m_data);

    int num_bytes_so_far = m_block_size;

    for (int j = 0; j < times_xor_folding; j++) {
        num_bytes_so_far = num_bytes_so_far/2;
        xor_folding_result.clear();
        // DPRINTF(RubyDataTransformation, "round %d\n", j);
        for (int i = 0; i < num_bytes_so_far; i++) {
            uint8_t * chunk8_rhs = reinterpret_cast<uint8_t*>(ping.getDataMod(i));
            uint8_t * chunk8_lhs = reinterpret_cast<uint8_t*>(ping.getDataMod(i+num_bytes_so_far));
            uint8_t chunck8_xor_result = uint8_t(chunk8_rhs[0])^uint8_t(chunk8_lhs[0]);
            DPRINTF(RubyDataTransformation, " %dth B: 0x%llx ^ 0x%llx = 0x%llx\n", i, chunk8_rhs[0], chunk8_lhs[0], chunck8_xor_result);
            xor_folding_result.setData(&chunck8_xor_result,i,1);
        }
        ping = xor_folding_result;
    }
    // convert LSB 64 bits data in ping to uint64_t
    uint8_t * chunk8 = reinterpret_cast<uint8_t*>(ping.getDataMod(0));
    uint64_t result = 0;
    for (int i = 0; i < 8; i++) {
        result = result | (uint64_t(chunk8[i]) << (8*i));
    }
    DPRINTF(RubyDataTransformation, "fingerprint = %d\n", result);
    return result;
}

uint64_t
DataBlock::arbitrary_xor_folding(const DataBlock & blk, int fingerprint_bits, int m_block_size) const
{
    // this function take a datablock and generate a fingerprint with fingerprint_bits bits long.
    // the datablock is first scrabled by a random permutation, then every block length / fingerprint_bits
    // bits are xored together to generate one bit fingerprint.

    // Scramble the data block without modifying the original
    DPRINTF(RubyDataTransformation, "arbitrary_xor_folding() in DataBlock, %s\n", blk);
    DataBlock scrambled_blk = blk.scramble();
    DPRINTF(RubyDataTransformation, "scrambled_blk = %s\n", scrambled_blk);

    // Determine the number of bits in each segment to be XORed
    int segment_size_bits = 8 * m_block_size / fingerprint_bits;
    int segment_size_bytes = segment_size_bits / 8;

    uint64_t fingerprint = 0;
    uint8_t *scrambled_data = scrambled_blk.getDataMod(0);

    // Iterate over each bit of the fingerprint
    for (int bit = 0; bit < fingerprint_bits; ++bit) {
        uint8_t xor_byte_result = 0;

        // XOR every byte within the segment
        for (int byte = 0; byte < segment_size_bytes; ++byte) {
            int byte_index = bit * segment_size_bytes + byte;
            if (byte_index < m_block_size) {
                xor_byte_result ^= scrambled_data[byte_index];
                DPRINTF(RubyDataTransformation, "       byte_index=%d, xor_byte_result=0x%llx\n", byte_index, xor_byte_result);
            }
        }
        DPRINTF(RubyDataTransformation, "   xor_byte_result=%d (0x%llx)\n", xor_byte_result, xor_byte_result);
        

        // Perform bit-level XOR reduction on xor_byte_result
        uint8_t xor_bit_result = 0;
        for (int b = 0; b < 8; ++b) {
            xor_bit_result ^= (xor_byte_result >> b) & 1;
            DPRINTF(RubyDataTransformation, "       xor_bit_result=0x%llx\n", xor_bit_result);
        }
        DPRINTF(RubyDataTransformation, "   %d-bit fingerprint <reduction> xor_bit_result = %d\n", 
            bit, xor_bit_result);

        // Set the corresponding bit in the fingerprint
        fingerprint |= (uint64_t(xor_bit_result & 1) << bit);
    }

    DPRINTF(RubyDataTransformation, "fingerprint = %d (0x%llx)\n", fingerprint, fingerprint);
    return fingerprint;
}

uint64_t
DataBlock::lsh_xor_folding(DataBlock & blk, int fingerprint_bits, int m_block_size) const
{
    // DataBlock blk_cpy = blk;
    if (fingerprint_bits == 8) {
        DPRINTF(RubyDataTransformation, "lsh_xor_folding(8bit) in DataBlock, %s\n", blk);
        // for every 3 bytes, xor them together, then skip the next byte and repeat
        uint8_t * data = blk.getDataMod(0);
        uint8_t result = 0;
        for (int i = 0; i < m_block_size; i+=4) {
            if (i==0) {
                result = data[i+1];
                result ^= data[i+2];
                result ^= data[i+3];
                DPRINTF(RubyDataTransformation, "i=%d: %llx^%llx^%llx=%llx\n", 
                    i, data[i+1],data[i+2],data[i+3],result);
            } else {
                result ^= data[i+1];
                result ^= data[i+2];
                result ^= data[i+3];
                DPRINTF(RubyDataTransformation, "i=%d: prior^%llx^%llx^%llx=%llx\n", 
                    i, data[i+1],data[i+2],data[i+3],result);
            }
        }
        assert(result < (1 << 8));
        DPRINTF(RubyDataTransformation, "fingerprint = %d (0x%llx)\n", result, result);
        return result;
    } else if (fingerprint_bits == 24) {
        DPRINTF(RubyDataTransformation, "lsh_xor_folding(24bit) in DataBlock, %s\n", blk);
        // for every 8 bytes xor byte [0,1,2] with [4,5,6] to get a 3 bytes intermediate result
        // finally xor all the 3 bytes together
        uint8_t * data = blk.getDataMod(0);
        uint64_t result = 0;
        for (int i=0; i < m_block_size; i+=8) {
            uint8_t result_1_5 = data[i+1] ^ data[i+5];
            uint8_t result_2_6 = data[i+2] ^ data[i+6];
            uint8_t result_3_7 = data[i+3] ^ data[i+7];
            uint64_t result_152637 = result_1_5 | (uint64_t(result_2_6) << 8) | (uint64_t(result_3_7) << 16);
            if (i == 0) {
                result = result_152637;
            } else {
                result ^= result_152637;
            }
            DPRINTF(RubyDataTransformation, "i=%d: 1^5=%llx, 2^6=%llx, 3^7=%llx => %llx, result=%llx\n", 
                i, result_1_5,result_2_6,result_3_7,result_152637,result
                );
        }
        assert(result < (1 << 24));
        return result;
    } else {
        panic("fingerprint_bits = %d is not supported\n", fingerprint_bits);
    }
}
     
uint64_t
DataBlock::dense_byte_label_shuffle_fold(DataBlock & blk, int fingerprint_bits, int m_block_size) const
{
    srand( 12345 ); // seed the random number generator
    std::vector<int> index;
    for (int i = 0; i < m_block_size; i++) { index.push_back(i); }
    random_shuffle(index.begin(), index.end());

    // print index
    // DPRINTF(RubyDataTransformation, "BL index =");
    // for (int i = 0; i < index.size(); i++) {
    //     DPRINTF(RubyDataTransformation, "%d ",index[i]);
    // }
    // DPRINTF(RubyDataTransformation, "\n");

    uint8_t * data = blk.getDataMod(0);
    DPRINTF(RubyDataTransformation, "data = %s\n", blk);

    uint8_t * byte_mask = new uint8_t[8];
    memset(byte_mask, 0, 8);

    for (int i = 0; i < index.size(); i+=1) {
        int byte_index = i/8;
        int bit_index = i%8;
        if (data[index[i]] != 0) {
            byte_mask[byte_index] |= (1 << bit_index);
        }
    }
    index.clear();
    for (int i = 0; i < 8; i++) {
        DPRINTF(RubyDataTransformation, "byte_mask[%d] = 0x%llx\n", i, byte_mask[i]);
    }
    // DPRINTF(RubyDataTransformation, "byte_mask = 0x%llx\n", byte_mask);
    // xor fold it to get the fingerprint
    uint8_t * folded_byte_mask = bit_xor_folding(byte_mask, 64, fingerprint_bits);
    delete[] byte_mask;
    uint64_t result = 0;
    memset(&result, 0, sizeof(result));
    memcpy(&result, folded_byte_mask, int(ceil(fingerprint_bits / 8.0)));
    delete[] folded_byte_mask;

    uint64_t max_byte_mask = uint64_t(-1);
    assert (fingerprint_bits < 64);
    max_byte_mask = uint64_t(1);
    max_byte_mask = max_byte_mask << fingerprint_bits;
    max_byte_mask = max_byte_mask - 1;
    // DPRINTF(RubyDataTransformation, "max_byte_mask = %d (0x%llx)\n", max_byte_mask, max_byte_mask);
    assert(result <= max_byte_mask);
    DPRINTF(RubyDataTransformation, "fingerprint = %d (0x%llx)\n", result, result);
    return result;
}

uint64_t
DataBlock::sparse_byte_label_shuffle_fold(DataBlock & blk, int fingerprint_bits, int m_block_size) const
{
    srand( 12345 ); // seed the random number generator
    std::vector<int> index;
    int numword = m_block_size / 8;
    // taking every 6 ms byte of every 8 byte word
    for (int i = 0; i < numword; i++) { 
        for (int j = 0; j < 8; j++) {
            if (j == 0 || j == 1){ continue; }
            index.push_back(i*8+j);
        }
    }
    random_shuffle(index.begin(), index.end());

    // print index
    // DPRINTF(RubyDataTransformation, "SBL index =");
    // for (int i = 0; i < index.size(); i++) {
    //     DPRINTF(RubyDataTransformation, "%d ",index[i]);
    // }
    // DPRINTF(RubyDataTransformation, "\n");

    uint8_t * data = blk.getDataMod(0);
    DPRINTF(RubyDataTransformation, "data = %s\n", blk);

    uint8_t * byte_mask = new uint8_t[6];
    memset(byte_mask, 0, 6);

    for (int i = 0; i < index.size(); i+=1) {
        int byte_index = i/8;
        int bit_index = i%8;
        if (data[index[i]] != 0) {
            byte_mask[byte_index] |= (1 << bit_index);
        }
    }
    index.clear();
    for (int i = 0; i < 6; i++) {
        DPRINTF(RubyDataTransformation, "byte_mask[%d] = 0x%llx\n", i, byte_mask[i]);
    }
    // DPRINTF(RubyDataTransformation, "byte_mask = 0x%llx\n", byte_mask);
    // xor fold it to get the fingerprint
    uint8_t * folded_byte_mask = bit_xor_folding(byte_mask, 48, fingerprint_bits);
    delete[] byte_mask;
    uint64_t result = 0;
    memset(&result, 0, sizeof(result));
    memcpy(&result, folded_byte_mask, int(ceil(fingerprint_bits / 8.0)));
    delete[] folded_byte_mask;

    uint64_t max_byte_mask = uint64_t(-1);
    assert (fingerprint_bits < 64);
    max_byte_mask = uint64_t(1);
    max_byte_mask = max_byte_mask << fingerprint_bits;
    max_byte_mask = max_byte_mask - 1;
    // DPRINTF(RubyDataTransformation, "max_byte_mask = %d (0x%llx)\n", max_byte_mask, max_byte_mask);
    assert(result <= max_byte_mask);
    DPRINTF(RubyDataTransformation, "fingerprint = %d (0x%llx)\n", result, result);
    return result;
}


uint64_t
DataBlock::xBmap(DataBlock & blk, int fingerprint_bits, int m_block_size) const
{
    assert(m_block_size % fingerprint_bits == 0);
    int every_n_bytes = m_block_size / fingerprint_bits;
    uint8_t * data = blk.getDataMod(0);
    uint64_t byte_mask = 0;
    int bit_position_counter = 0;
    for (int i = 0; i < m_block_size/every_n_bytes; i+=1) {
        if (data[i*every_n_bytes] != 0) {
            uint64_t and_byte_mask = uint64_t(1);
            and_byte_mask = and_byte_mask << bit_position_counter;
            byte_mask |= and_byte_mask;
        }
        bit_position_counter += 1;
    }
    DPRINTF(RubyDataTransformation, "byte_mask = 0x%llx\n", byte_mask);
    
    uint64_t max_byte_mask = uint64_t(-1);
    if (fingerprint_bits < 64) {
        max_byte_mask = uint64_t(1);
        max_byte_mask = max_byte_mask << fingerprint_bits;
        max_byte_mask = max_byte_mask - 1;
    }
    assert(byte_mask <= max_byte_mask);

    return byte_mask;
}

uint64_t
DataBlock::thesaurus_lsh(DataBlock & blk, int fingerprint_bits, int m_block_size) const
{
    uint64_t fingerprint = 0;
    uint8_t * data = blk.getDataMod(0);
    std::vector<int *> lsh_matrix;

    srand (12345);
    for (int i = 0; i < fingerprint_bits; i++) {
        int *lsh_vector = new int[64];
        for (int j = 0; j < 64; j++) {
            int random = rand() % 6;
            if (random == 0) {
                lsh_vector[j] = 1;
            } else if (random == 1) {
                lsh_vector[j] = -1;
            } else {
                lsh_vector[j] = 0;
            }
        }
        lsh_matrix.push_back(lsh_vector);
    }

    for (int i = 0; i < lsh_matrix.size(); i++) {
        int * lsh_vector = lsh_matrix[i];
        int sum = 0;
        for (int j = 0; j < m_block_size; j++) {
            sum += lsh_vector[j] * (uint8_t)data[j];
            // DPRINTF(RubyDataTransformation, "   lsh_vector[%d]=%d, data[%d]=%d, sum=%d\n", 
                // j, lsh_vector[j], j, (uint8_t)data[j], sum);
        }
        if (sum > 0) {
            fingerprint += 1 << i;
        }
        // DPRINTF(RubyDataTransformation, "sum = %d, fingerprint = %d\n", sum, fingerprint);
    }

    // free the lsh_matrix
    for (int i = 0; i < lsh_matrix.size(); i++) {
        delete[] lsh_matrix[i];
    }
    lsh_matrix.clear();

    DPRINTF(RubyDataTransformation, "fingerprint = %d\n", fingerprint);
    
    return fingerprint;

}

} // namespace ruby
} // namespace gem5
