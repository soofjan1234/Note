Terminology:
- Slot: A storage location of a single key/element pair.
- Group: A group of abi.SwissMapGroupSlots (8) slots, plus a control word.
- Control word: An 8-byte word which denotes whether each slot is empty,
  deleted, or used. If a slot is used, its control byte also contains the
  lower 7 bits of the hash (H2).
- H1: Upper 57 bits of a hash.
- H2: Lower 7 bits of a hash.
- Table: A complete "Swiss Table" hash table. A table consists of one or
  more groups for storage plus metadata to handle operation and determining
  when to grow.
- Map: The top-level Map type consists of zero or more tables for storage.
  The upper bits of the hash select which table a key belongs to.
- Directory: Array of the tables used by the map.

术语：
- Slot（槽位）：存储单个键/值对的位置。
- Group（组）：包含 abi.SwissMapGroupSlots (8) 个槽位以及一个控制字。
- Control word（控制字）：一个 8 字节的字，表示每个槽位是空的、已删除的还是已使用的。
  如果槽位已使用，其对应的控制字节还包含哈希值的低 7 位（H2）。
- H1：哈希值的高 57 位。
- H2：哈希值的低 7 位。
- Table（表）：一个完整的 "Swiss Table" 哈希表。一个表包含一个或多个用于存储的组，
  以及处理操作和确定何时扩容的元数据。
- Map（映射）：顶层的 Map 类型包含零个或多个用于存储的表。哈希值的高位决定键属于哪个表。
- Directory（目录）：Map 使用的表数组。

At its core, the table design is similar to a traditional open-addressed
hash table. Storage consists of an array of groups, which effectively means
an array of key/elem slots with some control words interspersed. Lookup uses
the hash to determine an initial group to check. If, due to collisions, this
group contains no match, the probe sequence selects the next group to check
(see below for more detail about the probe sequence).
在核心设计上，表的结构类似于传统的开放寻址哈希表。存储由组数组组成，
这实际上意味着一个散布着控制字的键/值槽位数组。查找时使用哈希值确定要检查的初始组。
如果由于冲突导致该组不包含匹配项，则探测序列会选择下一个要检查的组（有关探测序列的详情见下文）。

The key difference occurs within a group. In a standard open-addressed
linear probed hash table, we would check each slot one at a time to find a
match. A swiss table utilizes the extra control word to check all 8 slots in
parallel.
关键区别在于组内部。在标准的线性探测开放寻址哈希表中，我们会逐个检查槽位以寻找匹配。
Swiss Table 利用额外的控制字来并行检查所有 8 个槽位。

Each byte in the control word corresponds to one of the slots in the group.
In each byte, 1 bit is used to indicate whether the slot is in use, or if it
is empty/deleted. The other 7 bits contain the lower 7 bits of the hash for
the key in that slot. See [ctrl] for the exact encoding.
控制字中的每个字节对应组中的一个槽位。在每个字节中，1 位用于指示槽位是否正在使用，
或者是空的/已删除的。另外 7 位包含该槽位键的哈希值低 7 位。具体编码见 [ctrl]。

During lookup, we can use some clever bitwise manipulation to compare all 8
7-bit hashes against the input hash in parallel (see [ctrlGroup.matchH2]).
That is, we effectively perform 8 steps of probing in a single operation.
With SIMD instructions, this could be extended to 16 slots with a 16-byte
control word.
在查找期间，我们可以使用一些巧妙的位运算来并行地将所有 8 个 7 位哈希值与输入哈希值进行比较（见 [ctrlGroup.matchH2]）。
也就是说，我们实际上在单次操作中完成了 8 个探测步骤。
使用 SIMD 指令，如果配合 16 字节的控制字，这甚至可以扩展到 16 个槽位。

Since we only use 7 bits of the 64 bit hash, there is a 1 in 128 (~0.7%)
probability of false positive on each slot, but that's fine: we always need
double check each match with a standard key comparison regardless.
由于我们只使用了 64 位哈希中的 7 位，每个槽位出现误报的概率是 1/128 (~0.7%)，
但这没关系：无论如何，我们始终需要通过标准的键比较来双重检查每个匹配项。

Probing
Probing is done using the upper 57 bits (H1) of the hash as an index into
the groups array. Probing walks through the groups using quadratic probing
until it finds a group with a match or a group with an empty slot. See
[probeSeq] for specifics about the probe sequence. Note the probe
invariants: the number of groups must be a power of two, and the end of a
probe sequence must be a group with an empty slot (the table can never be
100% full).
探测是使用哈希值的高 57 位 (H1) 作为组数组的索引进行的。探测使用二次探测遍历组，
直到找到匹配的组或带有空槽位的组。探测序列的具体细节见 [probeSeq]。
注意探测不变性：组的数量必须是 2 的幂，并且探测序列的结尾必须是带有空槽位的组（表永远不会 100% 满）。

