
```go
// If m is non-nil, it should be used rather than allocating.
//
// maxAlloc should be runtime.maxAlloc.
//
// TODO(prattmic): Put maxAlloc somewhere accessible.
func NewMap(mt *abi.SwissMapType, hint uintptr, m *Map, maxAlloc uintptr) *Map {
	if m == nil {
		m = new(Map)
	}

	m.seed = uintptr(rand())

	if hint <= abi.SwissMapGroupSlots {
		// A small map can fill all 8 slots, so no need to increase
		// target capacity.
		//
		// In fact, since an 8 slot group is what the first assignment
		// to an empty map would allocate anyway, it doesn't matter if
		// we allocate here or on the first assignment.
		//
		// Thus we just return without allocating. (We'll save the
		// allocation completely if no assignment comes.)

		// Note that the compiler may have initialized m.dirPtr with a
		// pointer to a stack-allocated group, in which case we already
		// have a group. The control word is already initialized.

		return m
	}

	// Full size map.

	// Set initial capacity to hold hint entries without growing in the
	// average case.
	targetCapacity := (hint * abi.SwissMapGroupSlots) / maxAvgGroupLoad
	if targetCapacity < hint { // overflow
		return m // return an empty map.
	}

	dirSize := (uint64(targetCapacity) + maxTableCapacity - 1) / maxTableCapacity
	dirSize, overflow := alignUpPow2(dirSize)
	if overflow || dirSize > uint64(math.MaxUintptr) {
		return m // return an empty map.
	}

	// Reject hints that are obviously too large.
	groups, overflow := math.MulUintptr(uintptr(dirSize), maxTableCapacity)
	if overflow {
		return m // return an empty map.
	} else {
		mem, overflow := math.MulUintptr(groups, mt.GroupSize)
		if overflow || mem > maxAlloc {
			return m // return an empty map.
		}
	}

	m.globalDepth = uint8(sys.TrailingZeros64(dirSize))
	m.globalShift = depthToShift(m.globalDepth)

	directory := make([]*table, dirSize)

	for i := range directory {
		// TODO: Think more about initial table capacity.
		directory[i] = newTable(mt, uint64(targetCapacity)/dirSize, i, m.globalDepth)
	}

	m.dirPtr = unsafe.Pointer(&directory[0])
	m.dirLen = len(directory)

	return m
}
```

1. 分配Map对象
2. 如果只存8个以内的元素，直接返回
    1. 编译器介入，如果比较小，那么可能已经分配好了一个group空间，并直接塞给了dirPtr
    2. 如果编译器没分配，我也不分配
3. 如果大于8个，进行计算分配，然后实例化目录与表

