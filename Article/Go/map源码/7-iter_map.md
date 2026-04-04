```go
type Iter struct {
	key  unsafe.Pointer // Must be in first position.  Write nil to indicate iteration end (see cmd/compile/internal/walk/range.go).
	// 键指针。必须位于第一位。写入 nil 表示迭代结束（参见 cmd/compile/internal/walk/range.go）。
	elem unsafe.Pointer // Must be in second position (see cmd/compile/internal/walk/range.go).
	// 元素（值）指针。必须位于第二位。
	typ  *abi.SwissMapType
	m    *Map

	// Randomize iteration order by starting iteration at a random slot
	// offset. The offset into the directory uses a separate offset, as it
	// must adjust when the directory grows.
	// 通过从随机的槽位偏移量开始迭代，来实现迭代顺序的随机化。
	// 目录的偏移量使用独立的偏移量，因为它必须在目录扩容时进行调整。
	entryOffset uint64
	dirOffset   uint64

	// Snapshot of Map.clearSeq at iteration initialization time. Used to
	// detect clear during iteration.
	// 迭代初始化时 Map.clearSeq 的快照。用于检测迭代过程中的 clear 操作。
	clearSeq uint64

	// Value of Map.globalDepth during the last call to Next. Used to
	// detect directory grow during iteration.
	// 上一次调用 Next 时 Map.globalDepth 的值。用于检测迭代过程中的目录扩容。
	globalDepth uint8

	// dirIdx is the current directory index, prior to adjustment by
	// dirOffset.
	// dirIdx 是当前的目录索引（在经由 dirOffset 调整之前）。
	dirIdx int

	// tab is the table at dirIdx during the previous call to Next.
	// tab 是上一次调用 Next 时位于 dirIdx 的表。
	tab *table

	// group is the group at entryIdx during the previous call to Next.
	// group 是上一次调用 Next 时位于 entryIdx 处的组。
	group groupReference

	// entryIdx is the current entry index, prior to adjustment by entryOffset.
	// The lower 3 bits of the index are the slot index, and the upper bits
	// are the group index.
	// entryIdx 是当前的条目索引（在经由 entryOffset 调整之前）。
	// 索引的低 3 位是槽位索引，高位是组索引。
	entryIdx uint64
}
```

```go
func (it *Iter) nextDirIdx() {
	// Skip other entries in the directory that refer to the same
	// logical table. There are two cases of this:
	//
	// Consider this directory:
	//
	// - 0: *t1
	// - 1: *t1
	// - 2: *t2a
	// - 3: *t2b
	//
	// At some point, the directory grew to accommodate a split of
	// t2. t1 did not split, so entries 0 and 1 both point to t1.
	// t2 did split, so the two halves were installed in entries 2
	// and 3.
	//
	// If dirIdx is 0 and it.tab is t1, then we should skip past
	// entry 1 to avoid repeating t1.
	//
	// If dirIdx is 2 and it.tab is t2 (pre-split), then we should
	// skip past entry 3 because our pre-split t2 already covers
	// all keys from t2a and t2b (except for new insertions, which
	// iteration need not return).
	//
	// We can achieve both of these by using to difference between
	// the directory and table depth to compute how many entries
	// the table covers.
	entries := 1 << (it.m.globalDepth - it.tab.localDepth)
	it.dirIdx += entries
	it.tab = nil
	it.group = groupReference{}
	it.entryIdx = 0
}
```

在迭代 Map 的目录（Directory）时，跳过指向同一个“逻辑表”的重复条目，确保每个数据只被遍历一次。
考虑这个全局深度为2的目录:
00 t1
01 t1
10 t2a
11 t2b
其中t1的局部深度是1，t2a和t2b的局部深度是2。
我们遍历了00的t1表后可以跳过01，直接到10的t2a表。