Deletion
Probing stops when it finds a group with an empty slot. This affects
deletion: when deleting from a completely full group, we must not mark the
slot as empty, as there could be more slots used later in a probe sequence
and this deletion would cause probing to stop too early. Instead, we mark
such slots as "deleted" with a tombstone. If the group still has an empty
slot, we don't need a tombstone and directly mark the slot empty. Insert
prioritizes reuse of tombstones over filling an empty slots. Otherwise,
tombstones are only completely cleared during grow, as an in-place cleanup
complicates iteration.
探测在找到带有空槽位的组时停止。这会影响删除操作：当从一个完全装满的组中删除时，
我们绝不能将该槽位标记为空，因为在探测序列的后续部分可能还有更多已使用的槽位，
而这种删除会导致探测过早停止。相反，我们使用"墓碑"将此类槽位标记为"已删除"。
如果组内仍有空槽位，则不需要墓碑，直接将槽位标记为空即可。
插入操作会优先复用墓碑，而不是填充空槽位。此外，墓碑只在扩容期间被彻底清理，
因为原地清理会使迭代变得复杂。

Growth
The probe sequence depends on the number of groups. Thus, when growing the
group count all slots must be reordered to match the new probe sequence. In
other words, an entire table must be grown at once.
探测序列取决于组的数量。因此，当扩容组数量时，必须重新排列所有槽位以匹配新的探测序列。
换句话说，整个表必须一次性扩容。

In order to support incremental growth, the map splits its contents across
multiple tables. Each table is still a full hash table, but an individual
table may only service a subset of the hash space. Growth occurs on
individual tables, so while an entire table must grow at once, each of these
grows is only a small portion of a map. The maximum size of a single grow is
limited by limiting the maximum size of a table before it is split into
multiple tables.
为了支持增量扩容，Map 将其内容拆分到多个表中。每个表仍然是一个完整的哈希表，
但单个表可能仅服务于哈希空间的一个子集。扩容发生在单个表上，
因此虽然整个表必须一次性扩容，但每次扩容仅仅是 Map 的一小部分。
单次扩容的最大规模受到限制，即限制了表在分裂成多个表之前的最大尺寸。

A map starts with a single table. Up to [maxTableCapacity], growth simply
replaces this table with a replacement with double capacity. Beyond this
limit, growth splits the table into two.
Map 以单个表开始。在达到 [maxTableCapacity] 之前，扩容只是简单地将此表替换为容量加倍的新表。
超过此限制后，扩容会将该表一分为二。

The map uses "extendible hashing" to select which table to use. In
extendible hashing, we use the upper bits of the hash as an index into an
array of tables (called the "directory"). The number of bits uses increases
as the number of tables increases. For example, when there is only 1 table,
we use 0 bits (no selection necessary). When there are 2 tables, we use 1
bit to select either the 0th or 1st table. [Map.globalDepth] is the number
of bits currently used for table selection, and by extension (1 <<
globalDepth), the size of the directory.
Map 使用"可扩展哈希"来选择使用哪个表。在可扩展哈希中，我们将哈希值的高位用作表数组（称为"目录"）的索引。
所使用的位数随着表数量的增加而增加。例如，当只有 1 个表时，我们使用 0 位（无需选择）。
当有 2 个表时，我们使用 1 位来选择第 0 个或第 1 个表。[Map.globalDepth] 是当前用于表选择的位数，
进而 (1 << globalDepth) 就是目录的大小。

Note that each table has its own load factor and grows independently. If the
1st bucket grows, it will split. We'll need 2 bits to select tables, though
we'll have 3 tables total rather than 4. We support this by allowing
multiple indicies to point to the same table. This example:
	directory (globalDepth=2)
	+----+
	| 00 | --\
	+----+    +--> table (localDepth=1)
	| 01 | --/
	+----+
	| 10 | ------> table (localDepth=2)
	+----+
	| 11 | ------> table (localDepth=2)
	+----+
请注意，每个表都有自己的负载因子并独立扩容。如果第 1 个存储桶扩容，它将分裂。
我们将需要 2 位来选择表，尽管我们总共只有 3 个表而不是 4 个。
我们通过允许多个索引指向同一个表来支持这一点。

Tables track the depth they were created at (localDepth). It is necessary to
grow the directory when splitting a table where globalDepth == localDepth.
表会跟踪它们创建时的深度 (localDepth)。当分裂一个 globalDepth == localDepth 的表时，有必要扩容目录。

Iteration
Iteration is the most complex part of the map due to Go's generous iteration
semantics. A summary of semantics from the spec:
1. Adding and/or deleting entries during iteration MUST NOT cause iteration
   to return the same entry more than once.
