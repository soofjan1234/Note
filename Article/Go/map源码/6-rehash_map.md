```go
// Replaces the table with one larger table or two split tables to fit more
// entries. Since the table is replaced, t is now stale and should not be
// modified.
func (t *table) rehash(typ *abi.SwissMapType, m *Map) {
	// TODO(prattmic): SwissTables typically perform a "rehash in place"
	// operation which recovers capacity consumed by tombstones without growing
	// the table by reordering slots as necessary to maintain the probe
	// invariant while eliminating all tombstones.
	//
	// However, it is unclear how to make rehash in place work with
	// iteration. Since iteration simply walks through all slots in order
	// (with random start offset), reordering the slots would break
	// iteration.
	//
	// As an alternative, we could do a "resize" to new groups allocation
	// of the same size. This would eliminate the tombstones, but using a
	// new allocation, so the existing grow support in iteration would
	// continue to work.

	newCapacity := 2 * t.capacity
	if newCapacity <= maxTableCapacity {
		t.grow(typ, m, newCapacity)
		return
	}

	t.split(typ, m)
}
```

1. 计算当前容量*2是否小于规定的单表最大限制
    1. 小于，则翻倍扩容，分配一个两倍大的新表，把旧数据重新哈希搬过去
    2. 否则分裂扩容，将一张表拆成两张新表。

TODO讲的是
标准 Swiss Table 的做法： 如果表里有很多“墓碑”（Deleted），空间被浪费了。标准做法是 "rehash in place"（原地重排）。不需要分配新内存，只是把数据在原表内重新挪动，清理掉墓碑。
Go 遇到的难题：迭代器 (Iteration)： Go 语言对 Map 的迭代语义非常慷慨（允许迭代时增删）。
迭代器通常是按内存顺序扫过去的。
如果你在迭代器扫到一半时“原地重排”了数据，由于探测序列变了，同一个 Key 可能会被迭代器碰到两次，或者被漏掉。
目前的权衡： 为了保证迭代器的正确性（不重复、不遗漏），Go 选择分配新内存。
要么通过 grow 变成更大的表。
要么通过 resize（注释里提到了）变成同样大小但“干净”的新表。
因为有了新分配的内存，旧表可以保持不动，直到正在运行的迭代器完成任务。


```go
// grow the capacity of the table by allocating a new table with a bigger array
// and uncheckedPutting each element of the table into the new table (we know
// that no insertion here will Put an already-present value), and discard the
// old table.
func (t *table) grow(typ *abi.SwissMapType, m *Map, newCapacity uint16) {
	newTable := newTable(typ, uint64(newCapacity), t.index, t.localDepth)

	if t.capacity > 0 {
		for i := uint64(0); i <= t.groups.lengthMask; i++ {
			g := t.groups.group(typ, i)
			for j := uintptr(0); j < abi.SwissMapGroupSlots; j++ {
				if (g.ctrls().get(j) & ctrlEmpty) == ctrlEmpty {
					// Empty or deleted
					continue
				}

				key := g.key(typ, j)
				if typ.IndirectKey() {
					key = *((*unsafe.Pointer)(key))
				}

				elem := g.elem(typ, j)
				if typ.IndirectElem() {
					elem = *((*unsafe.Pointer)(elem))
				}

				hash := typ.Hasher(key, m.seed)

				newTable.uncheckedPutSlot(typ, hash, key, elem)
			}
		}
	}

	newTable.checkInvariants(typ, m)
	m.replaceTable(newTable)
	t.index = -1
}
```

grow函数
1. 分配一个两倍大的新表
2. 遍历旧表，搬活人，跳过墓碑和空
3. 重新计算哈希，搬过去，不需要检查重复，性能优化
4. 替换旧表

```go
// split the table into two, installing the new tables in the map directory.
func (t *table) split(typ *abi.SwissMapType, m *Map) {
	localDepth := t.localDepth
	localDepth++

	// TODO: is this the best capacity?
	left := newTable(typ, maxTableCapacity, -1, localDepth)
	right := newTable(typ, maxTableCapacity, -1, localDepth)

	// Split in half at the localDepth bit from the top.
	mask := localDepthMask(localDepth)

	for i := uint64(0); i <= t.groups.lengthMask; i++ {
		g := t.groups.group(typ, i)
		for j := uintptr(0); j < abi.SwissMapGroupSlots; j++ {
			if (g.ctrls().get(j) & ctrlEmpty) == ctrlEmpty {
				// Empty or deleted
				continue
			}

			key := g.key(typ, j)
			if typ.IndirectKey() {
				key = *((*unsafe.Pointer)(key))
			}

			elem := g.elem(typ, j)
			if typ.IndirectElem() {
				elem = *((*unsafe.Pointer)(elem))
			}

			hash := typ.Hasher(key, m.seed)
			var newTable *table
			if hash&mask == 0 {
				newTable = left
			} else {
				newTable = right
			}
			newTable.uncheckedPutSlot(typ, hash, key, elem)
		}
	}

	m.installTableSplit(t, left, right)
	t.index = -1
}
```

split 函数：
1. **创建两个最大容量的新表 (`left` & `right`)**：
    * 触发前提：翻倍后的新容量超过了单表最大限制（`2 * t.capacity > maxTableCapacity`）。
    * `left` 表示哈希空间的左半部分，`right` 表示右半部分。
2. **数据分流搬迁**：
    * 遍历旧表，只搬运有效数据（跳过空位和墓碑）。
    * 根据哈希值在新增位（`localDepth` 位）上的值（0 或 1）决定将数据搬往 `left` 还是 `right`。
    * 使用 `uncheckedPutSlot` 快速写入，无需检查重复。
3. **更新目录与作废旧表**：
    * 调用 `installTableSplit` 更新顶层 Map 的目录，使对应索引指向这两个新表。
    * 将旧表索引设为 -1，标记为失效。

```go
func (m *Map) installTableSplit(old, left, right *table) {
	if old.localDepth == m.globalDepth {
		// No room for another level in the directory. Grow the
		// directory.
		newDir := make([]*table, m.dirLen*2)
		for i := range m.dirLen {
			t := m.directoryAt(uintptr(i))
			newDir[2*i] = t
			newDir[2*i+1] = t
			// t may already exist in multiple indicies. We should
			// only update t.index once. Since the index must
			// increase, seeing the original index means this must
			// be the first time we've encountered this table.
			if t.index == i {
				t.index = 2 * i
			}
		}
		m.globalDepth++
		m.globalShift--
		//m.directory = newDir
		m.dirPtr = unsafe.Pointer(&newDir[0])
		m.dirLen = len(newDir)
	}

	// N.B. left and right may still consume multiple indicies if the
	// directory has grown multiple times since old was last split.
	left.index = old.index
	m.replaceTable(left)

	entries := 1 << (m.globalDepth - left.localDepth)
	right.index = left.index + entries
	m.replaceTable(right)
}
```