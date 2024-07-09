#include "mem/ruby/structures/mystructures/msi/AssociativeMapTable.hh"

#include "base/compiler.hh"
#include "base/intmath.hh"
#include "base/logging.hh"
#include "base/random.hh"
#include "debug/RubyAssociativeMapTable.hh"
#include "mem/ruby/system/RubySystem.hh"

#include <iostream>

namespace gem5
{

namespace ruby
{

std::ostream&
operator<<(std::ostream& out, const AssociativeMapTable& obj)
{
    obj.print(out);
    out << std::flush;
    return out;
}

AssociativeMapTable::AssociativeMapTable(const Params &p)
    : SimObject(p),
    associativeMapTableStats(this, pow(2, p.map_bits))
{
    m_map_bits = p.map_bits;
    // assert(m_map_bits <= 16);
    m_regular_xor_folding = p.regular_xor_folding;
    m_xor_policy = p.xor_policy;
    // std::cout << "select candidate! From a AssociativeMapTable! map bits=" << m_map_bits << std::endl;
    m_num_sets = p.num_sets;
    m_assoc = p.assoc;
    m_replacementPolicy_ptr = p.replacement_policy;
    m_block_size = p.block_size;  // may be 0 at this point. Updated in init()
}

void
AssociativeMapTable::init()
{
    if (m_block_size == 0) {
        m_block_size = RubySystem::getBlockSizeBytes();
    }

    m_num_set_bits = floorLog2(m_num_sets);
    assert(m_num_set_bits >= 0);

    m_map_table.resize(m_num_sets,
                    std::vector<Addr>(m_assoc, Addr));
    m_valid.resize(m_num_sets,
                    std::vector<bool>(m_assoc, false));
    replacement_data.resize(m_cache_num_sets,
                               std::vector<ReplData>(m_cache_assoc, nullptr));
    
    // instantiate all the replacement_data here
    for (int i = 0; i < m_num_sets; i++) {
        for ( int j = 0; j < m_assoc; j++) {
            replacement_data[i][j] =
                                m_replacementPolicy_ptr->instantiateEntry();
        }
    }
}

AssociativeMapTable::~AssociativeMapTable()
{
    if (m_replacementPolicy_ptr)
        delete m_replacementPolicy_ptr;

    for (int i = 0; i < m_num_sets; i++) {
        m_map_table[i].clear();
        m_valid[i].clear();
    }
    m_uomap.clear();
    m_hash_way_map.clear();
}
void
AssociativeMapTable::print(std::ostream& out) const
{
    out << "AssociativeMapTable dump: " << name() << std::endl;
    
}

int
AssociativeMapTable::getNumberOfBins() const
{
    return pow(2, m_map_bits);
}

uint64_t
AssociativeMapTable::blockToMap(DataBlock blk) const
{   
    uint64_t hash = blk.xor_folding(blk, m_map_bits, m_block_size, m_regular_xor_folding);

    DPRINTF(RubyAssociativeMapTable, "map fingerprint = %d\n", hash);
    return hash;
}
// convert a hash to its location in the map table
int64_t
AssociativeMapTable::mapToSet(uint64_t hash) const
{   
    DPRINTF(RubyAssociativeMapTable, "map fingerprint = %d, set bits=[%d, %d]\n", hash, 
        m_start_index_bit, m_start_index_bit + m_num_set_bits - 1);
    if (m_num_set_bits == 0) {
        return int64_t(0);
    }
    return bitSelect(hash, m_start_index_bit,
                     m_start_index_bit + m_num_set_bits - 1);
}

void 
AssociativeMapTable::insert(Addr addr, DataBlock blk) {
    uint64_t map_index = blockToMap(blk);
    insert_map(addr, map_index);
}

void 
AssociativeMapTable::insert_map(Addr addr, uint64_t map_index) {
    DPRINTF(RubyAssociativeMapTable, "inserting 0x%llx to map_index %d\n", addr, map_index);
    int64_t set = mapToSet(map_index);
    DPRINTF(RubyAssociativeMapTable, "inserting 0x%llx to set %d\n", addr, set);
    // check if we have hit
    if (m_hash_way_map[map_index] != -1) {
        int way = m_hash_way_map[map_index];
        DPRINTF(RubyAssociativeMapTable, "already hit at way %d\n", way);
        assert(m_valid[set][way]);
        Addr old_addr = m_map_table[set][way];
        DPRINTF(RubyAssociativeMapTable, "old_addr=0x%llx\n", old_addr);
        assert(m_uomap[old_addr] == map_index);
        m_uomap.erase(old_addr);
        m_map_table[set][way] = addr;
        m_uomap[addr] = map_index;
        m_replacementPolicy_ptr->touch(replacement_data[set][way]);
        associativeMapTableStats.numAddrUpdate++;
    } else {
        // check every way in the set for invalid
        int way = -1;
        for (int i = 0; i < m_assoc; i++) {
            if (!m_valid[set][i]) {
                way = i;
                break;
            }
        }
        if (way != -1) {
            // found invalid way
            m_valid[set][way] = true;
            m_map_table[set][way] = addr;
            m_uomap[addr] = map_index;
            m_hash_way_map[map_index] = way;
            m_replacementPolicy_ptr->reset(replacement_data[set][way]);
            associativeMapTableStats.numInUse += 1;
        } else {
            // no invalid way, evict one
            way = m_replacementPolicy_ptr->getVictim(replacement_data[set]);
            Addr old_addr = m_map_table[set][way];
            uint64_t old_map_index = m_uomap[old_addr];
            DPRINTF(RubyAssociativeMapTable, "evicting 0x%llx from way %d, old map value=%d\n", old_addr, way, old_map_index);
            m_uomap.erase(old_addr);
            m_hash_way_map.erase(old_map_index);

            m_map_table[set][way] = addr;
            m_uomap[addr] = map_index;
            m_hash_way_map[map_index] = way;
            m_replacementPolicy_ptr->invalidate(replacement_data[set][way]);
            m_replacementPolicy_ptr->reset(replacement_data[set][way]);
            associativeMapTableStats.hashValueReplacement += 1;
        }
    }
}

void
AssociativeMapTable::remove(Addr addr) {
    DPRINTF(RubyAssociativeMapTable, "removing 0x%llx\n", addr);
    if (m_uomap.find(addr) == m_uomap.end()) {
        DPRINTF(RubyAssociativeMapTable, "not found\n");
        return;
    }
    uint64_t map_index = m_uomap[addr];
    int64_t set = mapToSet(map_index);
    int way = m_hash_way_map[map_index];
    assert(m_valid[set][way]);
    m_valid[set][way] = false;
    m_map_table[set][way] = 0;
    m_uomap.erase(addr);
    m_hash_way_map.erase(map_index);
    associativeMapTableStats.numInUse -= 1;
}

uint64_t
AssociativeMapTable::remove_return(Addr addr) {
    assert(m_uomap.find(addr) != m_uomap.end());
    uint64_t map_index = m_uomap[addr];
    remove(addr);
    return map_index;
}


bool
AssociativeMapTable::hasRegisteredCandidate(DataBlock blk) const {
    uint64_t map_index = blockToMap(blk);
    DPRINTF(RubyAssociativeMapTable, "checking map_index %d for registed candidate\n", map_index);
    int set = mapToSet(map_index);
    int way = m_hash_way_map[map_index];
    if (m_valid[set][way]) {
        return true;
    }
    return false;
}

bool
AssociativeMapTable::hasAnyRegisteredCandidate() const {
    for (int i = 0; i < getNumberOfBins(); i++) {
        if (!m_map_table[i].empty()) {
            return true;
        }
    }
    return false;
}

int
AssociativeMapTable::getAnyRegisteredCandidateCt() const {
    int result = 0;
    for (int i = 0; i < getNumberOfBins(); i++) {
        result += m_map_table[i].size();
    }
    return result;
}


int
AssociativeMapTable::getRegisteredCandidateCt(DataBlock blk) const {
    uint64_t map_index = blockToMap(blk);
    DPRINTF(RubyAssociativeMapTable, "checking map_index %d for registed candidate\n", map_index);
    return m_map_table[map_index].size();
}

Addr
AssociativeMapTable::getAnyRandomRegisteredCandidate() {
    assert(hasAnyRegisteredCandidate());
    uint64_t map_index = random_mt.random<unsigned>(0,getNumberOfBins() - 1);
    while (m_map_table[map_index].empty()) {
        map_index = random_mt.random<unsigned>(0,getNumberOfBins() - 1);
    }
    if (m_map_table[map_index].empty()) {
        panic("No candidate in map_index %d\n", map_index);
    }
    DPRINTF(RubyAssociativeMapTable, "getting any random candidate from map_index %d, size=%d\n", map_index, m_map_table[map_index].size() );
    
    // queue traversal
    int random_index = random_mt.random<unsigned>(0,m_map_table[map_index].size() - 1);
    DPRINTF(RubyAssociativeMapTable, "random_index=%d\n", random_index);

    std::queue<Addr> temp_queue;
    Addr result = 0;
    while (!m_map_table[map_index].empty()) {
        Addr temp_addr = m_map_table[map_index].front();
        if (random_index == 0) {
            result = temp_addr;
            temp_queue.push(temp_addr);
        } else {
            temp_queue.push(temp_addr);
        }
        m_map_table[map_index].pop();
        random_index--;
    }
    while (!temp_queue.empty()) {
        m_map_table[map_index].push(temp_queue.front());
        temp_queue.pop();
    }
    DPRINTF(RubyAssociativeMapTable, "after traversal size m_map_table[%d]=%d\n", map_index, m_map_table[map_index].size() );
    associativeMapTableStats.numMapRandomXOR++;
    return result;
}

Addr
AssociativeMapTable::getRandomRegisteredCandidate(DataBlock blk) {
    uint64_t map_index = blockToMap(blk);
    DPRINTF(RubyAssociativeMapTable, "getting random candidate from map_index %d, size=%d\n", map_index, m_map_table[map_index].size());
    if (m_map_table[map_index].empty()) {
        panic("No candidate in map_index %d\n", map_index);
    }
    int random_index = random_mt.random<unsigned>(0,m_map_table[map_index].size() - 1);
    
    // queue traversal

    std::queue<Addr> temp_queue;
    Addr result = 0;
    while (!m_map_table[map_index].empty()) {
        Addr temp_addr = m_map_table[map_index].front();
        if (random_index == 0) {
            result = temp_addr;
            temp_queue.push(temp_addr);
        } else {
            temp_queue.push(temp_addr);
        }
        m_map_table[map_index].pop();
        random_index--;
    }
    while (!temp_queue.empty()) {
        m_map_table[map_index].push(temp_queue.front());
        temp_queue.pop();
    }
    // associativeMapTableStats.listCapacityInUse[map_index] -= 1;
    // m_uomap.erase(result);
    DPRINTF(RubyAssociativeMapTable, "after traversal size m_map_table[%d]=%d\n", map_index, m_map_table[map_index].size() );
    associativeMapTableStats.numMapCollisionXOR++;
    return result;
}

bool
AssociativeMapTable::isCandidate(Addr addr) const {
    return m_uomap.find(addr) != m_uomap.end();
}

void
AssociativeMapTable::profileRead()
{
    associativeMapTableStats.m_read++;
}

void
AssociativeMapTable::profileWrite()
{
    associativeMapTableStats.m_write++;
}

AssociativeMapTable::
AssociativeMapTableStats::AssociativeMapTableStats(statistics::Group *parent)
    : statistics::Group(parent),
      ADD_STAT(numInUse, statistics::units::Rate<
                statistics::units::Count, statistics::units::Tick>::get(), "numInUse"),
      ADD_STAT(numMapCollisionXOR, "Number of xor that map to the same index"),
      ADD_STAT(numMapRandomXOR, "Number of xor that is randomly chosen"),
      ADD_STAT(numAddrUpdate, "Number of address update"),
      ADD_STAT(m_read, "Number of read"),
      ADD_STAT(m_write, "Number of write"),
      ADD_STAT(hashValueReplacement, "Number of hash value replacement")
{
    numInUse
        .flags(statistics::nozero);

    numMapCollisionXOR
        .flags(statistics::nozero);

    numMapRandomXOR
        .flags(statistics::nozero);

    numAddrUpdate
        .flags(statistics::nozero);

    m_read
        .flags(statistics::nozero);

    m_write
        .flags(statistics::nozero);

    hashValueReplacement
        .flags(statistics::nozero);
}


} // namespace ruby
} // namespace gem5
