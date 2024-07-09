#include "mem/ruby/structures/mystructures/msi/DirectMapTable.hh"

#include "base/compiler.hh"
#include "base/intmath.hh"
#include "base/logging.hh"
#include "base/random.hh"
#include "debug/RubyDirectMapTable.hh"
#include "mem/ruby/system/RubySystem.hh"

#include <iostream>

namespace gem5
{

namespace ruby
{

std::ostream&
operator<<(std::ostream& out, const DirectMapTable& obj)
{
    obj.print(out);
    out << std::flush;
    return out;
}

DirectMapTable::DirectMapTable(const Params &p)
    : SimObject(p),
    directMapTableStats(this, pow(2, p.map_bits))
{
    m_map_bits = p.map_bits;
    assert(m_map_bits <= 16);
    m_list_capacity = p.list_capacity;
    m_xor_folding_scheme = p.xor_folding_scheme;
    m_xor_policy = p.xor_policy;
    // std::cout << "select candidate! From a DirectMapTable! map bits=" << m_map_bits << std::endl;
    m_block_size = p.block_size;  // may be 0 at this point. Updated in init()
}

void
DirectMapTable::init()
{
    if (m_block_size == 0) {
        m_block_size = RubySystem::getBlockSizeBytes();
    }

    for (int i = 0; i < (unsigned int)pow(2, m_map_bits); i++) {
        m_map_table.push_back(std::queue<Addr>());
    }
}

DirectMapTable::~DirectMapTable()
{
    for (int i = 0; i < (unsigned int)pow(2, m_map_bits); i++) {
        while (!m_map_table[i].empty())
        {
            m_map_table[i].pop();
        }
    }
    m_uomap.clear();
}
void
DirectMapTable::print(std::ostream& out) const
{
    out << "DirectMapTable dump: " << name() << std::endl;
    
}

int
DirectMapTable::getNumberOfBins() const
{
    return pow(2, m_map_bits);
}

uint64_t
DirectMapTable::blockToMap(DataBlock blk) const
{   
    uint64_t hash = blk.xor_folding(blk, m_map_bits, m_block_size, m_xor_folding_scheme);

    DPRINTF(RubyDirectMapTable, "map fingerprint = %d\n", hash);
    return hash;
}

void 
DirectMapTable::insert(Addr addr, DataBlock blk) {
    uint64_t map_index = blockToMap(blk);
    insert_map(addr, map_index);
}

void 
DirectMapTable::insert_map(Addr addr, uint64_t map_index) {
    DPRINTF(RubyDirectMapTable, "inserting 0x%llx to map_index %d\n", addr, map_index);
    m_map_table[map_index].push(addr);
    m_uomap[addr] = map_index;
    directMapTableStats.listCapacityInUse[map_index] += 1;
    if (m_map_table[map_index].size() > m_list_capacity) {
        directMapTableStats.numMaxCapcityReached[map_index]++;
        m_map_table[map_index].pop();
        directMapTableStats.listCapacityInUse[map_index] -= 1;
    }
}

void
DirectMapTable::remove(Addr addr) {
    remove_return(addr);
}

uint64_t
DirectMapTable::remove_return(Addr addr) {
    uint64_t map_index = m_uomap[addr];
    int found = 0;
    DPRINTF(RubyDirectMapTable, "removing 0x%llx from map_index %d\n", addr, map_index);
    std::queue<Addr> temp_queue;
    while (!m_map_table[map_index].empty()) {
        Addr temp_addr = m_map_table[map_index].front();
        if (temp_addr != addr) {
            temp_queue.push(temp_addr);
        } else {
            found += 1;
        }
        m_map_table[map_index].pop();
    }
    while (!temp_queue.empty()) {
        m_map_table[map_index].push(temp_queue.front());
        temp_queue.pop();
    }
    if (found == 1) {
        directMapTableStats.listCapacityInUse[map_index] -= 1;
    } else if (found == 0) {
        DPRINTF(RubyDirectMapTable, "no match\n");
    } else {
        panic("more than one match\n");
    }
    m_uomap.erase(addr);
    return map_index;
}


bool
DirectMapTable::hasRegisteredCandidate(DataBlock blk) const {
    uint64_t map_index = blockToMap(blk);
    DPRINTF(RubyDirectMapTable, "checking map_index %d for registed candidate\n", map_index);
    if (m_map_table[map_index].empty()) {
        return false;
    }
    return true;
}

bool
DirectMapTable::hasAnyRegisteredCandidate() const {
    for (int i = 0; i < getNumberOfBins(); i++) {
        if (!m_map_table[i].empty()) {
            return true;
        }
    }
    return false;
}

int
DirectMapTable::getAnyRegisteredCandidateCt() const {
    int result = 0;
    for (int i = 0; i < getNumberOfBins(); i++) {
        result += m_map_table[i].size();
    }
    return result;
}


int
DirectMapTable::getRegisteredCandidateCt(DataBlock blk) const {
    uint64_t map_index = blockToMap(blk);
    DPRINTF(RubyDirectMapTable, "checking map_index %d for registed candidate\n", map_index);
    return m_map_table[map_index].size();
}

Addr
DirectMapTable::getAnyRandomRegisteredCandidate() {
    assert(hasAnyRegisteredCandidate());
    uint64_t map_index = random_mt.random<unsigned>(0,getNumberOfBins() - 1);
    while (m_map_table[map_index].empty()) {
        map_index = random_mt.random<unsigned>(0,getNumberOfBins() - 1);
    }
    if (m_map_table[map_index].empty()) {
        panic("No candidate in map_index %d\n", map_index);
    }
    DPRINTF(RubyDirectMapTable, "getting any random candidate from map_index %d, size=%d\n", map_index, m_map_table[map_index].size() );
    
    // queue traversal
    int random_index = random_mt.random<unsigned>(0,m_map_table[map_index].size() - 1);
    DPRINTF(RubyDirectMapTable, "random_index=%d\n", random_index);

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
    DPRINTF(RubyDirectMapTable, "after traversal size m_map_table[%d]=%d\n", map_index, m_map_table[map_index].size() );
    directMapTableStats.numMapRandomXOR++;
    return result;
}

Addr
DirectMapTable::getRandomRegisteredCandidate(DataBlock blk) {
    uint64_t map_index = blockToMap(blk);
    DPRINTF(RubyDirectMapTable, "getting random candidate from map_index %d, size=%d\n", map_index, m_map_table[map_index].size());
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
    // directMapTableStats.listCapacityInUse[map_index] -= 1;
    // m_uomap.erase(result);
    DPRINTF(RubyDirectMapTable, "after traversal size m_map_table[%d]=%d\n", map_index, m_map_table[map_index].size() );
    directMapTableStats.numMapCollisionXOR++;
    return result;
}

bool
DirectMapTable::isCandidate(Addr addr) const {
    return m_uomap.find(addr) != m_uomap.end();
}

void
DirectMapTable::profileRead()
{
    directMapTableStats.m_read++;
}

void
DirectMapTable::profileWrite()
{
    directMapTableStats.m_write++;
}

DirectMapTable::
DirectMapTableStats::DirectMapTableStats(statistics::Group *parent, int num_bins)
    : statistics::Group(parent),
      ADD_STAT(numMaxCapcityReached, "Number of max capacity reached"),
      ADD_STAT(listCapacityInUse, statistics::units::Rate<
                statistics::units::Count, statistics::units::Tick>::get(), "listCapacityInUse"),
      ADD_STAT(numMapCollisionXOR, "Number of xor that map to the same index"),
      ADD_STAT(numMapRandomXOR, "Number of xor that is randomly chosen"),
      ADD_STAT(m_read, "Number of read")
{
    numMaxCapcityReached
        .init(num_bins)
        .flags(statistics::total | statistics::nozero | statistics::nonan | statistics::dist | statistics::pdf)
        ;

    listCapacityInUse
        .init(num_bins)
        .flags(statistics::total | statistics::nozero | statistics::nonan | statistics::dist | statistics::pdf)
        ;
    numMapCollisionXOR
        .flags(statistics::nozero);

    numMapRandomXOR
        .flags(statistics::nozero);

    m_read
        .flags(statistics::nozero);
}


} // namespace ruby
} // namespace gem5
