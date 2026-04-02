
```go
// getWithKey performs a lookup of key, returning a pointer to the version of
// the key in the map in addition to the element.
//
// This is relevant when multiple different key values compare equal (e.g.,
// +0.0 and -0.0). When a grow occurs during iteration, iteration perform a
// lookup of keys from the old group in the new group in order to correctly
// expose updated elements. For NeedsKeyUpdate keys, iteration also must return
// the new key value, not the old key value.
// hash must be the hash of the key.
// getWithKey 执行键的查找，除了返回元素外，还会返回指向 map 中该键版本的指针。
//
// 当多个不同的键值比较相等时（例如 +0.0 和 -0.0），这就非常有用。
// 当迭代期间发生扩容时，迭代器会在新组中查找旧组的键，以便正确暴露更新后的元素。
// 对于需要更新键（NeedsKeyUpdate）的类型，迭代还必须 return 新的键值，而不是旧的键值。
// hash 必须是该键的哈希值。
func (t *table) getWithKey(typ *abi.SwissMapType, hash uintptr, key unsafe.Pointer) (unsafe.Pointer, unsafe.Pointer, bool) {
	// To find the location of a key in the table, we compute hash(key). From
	// h1(hash(key)) and the capacity, we construct a probeSeq that visits
	// every group of slots in some interesting order. See [probeSeq].
	//
	// We walk through these indices. At each index, we select the entire
	// group starting with that index and extract potential candidates:
	// occupied slots with a control byte equal to h2(hash(key)). The key
	// at candidate slot i is compared with key; if key == g.slot(i).key
	// we are done and return the slot; if there is an empty slot in the
	// group, we stop and return an error; otherwise we continue to the
	// next probe index. Tombstones (ctrlDeleted) effectively behave like
	// full slots that never match the value we're looking for.
	//
	// The h2 bits ensure when we compare a key we are likely to have
	// actually found the object. That is, the chance is low that keys
	// compare false. Thus, when we search for an object, we are unlikely
	// to call Equal many times. This likelihood can be analyzed as follows
	// (assuming that h2 is a random enough hash function).
	//
	// Let's assume that there are k "wrong" objects that must be examined
	// in a probe sequence. For example, when doing a find on an object
	// that is in the table, k is the number of objects between the start
	// of the probe sequence and the final found object (not including the
	// final found object). The expected number of objects with an h2 match
	// is then k/128. Measurements and analysis indicate that even at high
	// load factors, k is less than 32, meaning that the number of false
	// positive comparisons we must perform is less than 1/8 per find.
	// 为了在表中找到键的位置，我们计算 hash(key)。
	// 根据 h1(hash(key)) 和容量，我们构造一个探测序列 (probeSeq)，
	// 该序列会按某种特定的顺序访问每个槽位组。详见 [probeSeq]。
	//
	// 我们遍历这些索引。在每个索引处，我们选择以此索引开始的整个组，
	// 并提取潜在的候选条目：即控制字节等于 h2(hash(key)) 的已占用槽位。
	// 将候选槽位 i 处的键与目标键进行比较；如果 key == g.slot(i).key，则查找完成并返回该槽位；
	// 如果组中存在空槽位，则停止探测并返回未找到；否则继续下一个探测索引。
	// “墓碑”（ctrlDeleted）的效果类似于永远不会与我们寻找的值匹配的已满槽位。
	//
	// h2 位确保我们在比较键时，很有可能确实找到了目标对象。
	// 也就是说，键比较结果为 false 的概率很低。
	// 因此，在我们搜索对象时，不太可能多次调用 Equal 函数。
	// 这种可能性可以分析如下（假设 h2 是一个足够随机的哈希函数）：
	//
	// 假设在探测序列中必须检查 k 个“错误”对象。
	// 例如，在对表中已存在的对象进行查找时，k 是探测序列起点与最终找到的对象之间的对象数量（不包括最终找到的对象）。
	// 那么 h2 匹配的对象的预期数量为 k/128。
	// 测量和分析表明，即使在高负载因子下，k 通常也小于 32，
	// 这意味着我们每次查找时必须执行的误报比较次数小于 1/8。
	seq := makeProbeSeq(h1(hash), t.groups.lengthMask)
	for ; ; seq = seq.next() {
		g := t.groups.group(typ, seq.offset)

		match := g.ctrls().matchH2(h2(hash))

		for match != 0 {
			i := match.first()

			slotKey := g.key(typ, i)
			if typ.IndirectKey() {
				slotKey = *((*unsafe.Pointer)(slotKey))
			}
			if typ.Key.Equal(key, slotKey) {
				slotElem := g.elem(typ, i)
				if typ.IndirectElem() {
					slotElem = *((*unsafe.Pointer)(slotElem))
				}
				return slotKey, slotElem, true
			}
			match = match.removeFirst()
		}

		match = g.ctrls().matchEmpty()
		if match != 0 {
			// Finding an empty slot means we've reached the end of
			// the probe sequence.
			// 找到空槽位意味着我们已经到达了探测序列的末尾。
			return nil, nil, false
		}
	}
}

func (t *table) getWithoutKey(typ *abi.SwissMapType, hash uintptr, key unsafe.Pointer) (unsafe.Pointer, bool) {
	seq := makeProbeSeq(h1(hash), t.groups.lengthMask)
	for ; ; seq = seq.next() {
		g := t.groups.group(typ, seq.offset)

		match := g.ctrls().matchH2(h2(hash))

		for match != 0 {
			i := match.first()

			slotKey := g.key(typ, i)
			if typ.IndirectKey() {
				slotKey = *((*unsafe.Pointer)(slotKey))
			}
			if typ.Key.Equal(key, slotKey) {
				slotElem := g.elem(typ, i)
				if typ.IndirectElem() {
					slotElem = *((*unsafe.Pointer)(slotElem))
				}
				return slotElem, true
			}
			match = match.removeFirst()
		}

		match = g.ctrls().matchEmpty()
		if match != 0 {
			// Finding an empty slot means we've reached the end of
			// the probe sequence.
			// 找到空槽位意味着我们已经到达了探测序列的末尾。
			return nil, false
		}
	}
}
```