2. Entries added during iteration MAY be returned by iteration.
3. Entries modified during iteration MUST return their latest value.
4. Entries deleted during iteration MUST NOT be returned by iteration.
5. Iteration order is unspecified. In the implementation, it is explicitly
   randomized.
迭代
由于 Go 慷慨的迭代语义，迭代是 Map 中最复杂的部分。规范中的语义摘要：
1. 在迭代期间添加和/或删除条目绝不能导致迭代多次返回同一个条目。
2. 在迭代期间添加的条目可能会被迭代返回。
3. 在迭代期间修改的条目必须返回其最新值。
4. 在迭代期间删除的条目绝不能被迭代返回。
5. 迭代顺序是未指定的。在实现中，它是被显式随机化的。

If the map never grows, these semantics are straightforward: just iterate
over every table in the directory and every group and slot in each table.
These semantics all land as expected.
如果 Map 永远不扩容，这些语义就很简单：只需遍历目录中的每个表以及每个表中的每个组和槽位即可。
这些语义都会如预期般实现。

If the map grows during iteration, things complicate significantly. First
and foremost, we need to track which entries we already returned to satisfy
(1). There are three types of grow:
a. A table replaced by a single larger table.
b. A table split into two replacement tables.
c. Growing the directory (occurs as part of (b) if necessary).
如果 Map 在迭代期间扩容，情况会变得非常复杂。首先也是最重要的，
我们需要跟踪已经返回了哪些条目以满足 (1)。有三种类型的扩容：
a. 一个表被单个更大的表替换。
b. 一个表分裂为两个替换表。
c. 扩容目录（如果需要，作为 (b) 的一部分发生）。

For all of these cases, the replacement table(s) will have a different probe
sequence, so simply tracking the current group and slot indices is not
sufficient.
对于所有这些情况，替换表将具有不同的探测序列，因此仅跟踪当前的组和槽位索引是不够的。

For (a) and (b), note that grows of tables other than the one we are
currently iterating over are irrelevant.
对于 (a) 和 (b)，请注意，除了我们当前正在迭代的表之外，其他表的扩容是无关紧要的。

We handle (a) and (b) by having the iterator keep a reference to the table
it is currently iterating over, even after the table is replaced. We keep
iterating over the original table to maintain the iteration order and avoid
violating (1). Any new entries added only to the replacement table(s) will
be skipped (allowed by (2)). To avoid violating (3) or (4), while we use the
original table to select the keys, we must look them up again in the new
table(s) to determine if they have been modified or deleted. There is yet
another layer of complexity if the key does not compare equal itself. See
[Iter.Next] for the gory details.
我们通过让迭代器保持对当前正在迭代的表的引用来处理 (a) 和 (b)，即使在该表被替换之后也是如此。
我们继续在原表上进行迭代以维持迭代顺序并避免违反 (1)。
任何仅添加到替换表中的新条目都将被跳过（这是 (2) 允许的）。
为了避免违反 (3) 或 (4)，虽然我们使用原表来选择键，但我们必须在新表中再次查找它们，
以确定它们是否已被修改或删除。如果键本身比较不相等，还会有另一层复杂性。具体细节见 [Iter.Next]。

Note that for (b) once we finish iterating over the old table we'll need to
skip the next entry in the directory, as that contains the second split of
the old table. We can use the old table's localDepth to determine the next
logical index to use.
注意对于 (b)，一旦我们完成了对旧表的迭代，我们需要跳过目录中的下一个条目，因为那包含旧表的第二次分裂。
我们可以使用旧表的 localDepth 来确定要使用的下一个逻辑索引。

For (b), we must adjust the current directory index when the directory
grows. This is more straightforward, as the directory orders remains the
same after grow, so we just double the index if the directory size doubles.
对于 (b)，当目录扩容时，我们必须调整当前的目录索引。这比较直接，因为目录顺序在扩容后保持不变，
所以如果目录大小翻倍，我们只需将索引翻倍即可。

```go
type map struct {
	// 表的目录。
	dirPtr unsafe.Pointer
	dirLen int
	// 用于表目录查找的位数。
	globalDepth uint8
}
```

```go
// Maximum size of a table before it is split at the directory level.
const maxTableCapacity = 1024

// table is a Swiss table hash table structure.
type table struct {
	// The number of filled slots (i.e. the number of elements in the table).
	used uint16
	// The total number of slots (always 2^N).
	capacity uint16
	// The number of slots we can still fill without needing to rehash.
	growthLeft uint16
	// The number of bits used by directory lookups above this table.
	localDepth uint8
	// Index of this table in the Map directory.
	index int
	// groups is an array of slot groups.
	groups groupsReference
}
```