```go
// Return the appropriate key/elem for key at slotIdx index within it.group, if
// any.
func (it *Iter) grownKeyElem(key unsafe.Pointer, slotIdx uintptr) (unsafe.Pointer, unsafe.Pointer, bool) {
	newKey, newElem, ok := it.m.getWithKey(it.typ, key)
	if !ok {
		// Key has likely been deleted, and
		// should be skipped.
		//
		// One exception is keys that don't
		// compare equal to themselves (e.g.,
		// NaN). These keys cannot be looked
		// up, so getWithKey will fail even if
		// the key exists.
		//
		// However, we are in luck because such
		// keys cannot be updated and they
		// cannot be deleted except with clear.
		// Thus if no clear has occurred, the
		// key/elem must still exist exactly as
		// in the old groups, so we can return
		// them from there.
		//
		// TODO(prattmic): Consider checking
		// clearSeq early. If a clear occurred,
		// Next could always return
		// immediately, as iteration doesn't
		// need to return anything added after
		// clear.
		if it.clearSeq == it.m.clearSeq && !it.typ.Key.Equal(key, key) {
			elem := it.group.elem(it.typ, slotIdx)
			if it.typ.IndirectElem() {
				elem = *((*unsafe.Pointer)(elem))
			}
			return key, elem, true
		}

		// This entry doesn't exist anymore.
		return nil, nil, false
	}

	return newKey, newElem, true
}
```

这个函数就是去新表读最新的值返回，没查到怎么办？
1. 说明已经被删除了，直接返回
2. 还有种情况是key为NaN，那无法get，也就无法修改，直接找旧值返回
    1. 还要查看是否在clear后，如果是，就说明数据都已经失效了

