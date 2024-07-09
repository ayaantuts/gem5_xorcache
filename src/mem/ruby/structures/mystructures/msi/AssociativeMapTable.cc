#include "mem/ruby/structures/mystructures/msi/AssociativeMapTable.hh"

#include "base/compiler.hh"
#include "base/intmath.hh"
#include "base/logging.hh"
#include "base/random.hh"
#include "debug/RubyAssociativeMapTable.hh"
#include "debug/RubyDataCluster.hh"
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
    associativeMapTableStats(this, p.num_set)
{
    m_map_bits = p.map_bits;
    // assert(m_map_bits <= 16);
    m_list_capacity = p.list_capacity;
    m_xor_folding_scheme = p.xor_folding_scheme;
    m_xor_policy = p.xor_policy;
    m_num_sets = p.num_set;
    std::cout << "select candidate! From a AssociativeMapTable! map bits=" << m_map_bits << ", num_set"<<
    m_num_sets << std::endl;
    m_block_size = p.block_size;  // may be 0 at this point. Updated in init()
}

void
AssociativeMapTable::init()
{
    if (m_block_size == 0) {
        m_block_size = RubySystem::getBlockSizeBytes();
    }
    m_num_set_bits = floorLog2(m_num_sets);
    assert(m_num_set_bits <= m_map_bits);


    // for (int i = 0; i < (unsigned int)pow(2, m_map_bits); i++) {
    for (int i = 0; i < m_num_sets; i++) {
        m_map_table.push_back(std::queue<Addr>());
        m_map_table_tag.push_back(std::queue<Addr>());
    }
}

