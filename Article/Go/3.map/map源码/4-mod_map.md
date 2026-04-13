```go
// PutSlot returns a pointer to the element slot where an inserted element
// should be written.
//
// PutSlot never returns nil.
func (m *Map) PutSlot(typ *abi.SwissMapType, key unsafe.Pointer) unsafe.Pointer {
	if m.writing != 0 {
		fatal("concurrent map writes")
	}

	hash := typ.Hasher(key, m.seed)

	// Set writing after calling Hasher, since Hasher may panic, in which
	// case we have not actually done a write.
	m.writing ^= 1 // toggle, see comment on writing

	if m.dirPtr == nil {
		m.growToSmall(typ)
	}

	if m.dirLen == 0 {
		if m.used < abi.SwissMapGroupSlots {
			elem := m.putSlotSmall(typ, hash, key)

			if m.writing == 0 {
				fatal("concurrent map writes")
			}
			m.writing ^= 1

			return elem
		}

		// Can't fit another entry, grow to full size map.
		//
		// TODO(prattmic): If this is an update to an existing key then
		// we actually don't need to grow.
		m.growToTable(typ)
	}

	for {
		idx := m.directoryIndex(hash)
		elem, ok := m.directoryAt(idx).PutSlot(typ, m, hash, key)
		if !ok {
			continue
		}

		if m.writing == 0 {
			fatal("concurrent map writes")
		}
		m.writing ^= 1

		return elem
	}
}
```

1. 如果是空，则growToSmall
2. 如果是指向一个group，就加数据；位置满了，就growToTable

```go
// PutSlot returns a pointer to the element slot where an inserted element
// should be written, and ok if it returned a valid slot.
//
// PutSlot returns ok false if the table was split and the Map needs to find
// the new table.
//
// hash must be the hash of key.
func (t *table) PutSlot(typ *abi.SwissMapType, m *Map, hash uintptr, key unsafe.Pointer) (unsafe.Pointer, bool) {
	seq := makeProbeSeq(h1(hash), t.groups.lengthMask)

	// As we look for a match, keep track of the first deleted slot we
	// find, which we'll use to insert the new entry if necessary.
	var firstDeletedGroup groupReference
	var firstDeletedSlot uintptr

	for ; ; seq = seq.next() {
		g := t.groups.group(typ, seq.offset)
		match := g.ctrls().matchH2(h2(hash))

		// Look for an existing slot containing this key.
		for match != 0 {
			i := match.first()

			slotKey := g.key(typ, i)
			if typ.IndirectKey() {
				slotKey = *((*unsafe.Pointer)(slotKey))
			}
			if typ.Key.Equal(key, slotKey) {
				if typ.NeedKeyUpdate() {
					typedmemmove(typ.Key, slotKey, key)
				}

				slotElem := g.elem(typ, i)
				if typ.IndirectElem() {
					slotElem = *((*unsafe.Pointer)(slotElem))
				}

				t.checkInvariants(typ, m)
				return slotElem, true
			}
			match = match.removeFirst()
		}

		// No existing slot for this key in this group. Is this the end
		// of the probe sequence?
		match = g.ctrls().matchEmptyOrDeleted()
		if match == 0 {
			continue // nothing but filled slots. Keep probing.
		}
		i := match.first()
		if g.ctrls().get(i) == ctrlDeleted {
			// There are some deleted slots. Remember
			// the first one, and keep probing.
			if firstDeletedGroup.data == nil {
				firstDeletedGroup = g
				firstDeletedSlot = i
			}
			continue
		}
		// We've found an empty slot, which means we've reached the end of
		// the probe sequence.

		// If we found a deleted slot along the way, we can
		// replace it without consuming growthLeft.
		if firstDeletedGroup.data != nil {
			g = firstDeletedGroup
			i = firstDeletedSlot
			t.growthLeft++ // will be decremented below to become a no-op.
		}

		// If there is room left to grow, just insert the new entry.
		if t.growthLeft > 0 {
			slotKey := g.key(typ, i)
			if typ.IndirectKey() {
				kmem := newobject(typ.Key)
				*(*unsafe.Pointer)(slotKey) = kmem
				slotKey = kmem
			}
			typedmemmove(typ.Key, slotKey, key)

			slotElem := g.elem(typ, i)
			if typ.IndirectElem() {
				emem := newobject(typ.Elem)
				*(*unsafe.Pointer)(slotElem) = emem
				slotElem = emem
			}

			g.ctrls().set(i, ctrl(h2(hash)))
			t.growthLeft--
			t.used++
			m.used++

			t.checkInvariants(typ, m)
			return slotElem, true
		}

		t.rehash(typ, m)
		return nil, false
	}
}
```

1. 根据哈希值的高位构造探测序列
2. 循环遍历
    1. SIMD快速匹配候选人
    2. 逐个比较候选人的键
        1. 如果找到，直接更新，退出
    3. 如果未找到，看是否有墓碑
        1. 有则记录第一个墓碑在哪，继续找
    4. 未找到，并且到达终点，优先填坑墓碑，不行就填坑空位
    5. 没位置则进行扩容

我刚开始还会想，遇到墓碑，直接填就行了，为啥还要继续探测？
核心原因：Key 可能在墓碑后面
直接填可能会导致key重复