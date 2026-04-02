```go
func (t *table) Delete(typ *abi.SwissMapType, m *Map, hash uintptr, key unsafe.Pointer) {
	seq := makeProbeSeq(h1(hash), t.groups.lengthMask)
	for ; ; seq = seq.next() {
		g := t.groups.group(typ, seq.offset)
		match := g.ctrls().matchH2(h2(hash))

		for match != 0 {
			i := match.first()

			slotKey := g.key(typ, i)
			origSlotKey := slotKey
			if typ.IndirectKey() {
				slotKey = *((*unsafe.Pointer)(slotKey))
			}

			if typ.Key.Equal(key, slotKey) {
				t.used--
				m.used--

				if typ.IndirectKey() {
					// Clearing the pointer is sufficient.
					*(*unsafe.Pointer)(origSlotKey) = nil
				} else if typ.Key.Pointers() {
					// Only bothing clear the key if there
					// are pointers in it.
					typedmemclr(typ.Key, slotKey)
				}

				slotElem := g.elem(typ, i)
				if typ.IndirectElem() {
					// Clearing the pointer is sufficient.
					*(*unsafe.Pointer)(slotElem) = nil
				} else {
					// Unlike keys, always clear the elem (even if
					// it contains no pointers), as compound
					// assignment operations depend on cleared
					// deleted values. See
					// https://go.dev/issue/25936.
					typedmemclr(typ.Elem, slotElem)
				}

				// Only a full group can appear in the middle
				// of a probe sequence (a group with at least
				// one empty slot terminates probing). Once a
				// group becomes full, it stays full until
				// rehashing/resizing. So if the group isn't
				// full now, we can simply remove the element.
				// Otherwise, we create a tombstone to mark the
				// slot as deleted.
				if g.ctrls().matchEmpty() != 0 {
					g.ctrls().set(i, ctrlEmpty)
					t.growthLeft++
				} else {
					g.ctrls().set(i, ctrlDeleted)
				}

				t.checkInvariants(typ, m)
				return
			}
			match = match.removeFirst()
		}

		match = g.ctrls().matchEmpty()
		if match != 0 {
			// Finding an empty slot means we've reached the end of
			// the probe sequence.
			return
		}
	}
}
```

1. 根据哈希值的高位构造探测序列
2. 循环遍历
    1. SIMD快速匹配候选人
    2. 逐个比较候选人的键
        1. 如果找到, 是指针就清零, 不是指针就清内存
        2. 未找到，则继续下一个Group，直到到达终点
    3. 清空后，看组里有没有空位
        1. 有，说明是探测序列终点，可以置metadata为空
        2. 没有，说明组内满员，不是终点，置为墓碑（ctrlDeleted）