## sync.Map vs 普通Map

| 特性 | 普通Map + Mutex | sync.Map |
|------|----------------|----------|
| 读性能 | 中等（需要读锁） | **极高**（无锁读） |
| 写性能 | 中等（需要写锁） | 中等 |
| 内存使用 | 低 | **较高**（复杂结构） |
| 类型安全 | **高**（编译时检查） | 低（interface{}类型） |
| 使用复杂度 | 高（需要管理锁） | **低**（内置并发控制） |
| 适用场景 | 通用场景 | 特定并发场景 |

---

## 适用场景分析

### 🟢 强烈推荐使用sync.Map

#### 场景1：一写多读
**特点**：同一个key只写一次，之后大量读取

#### 场景2：多goroutine操作不同key
**特点**：各goroutine操作的key集合几乎不重叠

### 🔴 不推荐使用sync.Map的场景

#### 场景1：频繁删除操作

#### 场景2：大量随机读写

#### 场景3：需要类型安全
```go
// 不推荐：需要类型安全
type User struct {
    ID   int
    Name string
}

// sync.Map只能存interface{}，类型不安全
var m sync.Map
m.Store("user1", User{ID: 1, Name: "Alice"})
```

---

## 核心架构详解

### 设计理念
sync.Map使用**哈希trie（前缀树）** 结构，通过空间换时间的方式实现高效并发访问。

### 关键设计决策
```go
// 常量定义
const (
    nChildrenLog2 = 4     // 每层使用4位哈希
    nChildren     = 1 << 4  // 每层16个子节点
    nChildrenMask = nChildren - 1
)
```

### 核心数据结构
```go
// Map 是 sync.Map 的主要结构
type Map struct {
    _       noCopy  // 防止复制
    m       HashTrieMap[any, any]  // 哈希trie实现
}

// HashTrieMap 哈希trie的核心实现
type HashTrieMap[K comparable, V any] struct {
    inited   atomic.Uint32    // 初始化标志
    initMu   sync.Mutex      // 初始化锁
    root     atomic.Pointer[indirect[K, V]]  // 根节点（原子指针）
    keyHash  hashFunc        // 哈希函数
    valEqual equalFunc       // 值比较函数
}

// indirect 内部节点（非叶子节点）
type indirect[K comparable, V any] struct {
    node[K, V]
    dead    atomic.Bool      // 标记节点是否已废弃
    mu      sync.Mutex       // 节点级锁
    parent  *indirect[K, V]   // 父节点
    children [16]atomic.Pointer[node[K, V]]  // 16个子节点，每个指向 node（可能是 indirect 或 entry）
}

// entry 叶子节点（存储实际数据）
type entry[K comparable, V any] struct {
    node[K, V]
    overflow atomic.Pointer[entry[K, V]]  // 冲突处理链表
    key      K
    value    V
}

// node 是节点的公共头，通过 isEntry 区分实际是 entry 还是 indirect。
type node[K comparable, V any] struct {
	// true 表示实际是 entry（叶子），false 表示是 indirect（内部节点）
	isEntry bool
}
```

### 工作原理

#### 1. 查找流程
1. 计算key的64位哈希值
2. hashShift := 8 * goarch.PtrSize：
    - 64 位系统：hashShift = 64
    - 32 位系统：hashShift = 32
3. 循环按块吃掉 hash 高位：
    - hashShift -= nChildrenLog2，nChildrenLog2=4
    - 选槽位：idx := (hash >> hashShift) & nChildrenMask，nChildrenMask=15
    - n := i.children[idx].Load() 读取这一格的节点
4. 根据节点类型处理：
    - nil: key不存在
    - indirect: 继续向下查找
    - entry: 比对key，匹配则返回
```go
// Load returns the value stored in the map for a key, or nil if no
// value is present.
// The ok result indicates whether value was found in the map.
func (ht *HashTrieMap[K, V]) Load(key K) (value V, ok bool) {
	ht.init()
	// 计算 hash
	hash := ht.keyHash(abi.NoEscape(unsafe.Pointer(&key)), ht.seed)

	i := ht.root.Load()
    // goarch.PtrSize: 4 on 32-bit systems, 8 on 64-bit
	hashShift := 8 * goarch.PtrSize
	for hashShift != 0 {
		hashShift -= nChildrenLog2

		n := i.children[(hash>>hashShift)&nChildrenMask].Load()
		if n == nil {
			return *new(V), false
		}
		if n.isEntry {
			return n.entry().lookup(key)
		}
		i = n.indirect()
	}
	panic("internal/sync.HashTrieMap: ran out of hash bits while iterating")
}

func (e *entry[K, V]) lookup(key K) (V, bool) {
	for e != nil {
		if e.key == key {
			return e.value, true
		}
		e = e.overflow.Load()
	}
	return *new(V), false
}
```

#### 2. 插入流程

1. 按查找路径找到插入位置
2. 锁定插入位置的上一个indirect节点
3. 处理三种情况：
   - 槽为空：创建新entry
   - 槽有entry且key匹配：更新值
   - 槽有entry但key不匹配：需要扩展

