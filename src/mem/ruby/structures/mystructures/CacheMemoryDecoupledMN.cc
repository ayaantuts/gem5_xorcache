#include "debug/RubyCacheDecoupledMN.hh"
#include "mem/ruby/structures/mystructures/CacheMemoryDecoupledMN.hh"
#include "mem/ruby/system/RubySystem.hh"

#include <iostream>

namespace gem5
{

namespace ruby
{

CacheMemoryDecoupledMN::CacheMemoryDecoupledMN(const Params &p)
    : CacheMemoryDecoupled(p),
    cacheMemoryDecoupledMNStats(this)
{
    m_num_hash_bucket = p.numHashBucket;
    m_chain_length = p.chainLength;
    m_hashTable_partialHash_length = p.partialHashLength; // num tag bits for hash table
    m_replacementPolicy_ptr_hashTable = p.replacement_policy_hashTable;
    std::cout << "Hello World flex! From a CacheMemoryDecoupledMN! "<<m_num_seg_per_set <<
        " segs per set; HT(" << m_num_hash_bucket << "x" << m_chain_length << ")" <<std::endl;
    
}

void
CacheMemoryDecoupledMN::init()
{
    CacheMemoryDecoupled::init();
    std::cout << "CacheMemoryDecoupledMN::m_cache_num_sets=" << m_cache_num_sets << std::endl;
    assert(m_data_array_assoc == 1); // data array has to be fully associative
    // std::cout << "m_data_num_set_bits="<<m_data_num_set_bits <<std::endl;

    // partial hash bits
    m_hashTable_num_set_bits = floorLog2(m_num_hash_bucket);
    assert(m_hashTable_num_set_bits > 0);
    std::cout << "m_hashTable_num_set_bits="<<m_hashTable_num_set_bits <<std::endl;
    

    m_cache_hashTable.resize(m_num_hash_bucket,
                    std::vector<HashTableEntry*>(m_chain_length, nullptr));
    replacement_data_hashTable.resize(m_num_hash_bucket,
                               std::vector<ReplData>(m_chain_length, nullptr));

    m_tag_hashTable_ptr.resize(m_cache_num_sets,
                    std::vector<uint32_t>(m_cache_assoc, 0));
    m_tag_hashTable_ptr_valid.resize(m_cache_num_sets,
                    std::vector<bool>(m_cache_assoc, false));
    m_hashTable_index.resize(m_num_hash_bucket,
                    std::unordered_map<uint32_t, int>());
    
    // instantiate all the replacement_data here
    for (int i = 0; i < m_num_hash_bucket; i++) {
        for ( int j = 0; j < m_chain_length; j++) {
            replacement_data_hashTable[i][j] =
                                m_replacementPolicy_ptr_hashTable->instantiateEntry();
        }
    }
}

CacheMemoryDecoupledMN::~CacheMemoryDecoupledMN()
{
    if (m_replacementPolicy_ptr_hashTable)
        delete m_replacementPolicy_ptr_hashTable;
    for (int i = 0; i < m_num_hash_bucket; i++) {
        for (int j = 0; j < m_chain_length; j++) {
            delete m_cache_hashTable[i][j];
        }
        m_hashTable_index[i].clear();
    }
    m_tag_hashTable_ptr.clear();
    m_tag_hashTable_ptr_valid.clear();
}

/* convert a Address to its location in the cache. if this dataset does not have 
enough vacancy, select first free set.
Note: make sure there is at least one set has enough vacancy!*/
int64_t
CacheMemoryDecoupledMN::addressToCacheSetData(Addr address, int data_size)
{
    assert(address == makeLineAddress(address));
    int num_seg_per_data = divCeil(data_size,m_segment_size);
    int64_t set_default = bitSelect(address, m_start_index_bit,
                     m_start_index_bit + m_data_num_set_bits - 1);
    if (m_data_set_vacancy[set_default] < num_seg_per_data) {
        for (int64_t i = 0; i < m_data_array_set; i++) {
            if (m_data_set_vacancy[i] >= num_seg_per_data) {
                cacheMemoryDecoupledMNStats.numDataSetMisplace++;
                return i;
            }
        }
    }
    else {
        cacheMemoryDecoupledMNStats.numDataSetDefaultPlacement++;
        return set_default;
    }
    panic("no set has enough segments!");
}

// convert a 32 bit hash to its set in HashTable
int64_t
CacheMemoryDecoupledMN::hashToHashTableSet(uint32_t hash) const
{
    // DPRINTF(RubyCacheDecoupledMN, "hashToHashTableSet() in CacheMemoryDecoupledMN\n");
    // lower m_hashTable_num_set_bits bits
    Addr hash_cast = Addr(hash);
    return bitSelect(hash_cast, 0, m_hashTable_num_set_bits-1);
}

uint32_t
CacheMemoryDecoupledMN::hashToHashTablePartialTag(uint32_t hash) const
{
    // DPRINTF(RubyCacheDecoupledMN, "hashToHashTablePartialTag() in CacheMemoryDecoupledMN\n");
    // middle m_hashTable_partialHash_length bits
    assert(m_hashTable_num_set_bits+m_hashTable_partialHash_length <= 32);
    Addr hash_cast = Addr(hash);
    return uint32_t(bitSelect(hash_cast, m_hashTable_num_set_bits, 
        m_hashTable_num_set_bits+m_hashTable_partialHash_length-1));
}

int
CacheMemoryDecoupledMN::findTagInSetHashTable(int64_t hashSet, Addr hashTag) const
{
    DPRINTF(RubyCacheDecoupledMN, "findTagInSetHashTable() in CacheMemoryDecoupledMN\n");
    // search the set for the tags
    auto it = m_hashTable_index[hashSet].find(hashTag);
    if (it != m_hashTable_index[hashSet].end()) {
        DPRINTF(RubyCacheDecoupledMN, "findTagInSetHashTable returning %d\n", it->second);
        return it->second;
    }
    DPRINTF(RubyCacheDecoupledMN, "findTagInSetHashTable returning -1\n");
    return -1; // Not found
}

// looks a hash up in the hashtable if present, else return null
HashTableEntry*
CacheMemoryDecoupledMN::lookupHash(uint32_t hash) const
{
    DPRINTF(RubyCacheDecoupledMN, "lookupHash() in CacheMemoryDecoupledMN\n");
    // std::cout << "hash=" <<
    //         std::setw(2) << std::setfill('0') << std::hex << "0x" <<
    //         uint32_t(hash)
    //         << " " << std::setfill(' ')<< std::dec << std::endl;
    int64_t hashSet = hashToHashTableSet(hash);
    // DPRINTF(RubyCacheDecoupledMN, "1.hash to hash set %d\n", hashSet);
    uint32_t hashTag = hashToHashTablePartialTag(hash);
    // std::cout << "hashTag=" <<
    //         std::setw(2) << std::setfill('0') << std::hex << "0x" <<
    //         uint32_t(hashTag)
    //         << " " << std::setfill(' ')<< std::dec << std::endl;
    int loc = findTagInSetHashTable(hashSet, hashTag);
    if (loc == -1) {
        DPRINTF(RubyCacheDecoupledMN, "lookupHash() returning null\n");
        return nullptr;
    }
    assert(m_cache_hashTable[hashSet][loc]!=nullptr);
    DPRINTF(RubyCacheDecoupledMN, "lookupHash returning HT[%d,%d]\n", hashSet,loc);
    return m_cache_hashTable[hashSet][loc];
}

/* returns true if there is space in ht or this hash already exist in ht */
bool
CacheMemoryDecoupledMN::hashTableAvail(uint32_t hash) const
{
    int64_t hashSet = hashToHashTableSet(hash);

    for (int i = 0; i < m_chain_length; i++) {
        HashTableEntry* entry = m_cache_hashTable[hashSet][i];
        if (entry != NULL) {
            // if (entry->m_partial_hash == hashToHashTablePartialTag(hash)) {
            //     // as long as partial hash matches
            //     return true;
            // }
        } else {
            return true;
        }
    }
    return false;
}

// returns conflicting hash table entry
HashTableEntry*
CacheMemoryDecoupledMN::hashTableProbe(uint32_t hash) const
{
    assert(!hashTableAvail(hash));

    int64_t hashSet = hashToHashTableSet(hash);
    std::vector<ReplaceableEntry*> candidates;
    for (int i = 0; i < m_chain_length; i++) {
        candidates.push_back(static_cast<ReplaceableEntry*>(
                                                       m_cache_hashTable[hashSet][i]));
    }
    assert(candidates.size() > 0);
    return m_cache_hashTable[hashSet][m_replacementPolicy_ptr_hashTable->
                        getVictim(candidates)->getWay()];
}

// if present in hashtable return dataset, else return -1
int64_t
CacheMemoryDecoupledMN::hashToDataSet_noInsert(uint32_t hash) const
{
    HashTableEntry* hashEntry = lookupHash(hash);
    int64_t dataSet_from_hashTable = -1;
    if (hashEntry != nullptr) {
        dataSet_from_hashTable = hashEntry->m_dataSet;
        std::cout << "  hashToDataSet_noInsert():present in hash table, dataset=" << dataSet_from_hashTable << std::endl;
    }
    else {
        std::cout << "  hashToDataSet_noInsert():miss, ret dataset=" << dataSet_from_hashTable << std::endl;
    }
    return dataSet_from_hashTable;
}

void
CacheMemoryDecoupledMN::linkDataToTag(Addr address, AbstractCacheEntry* new_dataEntry, int data_size, uint32_t hash) {
    DPRINTF(RubyCacheDecoupledMN, "=====linkDataToTag() in CacheMemoryDecoupledMN=====\n");
    int num_seg_per_data = divCeil(data_size,m_segment_size);
    DPRINTF(RubyCacheDecoupledMN, "0.linkDataToTag:data_size=%dB, equivalent to %d segment\n", data_size, num_seg_per_data);
    
    assert(address == makeLineAddress(address));
    assert(CacheMemory::isTagPresent(address));
    // assert(cacheCanCoallocate(address, data_size));
    DPRINTF(RubyCacheDecoupledMN, "   1.address: %#x data filing...\n", address);
    
    //lookup tag
    AbstractCacheEntry* tagEntry = lookup(address);
    assert(tagEntry != nullptr);
    int tagSet = tagEntry->getSet();
    int tagWay = tagEntry->getWay();
    assert(m_cache[tagSet][tagWay]->m_Address == address);
    assert(m_tag_hashTable_ptr_valid[tagSet][tagWay] == false);

    // calculate data set
    int64_t dataSet_new = addressToCacheSetData(address,data_size);
    int free = m_data_set_vacancy[dataSet_new];
    if (free >= num_seg_per_data) {
        DPRINTF(RubyCacheDecoupledMN, "   2.tag[%d,%d] will be linked to %d segments in data[%d]\n", 
            tagSet, tagWay, num_seg_per_data,dataSet_new);
    }
    else {
        assert(false);
    }
    // ************ hash table operations *************
    // look up hash table
    // std::cout << "hash=" <<
    //     std::setw(2) << std::setfill('0') << std::hex << "0x" <<
    //     uint32_t(hash)
    //     << " " << std::setfill(' ')<< std::dec << std::endl;
    int seg = findDuplicatedDatasTagWay(hash);
    // assert (seg == -1);
    if (seg == -1) {
        DPRINTF(RubyCacheDecoupledMN, " 3.ht miss\n");
        cacheMemoryDecoupledMNStats.numHashTableMiss++;
    }
    else {
        DPRINTF(RubyCacheDecoupledMN, " 3.ht hit but data does not match\n");
        cacheMemoryDecoupledMNStats.numHashTableHit++;
        cacheMemoryDecoupledMNStats.numHashCollision++;
    }
    uint32_t phash = hashToHashTablePartialTag(hash);

    // ht miss
    if (hashTableAvail(hash) == false) {
        // no space => replace
        cacheMemoryDecoupledMNStats.numHashTableEntryReplacement++;
        DPRINTF(RubyCacheDecoupledMN, " 4.ht no space avail => ht replacing\n");
        HashTableEntry* victimHTE = hashTableProbe(hash);
        DPRINTF(RubyCacheDecoupledMN, "      4a.victim is at hash[%d,%d]\n",victimHTE->getSet(),victimHTE->getWay());
        m_replacementPolicy_ptr_hashTable->invalidate(victimHTE->replacementData);
        DPRINTF(RubyCacheDecoupledMN, "      4b.invalidated victimHTE's repl data\n", victimHTE->getSet());
        m_cache_hashTable[victimHTE->getSet()][victimHTE->getWay()] = nullptr;
        DPRINTF(RubyCacheDecoupledMN, "      4c.removed victimHTE from hashtable data structure\n");
        m_hashTable_index[victimHTE->getSet()].erase(phash);
        DPRINTF(RubyCacheDecoupledMN, "      4d.erased partialhash from m_hashTable_index[%d]\n", victimHTE->getSet());
        cacheMemoryDecoupledMNStats.numHashTableEntryInUse--;

        delete victimHTE;
        DPRINTF(RubyCacheDecoupledMN, "      4e.deleted victimHTE\n");
        assert(hashTableAvail(hash));
    }
    // there is space => add entry
    DPRINTF(RubyCacheDecoupledMN, " 4.ht space avail now\n");
    int64_t hashSet = hashToHashTableSet(hash);
    DPRINTF(RubyCacheDecoupledMN, " 5.=> adding a new ht entry in ht set %d\n",hashSet);
    bool found_free_space = false;
    for (int i = 0; i < m_chain_length; i++) {
        if (!m_cache_hashTable[hashSet][i]) {
            m_cache_hashTable[hashSet][i] = new HashTableEntry;
            m_cache_hashTable[hashSet][i]->m_partial_hash = phash;
            m_cache_hashTable[hashSet][i]->m_dataSet = dataSet_new;
            m_cache_hashTable[hashSet][i]->setPosition(hashSet, i);
            // std::cout << "      4a.added partialhash to hashtable[" << hashSet << "," << i << "]" << std::endl;
            DPRINTF(RubyCacheDecoupledMN, "      5a.added partialhash to hashtable[%d,%d]\n",hashSet,i);
            m_hashTable_index[hashSet][phash] = i;
            m_cache_hashTable[hashSet][i]->replacementData = replacement_data_hashTable[hashSet][i];
            m_cache_hashTable[hashSet][i]->setLastAccess(curTick());
            m_replacementPolicy_ptr_hashTable->reset(m_cache_hashTable[hashSet][i]->replacementData);
            cacheMemoryDecoupledMNStats.numHashTableEntryInUse++;
            found_free_space = true;
            // std::cout << "      4b.dataset=" <<  m_cache_hashTable[hashSet][i]->m_dataSet << std::endl;
            DPRINTF(RubyCacheDecoupledMN, "      5b.dataset=%d\n",m_cache_hashTable[hashSet][i]->m_dataSet);

            // set up tag hashtable pointers
            m_tag_hashTable_ptr_valid[tagSet][tagWay] = true;
            m_tag_hashTable_ptr[tagSet][tagWay] = hash;
            break;
        }
    }
    if (!found_free_space) panic("Didn't find an available hash table entry");
    
    
    // ************ data array operations *************
    // set up tag data link
    new_dataEntry->setLastAccess(curTick());
    m_tag_data_ptr[tagSet][tagWay] = new_dataEntry; //tag to data

    for (int j = 0; j < m_num_seg_per_set; j++) {
        if (m_cache_data[dataSet_new][j] == NULL) {
            DPRINTF(RubyCacheDecoupledMN, " 6.tag[%d,%d] linking to data[%d,%d]\n", 
            tagSet, tagWay, dataSet_new, j);
            m_cache_data[dataSet_new][j] = new_dataEntry;  // Init entry
            DPRINTF(RubyCacheDecoupledMN, "   6a.data[%d,%d] added to data structure\n", dataSet_new, j);
            m_tag_seg_cntr[tagSet][tagWay] += num_seg_per_data;
            DPRINTF(RubyCacheDecoupledMN, "   6b.tag[%d,%d] segment counter set to %d\n", tagSet, tagWay,m_tag_seg_cntr[tagSet][tagWay]);
            m_data_head_tag_ptr[dataSet_new][j] = m_cache[tagSet][tagWay]; //data to tag head
            assert(m_cache[tagSet][tagWay] != nullptr);
            DPRINTF(RubyCacheDecoupledMN, "   6c.data[%d,%d] rev pointer is set to head tag[%d,%d]\n",dataSet_new, j, tagSet, tagWay);
            m_data_cntr[dataSet_new][j] += 1;
            assert(m_data_cntr[dataSet_new][j] <= 1);
            DPRINTF(RubyCacheDecoupledMN, "   6d.data[%d,%d] pointer counter is set to %d\n",dataSet_new, j, m_data_cntr[dataSet_new][j]);
            m_data_set_vacancy[dataSet_new] -= num_seg_per_data;
            DPRINTF(RubyCacheDecoupledMN, "   6e.data[%d] vacancy is set to %d\n",dataSet_new,m_data_set_vacancy[dataSet_new]);
            new_dataEntry->replacementData = replacement_data_for_data[dataSet_new][j];
            m_replacementPolicy_ptr_data->reset(new_dataEntry->replacementData);
            DPRINTF(RubyCacheDecoupledMN, "   6f.assigning and reseting data's repl data\n");
            m_data_index[address] = j;
            DPRINTF(RubyCacheDecoupledMN, "   6g.m_data_index[%#x]=%d\n",address,j);

            new_dataEntry->setPosition(dataSet_new, j);
            DPRINTF(RubyCacheDecoupledMN, "   6h.data[%d,%d] set position\n",dataSet_new, j);

            cacheMemoryDecoupledStats.numSegInUse += num_seg_per_data;
            DPRINTF(RubyCacheDecoupledMN, "   6i.segment in use increase by %d\n",num_seg_per_data);
            return;
        }
    }
    panic("linkDataToTag didn't find an available entry");
}

void
CacheMemoryDecoupledMN::linkDataToTag_dedup(Addr address, int data_size, uint32_t hash) {
    DPRINTF(RubyCacheDecoupledMN, "======linkDataToTag_dedup() in CacheMemoryDecoupledMN=====\n");
    int num_seg_per_data = divCeil(data_size,m_segment_size);
    DPRINTF(RubyCacheDecoupledMN, "0.linkDataToTag_dedup:data_size=%dB, equivalent to %d segment\n", data_size, num_seg_per_data);
    // std::cout << "linkDataToTag:data size=" << data_size << ", equivalent to " << num_seg_per_data << " segs." <<std::endl;

    assert(address == makeLineAddress(address));
    assert(CacheMemory::isTagPresent(address));
    // assert(cacheAvailData(address, data_size));
    DPRINTF(RubyCacheDecoupledMN, "   1.address: %#x data filing...\n", address);
    
    //lookup tag
    AbstractCacheEntry* tagEntry = lookup(address);
    assert(tagEntry != nullptr);
    int tagSet = tagEntry->getSet();
    int tagWay = tagEntry->getWay();
    assert(m_cache[tagSet][tagWay]->m_Address == address);
    assert(m_tag_hashTable_ptr_valid[tagSet][tagWay] == false);

    // look up hash table
    // std::cout << "hash=" <<
    //     std::setw(2) << std::setfill('0') << std::hex << "0x" <<
    //     uint32_t(hash)
    //     << " " << std::setfill(' ')<< std::dec << std::endl;
    
    int seg = findDuplicatedDatasTagWay(hash);
    assert(seg != -1);
    Addr collision_head_address = findDuplicatedDatasTagAddr(hash, seg);
    cacheMemoryDecoupledMNStats.numHashTableHit++;

    assert(lookupHash(hash));
    m_replacementPolicy_ptr_hashTable->touch(lookupHash(hash)->replacementData);
    DPRINTF(RubyCacheDecoupledMN, " 2.touched ht[%d,%d] repl data\n",lookupHash(hash)->getSet(), lookupHash(hash)->getWay());

    DPRINTF(RubyCacheDecoupledMN, " 3.address collision=%#x\n",collision_head_address);
    // we know this is true collision!
    AbstractCacheEntry* tagEntry_collision = lookup(collision_head_address);
    assert(tagEntry_collision != nullptr);
    int tagSet_collision = tagEntry_collision->getSet();
    int tagWay_collision = tagEntry_collision->getWay();
    DPRINTF(RubyCacheDecoupledMN, "   4.tag[%d,%d] has same data as tag[%d,%d]?\n", 
            tagSet, tagWay, tagSet_collision,tagWay_collision);
    assert(m_tag_seg_cntr[tagSet_collision][tagWay_collision] > 0);
    DPRINTF(RubyCacheDecoupledMN, "   5.tag[%d,%d] has same data as tag[%d,%d]\n", 
            tagSet, tagWay, tagSet_collision,tagWay_collision);
    // calculate data set
    AbstractCacheEntry* dataEntry_collision = m_tag_data_ptr[tagSet_collision][tagWay_collision];
    assert(dataEntry_collision != nullptr);
    int dataSet_new = dataEntry_collision->getSet();
    int dataSeg_new = dataEntry_collision->getWay();
    
    // set up tag data link
    DPRINTF(RubyCacheDecoupledMN, "   6.tag[%d,%d] linking to data[%d,%d]\n", 
    tagSet, tagWay, dataSet_new, dataSeg_new);
    m_replacementPolicy_ptr_data->touch(dataEntry_collision->replacementData);
    dataEntry_collision->setLastAccess(curTick());
    DPRINTF(RubyCacheDecoupledMN, "   6a.data[%d,%d] repl touch\n", dataSet_new, dataSeg_new);

    // tag to data
    m_tag_data_ptr[tagSet][tagWay] = dataEntry_collision; //tag to data
    DPRINTF(RubyCacheDecoupledMN, "   6b.settup tag to data pointer\n");
    m_tag_seg_cntr[tagSet][tagWay] += num_seg_per_data;
    DPRINTF(RubyCacheDecoupledMN, "   6c.tag seg cntr increase by %d, now is %d\n",
        num_seg_per_data, m_tag_seg_cntr[tagSet][tagWay]);
    //tag internal
    AbstractCacheEntry* tagHead = m_data_head_tag_ptr[dataSet_new][dataSeg_new];
    assert(tagHead != nullptr);
    DPRINTF(RubyCacheDecoupledMN, "   6d.tag head is tag[%d,%d]\n",tagHead->getSet(),tagHead->getWay());
    addToTail(tagHead, tagEntry);
    DPRINTF(RubyCacheDecoupledMN, "   6e.tag is added to tail of tag list\n");
    //tag to hash
    m_tag_hashTable_ptr_valid[tagSet][tagWay] = true;
    m_tag_hashTable_ptr[tagSet][tagWay] = hash;
    DPRINTF(RubyCacheDecoupledMN, "   6f.m_tag_hashTable_ptr now valid\n");
    // data
    m_data_cntr[dataSet_new][dataSeg_new] += 1;
    assert(m_data_cntr[dataSet_new][dataSeg_new] > 1);
    DPRINTF(RubyCacheDecoupledMN, "   6g.m_data_cntr incremented by 1, now %d\n",m_data_cntr[dataSet_new][dataSeg_new]);

}

void
CacheMemoryDecoupledMN::unlinkDataToTag(Addr address) {
    DPRINTF(RubyCacheDecoupledMN, "=====unlinkDataToTag() in CacheMemoryDecoupled: %#x=====\n", address);
    AbstractCacheEntry* tagEntry = lookup(address);
    assert(tagEntry != nullptr);
    uint32_t tagSet = tagEntry->getSet();
    uint32_t tagWay = tagEntry->getWay();
    AbstractCacheEntry* dataEntry = m_tag_data_ptr[tagSet][tagWay];
    assert(dataEntry != NULL);
    
    //locate data entry's index
    uint32_t dataSet = dataEntry->getSet();
    uint32_t dataSeg = dataEntry->getWay();
    assert(dataSeg < m_num_seg_per_set);
    AbstractCacheEntry* tagHeadEntry = m_data_head_tag_ptr[dataSet][dataSeg];

    DPRINTF(RubyCacheDecoupledMN, "  0.data is at [%d,%d]\n", dataSet, dataSeg);

    if (m_data_cntr[dataSet][dataSeg] == 1) {
        DPRINTF(RubyCacheDecoupledMN, "  2.no tag points to this data, deallocating...\n");
        //reset data's replacement data
        m_replacementPolicy_ptr_data->invalidate(dataEntry->replacementData);
        DPRINTF(RubyCacheDecoupledMN, "  2a.invalidated data repl\n");
        //delete data entry
        delete dataEntry;
        DPRINTF(RubyCacheDecoupledMN, "  2b.deleted data entry\n");
        //reset ptrs
        m_data_set_vacancy[dataSet] += m_tag_seg_cntr[tagSet][tagWay]; // now vacant
        DPRINTF(RubyCacheDecoupledMN, "  2c.freed up %d segs in data[%d]\n", 
            m_tag_seg_cntr[tagSet][tagWay], dataSet);
        m_cache_data[dataSet][dataSeg] = NULL;
        DPRINTF(RubyCacheDecoupledMN, "  2d.m_cache_data data structure cleared.\n");
        int seg_cntr = m_tag_seg_cntr[tagSet][tagWay];
        m_data_head_tag_ptr[dataSet][dataSeg] = NULL;
        DPRINTF(RubyCacheDecoupledMN, "  2e.data[%d,%d] to tag head cleared.\n",dataSet,dataSeg);
        cacheMemoryDecoupledStats.numSegInUse -= seg_cntr;
        DPRINTF(RubyCacheDecoupledMN, "  2f. decrementing data seg in use.\n");
    }
    else {
        DPRINTF(RubyCacheDecoupledMN, "  2.other tag still points to this data\n");
        DPRINTF(RubyCacheDecoupledMN, "  2a.remove tag[%d,%d] from its tag list\n", tagSet,tagWay);
        removeFromList(tagHeadEntry, tagEntry);
    }
    DPRINTF(RubyCacheDecoupledMN, "  3a.erasing address to data seg mapping\n");
    m_data_index.erase(address);
    DPRINTF(RubyCacheDecoupledMN, "  3b.tag to data ptr cleared.\n");
    m_tag_data_ptr[tagSet][tagWay] = NULL; //tag to data
    DPRINTF(RubyCacheDecoupledMN, "  3c.m_tag_seg_cntr cleared.\n");
    m_tag_seg_cntr[tagSet][tagWay] = 0;
    DPRINTF(RubyCacheDecoupledMN, "  3d.m_tag_hashTable_ptr_valid reset to false.\n");
    m_tag_hashTable_ptr_valid[tagSet][tagWay] = false;

    //decrement data cntr
    DPRINTF(RubyCacheDecoupledMN, "  4.decrementing m_data_cntr.\n");
    m_data_cntr[dataSet][dataSeg] -= 1;
}

bool
CacheMemoryDecoupledMN::cacheCanCoallocate(Addr address, int data_size)
{
    DPRINTF(RubyCacheDecoupledMN, "cacheCanCoallocate() in CacheMemoryDecoupledMN: %#x\n",address);
    int num_seg_per_data = divCeil(data_size,m_segment_size);
    DPRINTF(RubyCacheDecoupledMN, "cacheCanCoallocate:data_size=%dB, equivalent to %d segment\n", data_size, num_seg_per_data);
    // std::cout << "cacheCanCoallocate:data size=" << data_size << ", equivalent to " << num_seg_per_data << " segs." <<std::endl;
    assert(address == makeLineAddress(address));

    // tag array look up
    const AbstractCacheEntry* const tagEntry = CacheMemory::lookup(address);
    int tagset = tagEntry->getSet();
    int tagway = tagEntry->getWay();
    int has = m_tag_seg_cntr[tagset][tagway];
    assert (has != 0); // should have some data

    AbstractCacheEntry* dataEntry = m_tag_data_ptr[tagset][tagway];
    assert (dataEntry!= nullptr);
    int remaining_vacancy = m_data_set_vacancy[dataEntry->getSet()];
    int need_more_segs = num_seg_per_data - has;
    if (m_data_cntr[dataEntry->getSet()][dataEntry->getWay()] > 1) {
        // other tags point to this data, we cannot assume these will be freed
        need_more_segs = num_seg_per_data;
    }

    if (need_more_segs > remaining_vacancy) { //current set cannot coallocate, check other sets
        // data array space check
        for (int i = 0; i < m_data_array_set; i++) {
            if (m_data_set_vacancy[i] >= num_seg_per_data) {
                // std::cout << "  data set[" << i << "] has enough vacancy." <<std::endl;
                DPRINTF(RubyCacheDecoupledMN, "  data set[%d] has enough vacancy.\n", i);
                return true;
            }
        }
    }
    else {
        DPRINTF(RubyCacheDecoupledMN, "  data set[%d] can coallocate.\n", dataEntry->getSet());
        return true;
    }
    DPRINTF(RubyCacheDecoupledMN, "  all data sets cannot coallocate.\n");
    return false;
}

bool
CacheMemoryDecoupledMN::cacheAvailData(Addr address, int data_size) const
{
    DPRINTF(RubyCacheDecoupledMN, "cacheAvailData() in CacheMemoryDecoupledMN: %#x\n",address);
    int num_seg_per_data = divCeil(data_size,m_segment_size);
    DPRINTF(RubyCacheDecoupledMN, "cacheAvailData:data_size=%dB, equivalent to %d segment\n", data_size, num_seg_per_data);
    // std::cout << "cacheAvailData:data size=" << data_size << ", equivalent to " << num_seg_per_data << " segs." <<std::endl;
    assert(address == makeLineAddress(address));

    // tag array look up
    const AbstractCacheEntry* const tagEntry = CacheMemory::lookup(address);
    int tagset = tagEntry->getSet();
    int tagway = tagEntry->getWay();
    assert (m_tag_seg_cntr[tagset][tagway] == 0); // should not have any data! write for the first time

    // data array space check
    for (int i = 0; i < m_data_array_set; i++) {
        if (m_data_set_vacancy[i] >= num_seg_per_data) {
            // std::cout << "  data set[" << i << "] has enough vacancy." <<std::endl;
            DPRINTF(RubyCacheDecoupledMN, "  data set[%d] has enough vacancy.\n", i);
            return true;
        }
    }
    return false;
}

bool
CacheMemoryDecoupledMN::doesTagListContainAddress(AbstractCacheEntry* tagHead, Addr address) const
{
    assert(tagHead != nullptr);
    if (tagHead->m_Address == address) {
        return true;
    }
    if (m_tag_next_tag_ptr[tagHead->getSet()][tagHead->getWay()] == nullptr) {
        if (tagHead->m_Address == address) {
            return true;
        }
        else {
            return false;
        }
    }
    AbstractCacheEntry* curTag = tagHead;
    while (m_tag_next_tag_ptr[curTag->getSet()][curTag->getWay()] != nullptr) {
        AbstractCacheEntry* nextTag = m_tag_next_tag_ptr[curTag->getSet()][curTag->getWay()];
        if (nextTag->m_Address == address) return true;
        curTag = nextTag;
    }
    return false;
}

// Returns with the physical address of the conflicting cache line for data array
Addr
CacheMemoryDecoupledMN::cacheProbeData(Addr address) const
{
    DPRINTF(RubyCacheDecoupledMN, "cacheProbeData() in CacheMemoryDecoupledMN\n");
    assert(address == makeLineAddress(address));
    assert(cacheAvail(address));

    // collect replacement candidates
    std::vector<ReplaceableEntry*> candidates;
    for (int i = 0; i < m_data_array_set; i++) {
        for (int j = 0; j < m_num_seg_per_set; j++) {
            if (m_cache_data[i][j] != NULL) {
                if (!doesTagListContainAddress(m_data_head_tag_ptr[i][j],address)) {
                    //if my address is not among the tag list => safe to add as cand
                    candidates.push_back(static_cast<ReplaceableEntry*>(
                                                                m_cache_data[i][j]));
                    DPRINTF(RubyCacheDecoupledMN, 
                    "       - data[%d,%d] added as candidate\n", i, j);
                }
                else {
                    DPRINTF(RubyCacheDecoupledMN, 
                        "       - data[%d,%d] is my data, skipping\n", i, j);
                }
            }
        }
    }
    assert(candidates.size() > 0);
    DPRINTF(RubyCacheDecoupledMN, "    arbitrating among %d candidates\n", candidates.size());

    ReplaceableEntry* victim = m_replacementPolicy_ptr_data->getVictim(candidates);
    assert(victim != NULL);
    int vSet = victim->getSet();
    int vSeg = victim->getWay();
    DPRINTF(RubyCacheDecoupledMN, "  identified conflicting data[%d,%d]\n", vSet, vSeg);

    assert(m_data_head_tag_ptr[vSet][vSeg] != NULL);
    DPRINTF(RubyCacheDecoupledMN, "  identified its associated tag head at tag[%d,%d]\n", 
    m_data_head_tag_ptr[vSet][vSeg]->getSet(),
    m_data_head_tag_ptr[vSet][vSeg]->getWay());

    return m_data_head_tag_ptr[vSet][vSeg]->m_Address;
}

Addr
CacheMemoryDecoupledMN::findDuplicatedDatasTagAddr(uint32_t hash, int i) const
{
    assert (i>=0);
    DPRINTF(RubyCacheDecoupledMN, "findDuplicatedDatasTagAddr() in CacheMemoryDecoupledMN\n");
    // access in hashTable
    HashTableEntry* hashEntry = lookupHash(hash);
    if (hashEntry != nullptr) {
        DPRINTF(RubyCacheDecoupledMN, "findDuplicatedDatasTagAddr:found hashtable entry\n");
        int dataSet = hashEntry->m_dataSet;
        DPRINTF(RubyCacheDecoupledMN, " findDuplicatedDatasTagAddr:found hashtable entry says dataset=%d\n", dataSet);
        // for (int i = 0; i < m_num_seg_per_set; i++) {
        // AbstractCacheEntry* dataEntry = m_cache_data[dataSet][i];
        AbstractCacheEntry* tagEntry_head_collision = m_data_head_tag_ptr[dataSet][i];
        DPRINTF(RubyCacheDecoupledMN, " findDuplicatedDatasTagAddr:data loc=%d,%d\n", dataSet, i);
        int tagset_collision = tagEntry_head_collision->getSet();
        int tagway_collision = tagEntry_head_collision->getWay();
        if (m_tag_hashTable_ptr_valid[tagset_collision][tagway_collision]) {
            uint32_t hash_collision = m_tag_hashTable_ptr[tagset_collision][tagway_collision];
            if (hash_collision == hash) {
                //found duplicated data's tag
                DPRINTF(RubyCacheDecoupledMN, " findDuplicatedDatasTagAddr:found duplicated data's tag at [%d,%d]\n",
                    tagset_collision, tagway_collision);
                return tagEntry_head_collision->m_Address;
            }
        }
        // }
    }
    panic("findDuplicatedDatasTagAddr did not find hash match");
}

int
CacheMemoryDecoupledMN::findDuplicatedDatasTagWay(uint32_t hash) const
{
    DPRINTF(RubyCacheDecoupledMN, "findDuplicatedDatasTagWay() in CacheMemoryDecoupledMN\n");

    // access in hashTable
    HashTableEntry* hashEntry = lookupHash(hash);
    if (hashEntry != nullptr) {
        DPRINTF(RubyCacheDecoupledMN, " findDuplicatedDatasTagWay:found hashtable entry\n");
        int dataSet = hashEntry->m_dataSet;
        DPRINTF(RubyCacheDecoupledMN, " findDuplicatedDatasTagWay:found hashtable entry says dataset=%d\n", dataSet);
        for (int i = 0; i < m_num_seg_per_set; i++) {
            // AbstractCacheEntry* dataEntry = m_cache_data[dataSet][i];
            AbstractCacheEntry* tagEntry_head_collision = m_data_head_tag_ptr[dataSet][i];
            if (tagEntry_head_collision != nullptr) {
                int tagset_collision = tagEntry_head_collision->getSet();
                int tagway_collision = tagEntry_head_collision->getWay();
                if (m_tag_hashTable_ptr_valid[tagset_collision][tagway_collision]) {
                    uint32_t hash_collision = m_tag_hashTable_ptr[tagset_collision][tagway_collision];
                    if (hash_collision == hash) {
                        //found duplicated data's tag
                        DPRINTF(RubyCacheDecoupledMN, " findDuplicatedDatasTagWay:found duplicated data's tag at [%d,%d]\n",
                            tagset_collision, tagway_collision);
                        return i;
                    }
                    else {
                        DPRINTF(RubyCacheDecoupledMN, " findDuplicatedDatasTagWay<info>:data[%d,%d]'s tag's hash mismatch!\n",
                            dataSet,i);
                        // std::cout << "  hash=" <<
                        //     std::setw(2) << std::setfill('0') << std::hex << "0x" <<
                        //     uint32_t(hash)
                        //     << " " << std::setfill(' ')<< std::dec << std::endl;
                        // std::cout << "  whereas hash_collision=" <<
                        //     std::setw(2) << std::setfill('0') << std::hex << "0x" <<
                        //     uint32_t(hash_collision)
                        //     << " " << std::setfill(' ')<< std::dec << std::endl;
                    }
                }
                else {
                    DPRINTF(RubyCacheDecoupledMN, " findDuplicatedDatasTagWay<info>:data[%d,%d]'s m_tag_hashTable_ptr_valid false!\n",
                                dataSet,i);
                }
            }
            else {
                DPRINTF(RubyCacheDecoupledMN, " findDuplicatedDatasTagWay<info>:data[%d,%d]'s head tag is null!\n",
                            dataSet,i);
            }
        }
    }
    DPRINTF(RubyCacheDecoupledMN, " findDuplicatedDatasTagWay:no ht entry found\n");
    return -1;
}

CacheMemoryDecoupledMN::
CacheMemoryDecoupledMNStats::CacheMemoryDecoupledMNStats(statistics::Group *parent)
    : statistics::Group(parent),
      ADD_STAT(numHashTableEntryInUse, statistics::units::Rate<
                statistics::units::Count, statistics::units::Tick>::get(),
                "Number of hashtable entry in use (average)"),
      ADD_STAT(numDataSetMisplace, "number of times non-default set mapping is used"),
      ADD_STAT(numDataSetDefaultPlacement, "number of times default set mapping is used"),
      ADD_STAT(numHashTableEntryReplacement, "number of times hash table entry replaced"),
      ADD_STAT(numHashTableHit, "number of times hash table entry hit"),
      ADD_STAT(numHashTableMiss, "number of times hash table entry miss"),
      ADD_STAT(numHashCollision, "number of times hash collides, i.e., hit but data mismatch")
{
    numHashTableEntryInUse
        .flags(statistics::nozero);
    numDataSetMisplace
        .flags(statistics::nozero);
    numDataSetDefaultPlacement
        .flags(statistics::nozero);
    numHashTableEntryReplacement
        .flags(statistics::nozero);
    numHashTableHit
        .flags(statistics::nozero);
    numHashTableMiss
        .flags(statistics::nozero);
    numHashCollision
        .flags(statistics::nozero);
}

}
}