AssociativeMapTable::~AssociativeMapTable()
{
    // for (int i = 0; i < (unsigned int)pow(2, m_map_bits); i++) {
    for (int i = 0; i < m_num_sets; i++) {
        while (!m_map_table[i].empty())
        {
            m_map_table[i].pop();
        }
    }
    for (int i = 0; i < m_num_sets; i++) {
        while (!m_map_table_tag[i].empty())
        {
            m_map_table_tag[i].pop();
        }
    }
    m_uomap.clear();
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
int
AssociativeMapTable::getNumberOfSets() const
{
    return m_num_sets;
}

uint64_t
AssociativeMapTable::blockToMap(DataBlock blk) const
{   
    uint64_t hash = blk.xor_folding(blk, m_map_bits, m_block_size, m_xor_folding_scheme);

    // DPRINTF(RubyAssociativeMapTable, "map fingerprint = %d\n", hash);
    return hash;
}
// convert a hash to its location in the map table
int64_t
AssociativeMapTable::mapToSet(uint64_t hash) const
{   
    // DPRINTF(RubyAssociativeMapTable, "map fingerprint = %d, set bits=[%d, %d]\n", hash, 
    //     0, 0 + m_num_set_bits - 1);
    if (m_num_set_bits == 0) {
        return int64_t(0);
    }
    return bitSelect(hash, 0,
                     0 + m_num_set_bits - 1);
}

void 
AssociativeMapTable::insert(Addr addr, DataBlock blk) {
    uint64_t map_index = blockToMap(blk);
    DPRINTF(RubyDataCluster, "<insert> 0x%llx, map_index %d, blk=%s\n", addr, map_index, blk);
    insert_map(addr, map_index);
}

// flow should be first check if replacement will happen, then call probe
// then mauallay evict the probed victim
// final call insert
bool
AssociativeMapTable::willReplacementHappen(Addr addr, DataBlock blk) {
    uint64_t map_index = blockToMap(blk);
    int set = mapToSet(map_index);
    bool found_match = false;
    // Addr match_addr = 0;
    // std::queue<Addr> temp_queue;
    std::queue<Addr> temp_queue_tag;

    // ***** print m_map_table_tag[set], it should not change *****
    DPRINTF(RubyAssociativeMapTable, "willReplacementHappen before: set %d, map_index %d\n", set, map_index);
    for (int i = 0; i < m_map_table_tag[set].size(); i++) {
        Addr tag = m_map_table_tag[set].front();
        m_map_table_tag[set].pop();
        m_map_table_tag[set].push(tag);
        DPRINTF(RubyAssociativeMapTable, "willReplacementHappen before: tag %d\n", tag);
    }

    while (!m_map_table_tag[set].empty()) {
        Addr tag = m_map_table_tag[set].front();
        // Addr addr = m_map_table[set].front();
        m_map_table_tag[set].pop();
        // m_map_table[set].pop();
        if (tag == map_index) {
            DPRINTF(RubyAssociativeMapTable, 
                "willReplacementHappen: map_index %d already in the maptable\n", map_index);
            // take it out first
            found_match = true;
            // match_addr = addr;
            temp_queue_tag.push(tag);
            // temp_queue.push(addr);
        } else {
            temp_queue_tag.push(tag);
            // temp_queue.push(addr);
        }
    }

    // restore the original queue
    m_map_table_tag[set] = temp_queue_tag;

    // ***** print m_map_table_tag[set], it should not change *****
    DPRINTF(RubyAssociativeMapTable, "willReplacementHappen after: set %d, map_index %d\n", set, map_index);
    for (int i = 0; i < m_map_table_tag[set].size(); i++) {
        Addr tag = m_map_table_tag[set].front();
        m_map_table_tag[set].pop();
        m_map_table_tag[set].push(tag);
        DPRINTF(RubyAssociativeMapTable, "willReplacementHappen after: tag %d\n", tag);
    }

    // m_map_table[set] = temp_queue;
    if (found_match) {
        DPRINTF(RubyAssociativeMapTable, "willReplacementHappen(%d) eval to true due to hit\n", map_index);
        return true; // because we hits
    }
    // m_map_table[set].push(addr);
    // m_map_table_tag[set].push(map_index);
    // m_uomap[addr] = map_index;
    // associativeMapTableStats.listCapacityInUse[set] += 1;
    if (m_map_table[set].size() == m_list_capacity) {
        DPRINTF(RubyAssociativeMapTable, "willReplacementHappen(%d) eval to true due to full\n", map_index);
        return true;
    }
    return false;
}

Addr
AssociativeMapTable::insertion_probe(Addr addr, DataBlock blk) {
    uint64_t map_index = blockToMap(blk);
    int set = mapToSet(map_index);
    bool found_match = false;
    Addr match_addr = 0;
    std::queue<Addr> temp_queue;
    std::queue<Addr> temp_queue_tag;

    // ***** print m_map_table_tag[set], it should not change *****
    DPRINTF(RubyAssociativeMapTable, "insertion_probe before: set %d, map_index %d\n", set, map_index);
    for (int i = 0; i < m_map_table_tag[set].size(); i++) {
        Addr tag = m_map_table_tag[set].front();
        m_map_table_tag[set].pop();
        m_map_table_tag[set].push(tag);
        DPRINTF(RubyAssociativeMapTable, "insertion_probe before: tag %d\n", tag);
    }

    while (!m_map_table_tag[set].empty()) {
        Addr tag = m_map_table_tag[set].front();
        Addr addr = m_map_table[set].front();
        m_map_table_tag[set].pop();
        m_map_table[set].pop();
        if (tag == map_index) {
            DPRINTF(RubyAssociativeMapTable, 
                "insertion_probe: map_index %d already in the maptable\n", map_index);
            // take it out first
            found_match = true;
            match_addr = addr;
            temp_queue_tag.push(tag);
            temp_queue.push(addr);
        } else {
            DPRINTF(RubyAssociativeMapTable, 
                "insertion_probe: tag under compare %d != search key map %d\n", tag, map_index);
            temp_queue_tag.push(tag);
            temp_queue.push(addr);
        }
    }

    // restore the original queue
    m_map_table_tag[set] = temp_queue_tag;
    m_map_table[set] = temp_queue;
    if (found_match) {
        return match_addr;
    }
    // m_map_table[set].push(addr);
    // m_map_table_tag[set].push(map_index);
    // m_uomap[addr] = map_index;
    // associativeMapTableStats.listCapacityInUse[set] += 1;
    if (m_map_table[set].size() == m_list_capacity) {
        Addr victim = m_map_table[set].front();
        DPRINTF(RubyAssociativeMapTable, "<probe> victim 0x%llx, set %d\n", victim, set);
        associativeMapTableStats.numMaxCapcityReached[set]++;
        return victim;
    }
    panic("insertion_probe: set %d not full yet, cap=%d\n", set, m_map_table[set].size());
}

void 
AssociativeMapTable::insert_map(Addr addr, uint64_t map_index) {
    int set = mapToSet(map_index);
    DPRINTF(RubyAssociativeMapTable, "<insert> 0x%llx, map_index %d, set %d\n", addr, map_index, set);
    // check tag first if map_index not in the maptable, then add it
    // read each element out and then put it back

    bool found_match = false;
    Addr match_addr = 0;
    std::queue<Addr> temp_queue;
    std::queue<Addr> temp_queue_tag;
    while (!m_map_table_tag[set].empty()) {
        Addr tag = m_map_table_tag[set].front();
        Addr addr = m_map_table[set].front();
        m_map_table_tag[set].pop();
        m_map_table[set].pop();
        if (tag == map_index) {
            // DPRINTF(RubyAssociativeMapTable, 
            //     "map_index %d already in the maptable\n", map_index);
            // take it out first
            found_match = true;
            match_addr = addr;
            temp_queue_tag.push(tag);
            temp_queue.push(addr);
        } else {
            temp_queue_tag.push(tag);
            temp_queue.push(addr);
        }
    }

    // restore the original queue
    m_map_table_tag[set] = temp_queue_tag;
    m_map_table[set] = temp_queue;
    if (found_match) {
        remove(match_addr);
        DPRINTF(RubyAssociativeMapTable, "<insert> map_index %d (0x%llx) already in the maptable, removed\n", 
            map_index, match_addr);
    }

    m_map_table[set].push(addr);
    m_map_table_tag[set].push(map_index);
    m_uomap[addr] = map_index;
    associativeMapTableStats.listCapacityInUse[set] += 1;
    if (m_map_table[set].size() > m_list_capacity) {
        panic("insert: set %d exceeds capacity %d, should have caught by probing\n", set, m_map_table[set].size());
    }
}


uint64_t
AssociativeMapTable::remove_return(Addr addr) {
    if (m_uomap.find(addr) == m_uomap.end()) {
        panic("remove_return: no match\n");
    }
    uint64_t map_index = m_uomap[addr];
    remove(addr);
    return map_index;
}

void
AssociativeMapTable::remove(Addr addr) {
    if (m_uomap.find(addr) == m_uomap.end()) {
        DPRINTF(RubyAssociativeMapTable, "<remove> 0x%llx no match\n", addr);
        return;
    }
    uint64_t map_index = m_uomap[addr];
    int set = mapToSet(map_index);
    int found = 0;
    DPRINTF(RubyAssociativeMapTable, "<remove> 0x%llx, map_index %d, set %d\n", addr, map_index,set);
    std::queue<Addr> temp_queue;
    std::queue<Addr> temp_queue_tag;
    while (!m_map_table[set].empty()) {
        Addr temp_addr = m_map_table[set].front();
        Addr temp_tag = m_map_table_tag[set].front();
        if (temp_addr != addr) {
            temp_queue.push(temp_addr);
            temp_queue_tag.push(temp_tag);
        } else {
            found += 1;
        }
        m_map_table[set].pop();
        m_map_table_tag[set].pop();
    }
    while (!temp_queue.empty()) {
        m_map_table[set].push(temp_queue.front());
        m_map_table_tag[set].push(temp_queue_tag.front());
        temp_queue.pop();
        temp_queue_tag.pop();
    }
    if (found == 1) {
        associativeMapTableStats.listCapacityInUse[set] -= 1;
    } else if (found == 0) {
        DPRINTF(RubyAssociativeMapTable, "<remove> no match\n");
    } else {
        panic("more than one match\n");
    }
    m_uomap.erase(addr);
}


bool
AssociativeMapTable::hasRegisteredCandidate(DataBlock blk) {
    uint64_t map_index = blockToMap(blk);
    int set = mapToSet(map_index);
    DPRINTF(RubyAssociativeMapTable, "checking map_index %d for registed candidate\n", map_index);
    if (m_map_table[set].empty()) {
        return false;
    } else {
        // still need to check tag
        bool found_match = false;
        std::queue<Addr> temp_queue;
        while (!m_map_table_tag[set].empty()) {
            Addr tag = m_map_table_tag[set].front();
            m_map_table_tag[set].pop();
            if (tag == map_index) {
                found_match = true;
                temp_queue.push(tag);
            } else {
                temp_queue.push(tag);
            }
        }

        // restore the original queue
        m_map_table_tag[set] = temp_queue;
        if (found_match) {
            return true;
        }
    }
    return false;
}

bool
AssociativeMapTable::hasAnyRegisteredCandidate() const {
    for (int i = 0; i < getNumberOfSets(); i++) {
        if (!m_map_table[i].empty()) {
            return true;
        }
    }
    return false;
}

int
AssociativeMapTable::getAnyRegisteredCandidateCt() const {
    int result = 0;
    for (int i = 0; i < getNumberOfSets(); i++) {
        result += m_map_table[i].size();
    }
    return result;
}


int
AssociativeMapTable::getRegisteredCandidateCt(DataBlock blk) {
    if (!hasRegisteredCandidate(blk)) {
        return 0;
    } else {
        return 1;
    }
}

Addr
AssociativeMapTable::getAnyRandomRegisteredCandidate() {
    assert(hasAnyRegisteredCandidate());
    uint64_t map_index = random_mt.random<unsigned>(0,getNumberOfBins() - 1);
    int set = mapToSet(map_index);
    while (m_map_table[set].empty()) {
        map_index = random_mt.random<unsigned>(0,getNumberOfBins() - 1);
        set = mapToSet(map_index);
    }
    if (m_map_table[set].empty()) {
        panic("No candidate in map_index %d\n", map_index);
    }
    DPRINTF(RubyAssociativeMapTable, "getting any random candidate from map_index %d, set %d, size=%d\n", map_index, set, m_map_table[set].size() );
    
    // queue traversal
    int random_index = random_mt.random<unsigned>(0,m_map_table[set].size() - 1);
    DPRINTF(RubyAssociativeMapTable, "random_index=%d\n", random_index);

    std::queue<Addr> temp_queue;
    std::queue<Addr> temp_queue_tag;
    Addr result_addr = 0;
    Addr result_tag = 0;
    while (!m_map_table[set].empty()) {
        Addr temp_addr = m_map_table[set].front();
        Addr temp_tag = m_map_table_tag[set].front();
        if (random_index == 0) {
            result_addr = temp_addr;
            result_tag = temp_tag;
            temp_queue.push(temp_addr);
            temp_queue_tag.push(temp_tag);
        } else {
            temp_queue.push(temp_addr);
            temp_queue_tag.push(temp_tag);
        }
        m_map_table[set].pop();
        m_map_table_tag[set].pop();
        random_index--;
    }
    while (!temp_queue.empty()) {
        m_map_table[set].push(temp_queue.front());
        m_map_table_tag[set].push(temp_queue_tag.front());
        temp_queue.pop();
        temp_queue_tag.pop();
    }
    DPRINTF(RubyAssociativeMapTable, "after traversal size m_map_table[%d]=%d\n", set, m_map_table[set].size() );
    DPRINTF(RubyAssociativeMapTable, "selected addr=%llx, selected hash=%d\n",result_addr, result_tag );
    associativeMapTableStats.numMapRandomXOR++;
    return result_addr;
}

Addr
AssociativeMapTable::getRandomRegisteredCandidate(DataBlock blk) {
    // actually, this is not random as only one will match!
    uint64_t map_index = blockToMap(blk);
    int set = mapToSet(map_index);
    DPRINTF(RubyAssociativeMapTable, "getting random candidate from map_index %d, set %d, size=%d\n", map_index, set, m_map_table[set].size());
    if (m_map_table[set].empty()) {
        panic("No candidate in map_index %d, set %d\n", map_index, set);
    }
    // int random_index = random_mt.random<unsigned>(0,m_map_table[set].size() - 1);
    
    // queue traversal

    std::queue<Addr> temp_queue;
    std::queue<Addr> temp_queue_tag;
    Addr result = 0;
    bool found_match = false;
    while (!m_map_table[set].empty()) {
        Addr temp_addr = m_map_table[set].front();
        Addr temp_tag = m_map_table_tag[set].front();
        if (temp_tag == map_index) {
            result = temp_addr;
            temp_queue.push(temp_addr);
            temp_queue_tag.push(temp_tag);
            found_match = true;
        } else {
            temp_queue.push(temp_addr);
            temp_queue_tag.push(temp_tag);
        }
        m_map_table[set].pop();
        m_map_table_tag[set].pop();
    }
    DPRINTF(RubyAssociativeMapTable, "found_match=%d\n", found_match);
    assert(found_match);
    while (!temp_queue.empty()) {
        m_map_table[set].push(temp_queue.front());
        m_map_table_tag[set].push(temp_queue_tag.front());
        temp_queue.pop();
        temp_queue_tag.pop();
    }
    // associativeMapTableStats.listCapacityInUse[map_index] -= 1;
    // m_uomap.erase(result);
    DPRINTF(RubyAssociativeMapTable, "after traversal size m_map_table[%d]=%d\n", set, m_map_table[set].size() );
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
AssociativeMapTableStats::AssociativeMapTableStats(statistics::Group *parent, int num_bins)
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