```go
for {
    // Find the key or a candidate location for insertion.
    ...

    // Grab the lock and double-check what we saw.
    i.mu.Lock()
    n = slot.Load()
    if (n == nil || n.isEntry) && !i.dead.Load() {
        // What we saw is still true, so we can continue with the insert.
        break
    }
    // We have to start over.
    i.mu.Unlock()
}

var zero V
var oldEntry *entry[K, V]
if n != nil {
    // Swap if the keys compare.
    oldEntry = n.entry()
    newEntry, old, swapped := oldEntry.swap(key, new)
    if swapped {
        slot.Store(&newEntry.node)
        return old, true
    }
}
// The keys didn't compare, so we're doing an insertion.
newEntry := newEntryNode(key, new)
if oldEntry == nil {
    // Easy case: create a new entry and store it.
    slot.Store(&newEntry.node)
} else {
    // We possibly need to expand the entry already there into one or more new nodes.
    //
    // Publish the node last, which will make both oldEntry and newEntry visible. We
    // don't want readers to be able to observe that oldEntry isn't in the tree.
    slot.Store(ht.expand(oldEntry, newEntry, hash, hashShift, i))
}
return zero, false
```

#### 3. 扩展机制
当同一个槽位有多个key时（哈希冲突）：
1. 创建新的indirect层
2. 按更低位哈希值重新分配
3. 处理真冲突：挂到overflow链表

```go
func (ht *HashTrieMap[K, V]) expand(oldEntry, newEntry *entry[K, V], newHash uintptr, hashShift uint, parent *indirect[K, V]) *node[K, V] {
	// Check for a hash collision.
	oldHash := ht.keyHash(unsafe.Pointer(&oldEntry.key), ht.seed)
	if oldHash == newHash {
		// Store the old entry in the new entry's overflow list, then store
		// the new entry.
		newEntry.overflow.Store(oldEntry)
		return &newEntry.node
	}
	// We have to add an indirect node. Worse still, we may need to add more than one.
	newIndirect := newIndirectNode(parent)
	top := newIndirect
	for {
		if hashShift == 0 {
			panic("internal/sync.HashTrieMap: ran out of hash bits while inserting")
		}
		hashShift -= nChildrenLog2 // hashShift is for the level parent is at. We need to go deeper.
		oi := (oldHash >> hashShift) & nChildrenMask
		ni := (newHash >> hashShift) & nChildrenMask
		if oi != ni {
			newIndirect.children[oi].Store(&oldEntry.node)
			newIndirect.children[ni].Store(&newEntry.node)
			break
		}
		nextIndirect := newIndirectNode(newIndirect)
		newIndirect.children[oi].Store(&nextIndirect.node)
		newIndirect = nextIndirect
	}
	return &top.node
}
```

---

## API使用指南

### 基本操作
```go
var m sync.Map

// 存储键值对
m.Store("key1", "value1")
m.Store(42, "answer")

// 读取值
if val, ok := m.Load("key1"); ok {
    fmt.Println(val.(string))
}

// 读取或设置默认值
val, _ := m.LoadOrStore("key2", "default")
fmt.Println(val)

// 删除值
m.Delete("key1")

// 遍历所有键值对
m.Range(func(key, value interface{}) bool {
    fmt.Printf("%v: %v\n", key, value)
    return true // 继续遍历
})
```

### 高级操作
```go
// CompareAndSwap 原子操作
m.Store("counter", 0)
if m.CompareAndSwap("counter", 0, 1) {
    fmt.Println("CAS成功")
}

// CompareAndDelete 原子删除
m.Store("temp", "value")
if m.CompareAndDelete("temp", "value") {
    fmt.Println("删除成功")
}
```


---
### 性能特点

#### 读性能
```
sync.Map优势场景：
- 读操作 >> 写操作
- key不经常变化
- 并发度较高

sync.Map劣势场景：
- 频繁的写操作
- key经常变化
- 并发度低
```

#### 写性能
```
sync.Map vs 普通Map + RWMutex：
- 写操作性能相近
- 但sync.Map更简单，不易出错
```

---
## 常见误区

### 误区1：sync.Map总是更快
```go
// 错误认知：sync.Map比普通map + 锁总是更快
// 实际：sync.Map在特定场景下才更优
```

### 误区2：忽略类型安全问题
```go
// 危险：类型断言可能导致panic
func badTypeCheck() {
    m := sync.Map{}
    m.Store("key", 42)

    val, _ := m.Load("key")
    // 可能panic，如果val不是int
    num := val.(int)
}
```

### 误区3：过度依赖sync.Map
```go
// 不必要的使用
func unnecessaryUse() {
    // 这个场景普通map + 锁更好
    var data = make(map[string]int)
    var mu sync.Mutex

    // 简单的计数器
    mu.Lock()
    data["count"]++
    mu.Unlock()
}
```

### 误区4：忽略内存开销
```go
// sync.Map内存开销较大
var m sync.Map  // 复杂结构，内存占用高

var simpleMap = make(map[string]int)  // 内存占用低
var mu sync.RWMutex
```

---

## 总结
### 选择决策树
```
是否需要并发安全？
├── 否 → 使用普通map
└── 是 → 并发程度如何？
    ├── 低 → 普通map + Mutex/RWMutex
    └── 高 → 操作模式如何？
        ├── 读多写少 → sync.Map
        ├── 写多读少 → 普通map + RWMutex
        └── 随机读写 → 按具体性能测试选择
```

sync.Map是一个强大的工具，但不是万能的。理解其原理和适用场景，才能在合适的时机选择合适的解决方案。