```go
// Next proceeds to the next element in iteration, which can be accessed via
// the Key and Elem methods.
//
// The table can be mutated during iteration, though there is no guarantee that
// the mutations will be visible to the iteration.
//
// Init must be called prior to Next.
func (it *Iter) Next() {
	if it.m == nil {
		// Map was empty at Iter.Init.
		it.key = nil
		it.elem = nil
		return
	}

	if it.m.writing != 0 {
		fatal("concurrent map iteration and map write")
		return
	}

	if it.dirIdx < 0 {
		// Map was small at Init.
		for ; it.entryIdx < abi.SwissMapGroupSlots; it.entryIdx++ {
			k := uintptr(it.entryIdx+it.entryOffset) % abi.SwissMapGroupSlots

			if (it.group.ctrls().get(k) & ctrlEmpty) == ctrlEmpty {
				// Empty or deleted.
				continue
			}

			key := it.group.key(it.typ, k)
			if it.typ.IndirectKey() {
				key = *((*unsafe.Pointer)(key))
			}

			// As below, if we have grown to a full map since Init,
			// we continue to use the old group to decide the keys
			// to return, but must look them up again in the new
			// tables.
			grown := it.m.dirLen > 0
			var elem unsafe.Pointer
			if grown {
				var ok bool
				newKey, newElem, ok := it.m.getWithKey(it.typ, key)
				if !ok {
					// See comment below.
					if it.clearSeq == it.m.clearSeq && !it.typ.Key.Equal(key, key) {
						elem = it.group.elem(it.typ, k)
						if it.typ.IndirectElem() {
							elem = *((*unsafe.Pointer)(elem))
						}
					} else {
						continue
					}
				} else {
					key = newKey
					elem = newElem
				}
			} else {
				elem = it.group.elem(it.typ, k)
				if it.typ.IndirectElem() {
					elem = *((*unsafe.Pointer)(elem))
				}
			}

			it.entryIdx++
			it.key = key
			it.elem = elem
			return
		}
		it.key = nil
		it.elem = nil
		return
	}

	if it.globalDepth != it.m.globalDepth {
		// Directory has grown since the last call to Next. Adjust our
		// directory index.
		//
		// Consider:
		//
		// Before:
		// - 0: *t1
		// - 1: *t2  <- dirIdx
		//
		// After:
		// - 0: *t1a (split)
		// - 1: *t1b (split)
		// - 2: *t2  <- dirIdx
		// - 3: *t2
		//
		// That is, we want to double the current index when the
		// directory size doubles (or quadruple when the directory size
		// quadruples, etc).
		//
		// The actual (randomized) dirIdx is computed below as:
		//
		// dirIdx := (it.dirIdx + it.dirOffset) % it.m.dirLen
		//
		// Multiplication is associative across modulo operations,
		// A * (B % C) = (A * B) % (A * C),
		// provided that A is positive.
		//
		// Thus we can achieve this by adjusting it.dirIdx,
		// it.dirOffset, and it.m.dirLen individually.
		orders := it.m.globalDepth - it.globalDepth
		it.dirIdx <<= orders
		it.dirOffset <<= orders
		// it.m.dirLen was already adjusted when the directory grew.

		it.globalDepth = it.m.globalDepth
	}

	// Continue iteration until we find a full slot.
	for ; it.dirIdx < it.m.dirLen; it.nextDirIdx() {
		// Resolve the table.
		if it.tab == nil {
			dirIdx := int((uint64(it.dirIdx) + it.dirOffset) & uint64(it.m.dirLen-1))
			newTab := it.m.directoryAt(uintptr(dirIdx))
			if newTab.index != dirIdx {
				// Normally we skip past all duplicates of the
				// same entry in the table (see updates to
				// it.dirIdx at the end of the loop below), so
				// this case wouldn't occur.
				//
				// But on the very first call, we have a
				// completely randomized dirIdx that may refer
				// to a middle of a run of tables in the
				// directory. Do a one-time adjustment of the
				// offset to ensure we start at first index for
				// newTable.
				diff := dirIdx - newTab.index
				it.dirOffset -= uint64(diff)
				dirIdx = newTab.index
			}
			it.tab = newTab
		}

		// N.B. Use it.tab, not newTab. It is important to use the old
		// table for key selection if the table has grown. See comment
		// on grown below.

		entryMask := uint64(it.tab.capacity) - 1
		if it.entryIdx > entryMask {
			// Continue to next table.
			continue
		}

		// Fast path: skip matching and directly check if entryIdx is a
		// full slot.
		//
		// In the slow path below, we perform an 8-slot match check to
		// look for full slots within the group.
		//
		// However, with a max load factor of 7/8, each slot in a
		// mostly full map has a high probability of being full. Thus
		// it is cheaper to check a single slot than do a full control
		// match.

		entryIdx := (it.entryIdx + it.entryOffset) & entryMask
		slotIdx := uintptr(entryIdx & (abi.SwissMapGroupSlots - 1))
		if slotIdx == 0 || it.group.data == nil {
			// Only compute the group (a) when we switch
			// groups (slotIdx rolls over) and (b) on the
			// first iteration in this table (slotIdx may
			// not be zero due to entryOffset).
			groupIdx := entryIdx >> abi.SwissMapGroupSlotsBits
			it.group = it.tab.groups.group(it.typ, groupIdx)
		}

		if (it.group.ctrls().get(slotIdx) & ctrlEmpty) == 0 {
			// Slot full.

			key := it.group.key(it.typ, slotIdx)
			if it.typ.IndirectKey() {
				key = *((*unsafe.Pointer)(key))
			}

			grown := it.tab.index == -1
			var elem unsafe.Pointer
			if grown {
				newKey, newElem, ok := it.grownKeyElem(key, slotIdx)
				if !ok {
					// This entry doesn't exist
					// anymore. Continue to the
					// next one.
					goto next
				} else {
					key = newKey
					elem = newElem
				}
			} else {
				elem = it.group.elem(it.typ, slotIdx)
				if it.typ.IndirectElem() {
					elem = *((*unsafe.Pointer)(elem))
				}
			}

			it.entryIdx++
			it.key = key
			it.elem = elem
			return
		}

	next:
		it.entryIdx++

		// Slow path: use a match on the control word to jump ahead to
		// the next full slot.
		//
		// This is highly effective for maps with particularly low load
		// (e.g., map allocated with large hint but few insertions).
		//
		// For maps with medium load (e.g., 3-4 empty slots per group)
		// it also tends to work pretty well. Since slots within a
		// group are filled in order, then if there have been no
		// deletions, a match will allow skipping past all empty slots
		// at once.
		//
		// Note: it is tempting to cache the group match result in the
		// iterator to use across Next calls. However because entries
		// may be deleted between calls later calls would still need to
		// double-check the control value.

		var groupMatch bitset
		for it.entryIdx <= entryMask {
			entryIdx := (it.entryIdx + it.entryOffset) & entryMask
			slotIdx := uintptr(entryIdx & (abi.SwissMapGroupSlots - 1))

			if slotIdx == 0 || it.group.data == nil {
				// Only compute the group (a) when we switch
				// groups (slotIdx rolls over) and (b) on the
				// first iteration in this table (slotIdx may
				// not be zero due to entryOffset).
				groupIdx := entryIdx >> abi.SwissMapGroupSlotsBits
				it.group = it.tab.groups.group(it.typ, groupIdx)
			}

			if groupMatch == 0 {
				groupMatch = it.group.ctrls().matchFull()

				if slotIdx != 0 {
					// Starting in the middle of the group.
					// Ignore earlier groups.
					groupMatch = groupMatch.removeBelow(slotIdx)
				}

				// Skip over groups that are composed of only empty or
				// deleted slots.
				if groupMatch == 0 {
					// Jump past remaining slots in this
					// group.
					it.entryIdx += abi.SwissMapGroupSlots - uint64(slotIdx)
					continue
				}

				i := groupMatch.first()
				it.entryIdx += uint64(i - slotIdx)
				if it.entryIdx > entryMask {
					// Past the end of this table's iteration.
					continue
				}
				entryIdx += uint64(i - slotIdx)
				slotIdx = i
			}

			key := it.group.key(it.typ, slotIdx)
			if it.typ.IndirectKey() {
				key = *((*unsafe.Pointer)(key))
			}

			// If the table has changed since the last
			// call, then it has grown or split. In this
			// case, further mutations (changes to
			// key->elem or deletions) will not be visible
			// in our snapshot table. Instead we must
			// consult the new table by doing a full
			// lookup.
			//
			// We still use our old table to decide which
			// keys to lookup in order to avoid returning
			// the same key twice.
			grown := it.tab.index == -1
			var elem unsafe.Pointer
			if grown {
				newKey, newElem, ok := it.grownKeyElem(key, slotIdx)
				if !ok {
					// This entry doesn't exist anymore.
					// Continue to the next one.
					groupMatch = groupMatch.removeFirst()
					if groupMatch == 0 {
						// No more entries in this
						// group. Continue to next
						// group.
						it.entryIdx += abi.SwissMapGroupSlots - uint64(slotIdx)
						continue
					}

					// Next full slot.
					i := groupMatch.first()
					it.entryIdx += uint64(i - slotIdx)
					continue
				} else {
					key = newKey
					elem = newElem
				}
			} else {
				elem = it.group.elem(it.typ, slotIdx)
				if it.typ.IndirectElem() {
					elem = *((*unsafe.Pointer)(elem))
				}
			}

			// Jump ahead to the next full slot or next group.
			groupMatch = groupMatch.removeFirst()
			if groupMatch == 0 {
				// No more entries in
				// this group. Continue
				// to next group.
				it.entryIdx += abi.SwissMapGroupSlots - uint64(slotIdx)
			} else {
				// Next full slot.
				i := groupMatch.first()
				it.entryIdx += uint64(i - slotIdx)
			}

			it.key = key
			it.elem = elem
			return
		}

		// Continue to next table.
	}

	it.key = nil
	it.elem = nil
	return
}
```

1. 处理小map，只有一个group（dirIdx < 0）
    1. 偏移量随机化，然后开始遍历
    2. 遍历过程可能会发生升级，依然用旧的进行遍历
    3. 只是会去查最新的数据
2. 如果迭代的过程中，map扩容了（it.globalDepth != it.m.globalDepth）
    1. 迭代器也要调整当前的目录指针
    2. 如果目录扩大了2^N倍，那么当前索引也左移N位
3. 主循环——表级遍历
    1. 确定目标表
    2. 边界检查
    3. 快速路径：迭代器先盲猜当前的槽位（Slot）就是满的，命中了就返回
    4. 慢路径：如果没命中，就用SIMD去匹配