查找步骤：
1. 根据哈希值的高位构造探测序列
2. 循环遍历
    1. SIMD快速匹配候选人
    2. 逐个比较候选人的键
        1. 如果找到，返回值
    3. 如果未找到，看是否有空元素
        1. 有则说明探测终止，直接返回未找到
        2. 无空元素，那就根据探测序列跳到下一个Group，继续找

键和值可以直接存在 Map 的连续内存块里，如果太大也可以通过指针间接存储


```go
// probeSeq maintains the state for a probe sequence that iterates through the
// groups in a table. The sequence is a triangular progression of the form
//
//	p(i) := (i^2 + i)/2 + hash (mod mask+1)
//
// The sequence effectively outputs the indexes of *groups*. The group
// machinery allows us to check an entire group with minimal branching.
//
// It turns out that this probe sequence visits every group exactly once if
// the number of groups is a power of two, since (i^2+i)/2 is a bijection in
// Z/(2^m). See https://en.wikipedia.org/wiki/Quadratic_probing
// probeSeq 维护探测序列的状态，该序列用于遍历表中的组。
// 该序列是一个三角数增长的形式：
//
//	p(i) := (i^2 + i)/2 + hash (mod mask+1)
//
// 该序列实际上输出的是 *组* 的索引。
// 组机制允许我们以极少的分支逻辑检查整个组。
//
// 事实证明，如果组的数量是 2 的幂，这个探测序列会恰好访问每个组一次，
// 因为 (i^2+i)/2 是 Z/(2^m) 空间中的一种双射。
// 参见 https://en.wikipedia.org/wiki/Quadratic_probing
type probeSeq struct {
	mask   uint64
	offset uint64
	index  uint64
}

func makeProbeSeq(hash uintptr, mask uint64) probeSeq {
	return probeSeq{
		mask:   mask,
		offset: uint64(hash) & mask,
		index:  0,
	}
}

func (s probeSeq) next() probeSeq {
	s.index++
	s.offset = (s.offset + s.index) & s.mask
	return s
}
```

该序列用于遍历表中的组

这个“三角数”公式有两个神级优点：

不挑食（分布均匀）：它跳跃的距离越来越长，能很快跳出“拥挤区”。
不漏掉（刚好走一圈）：数学上证明了，只要你的房间总数是 2 的幂（比如 16, 32, 64），这个公式产生的序列会恰好经过每一个房间一次，且不重复，直到回到起点。

```go
// Portable implementation of matchH2.
//
// Note: On AMD64, this is an intrinsic implemented with SIMD instructions. See
// note on bitset about the packed instrinsified return value.
func ctrlGroupMatchH2(g ctrlGroup, h uintptr) bitset {
    // NB: This generic matching routine produces false positive matches when
    // h is 2^N and the control bytes have a seq of 2^N followed by 2^N+1. For
    // example: if ctrls==0x0302 and h=02, we'll compute v as 0x0100. When we
    // subtract off 0x0101 the first 2 bytes we'll become 0xffff and both be
    // considered matches of h. The false positive matches are not a problem,
    // just a rare inefficiency. Note that they only occur if there is a real
    // match and never occur on ctrlEmpty, or ctrlDeleted. The subsequent key
    // comparisons ensure that there is no correctness issue.
    v := uint64(g) ^ (bitsetLSB * uint64(h))
    return bitset(((v - bitsetLSB) &^ v) & bitsetMSB)
}
```

在 ARM64 架构下，是在寄存器内实现 SIMD
在 AMD64 架构下，你看到的这段 Go 代码（Portable 实现）其实根本不会运行。
编译器会“偷梁换柱”，将这个函数替换成极其高效的硬件指令SIMD