# interface 源码

## 前言

本文是 **Go 1.25 运行时**里与接口值相关的阅读笔记，主线在 **`$GOROOT/src/runtime/iface.go`** 与 **`$GOROOT/src/runtime/runtime2.go`**，类型描述与 `ITab` 定义在 **`$GOROOT/src/internal/abi`**（`iface.go`、`type.go`）。从「接口值在内存里长什么样」写到 `getitab`、装箱 `convT*`、断言 `assertE2I*`、`typeAssert` / `interfaceSwitch` 与缓存；不展开 `cmd/compile` 的 SSA 全链路。

---

## 1. 两种接口值：`iface` 与 `eface`

带方法的接口与 `any` / `interface{}` 在运行时用了两套布局（`runtime/runtime2.go`）：

```go
// 非空接口（接口类型上声明了方法）：第一个字是 *itab（动态类型 + 派发表），第二个字是 data。
type iface struct {
	tab  *itab
	data unsafe.Pointer
}

// 空接口 any：第一个字是 *_type（仅动态类型描述），第二个字是 data。
type eface struct {
	_type *_type
	data  unsafe.Pointer
}
```

`efaceOf` 把 `*any` 强转成 `*eface`，便于在 runtime 里拆开空接口：

```go
func efaceOf(ep *any) *eface {
	return (*eface)(unsafe.Pointer(ep))
}
```

`internal/abi` 里与之对应的名字是 `NonEmptyInterface` / `EmptyInterface`，便于和编译器/链接器约定对齐。

---

## 2. `itab`：动态类型 + 方法代码指针

非空接口（像 io.Reader 这种带方法的接口）在运行时怎么表示「当前具体是哪种类型、以及怎么调到对应方法」。
`runtime` 里 `itab` 是 **`abi.ITab` 的类型别名**（`runtime/runtime2.go` 中 `type itab = abi.ITab`）。

```go
// internal/abi/iface.go — ITab
type ITab struct {
	Inter *InterfaceType  // 为哪个接口类型准备的（方法列表、包路径等）
	Type  *Type			// 当前装进去的具体类型是哪一个（int、*File、自定义 struct…）
	Hash  uint32     // copy of Type.Hash；用于 type switch 等
	Fun   [1]uintptr // 变长：Fun[0] 起按接口方法顺序存代码指针
}

type InterfaceType struct {
	Type
	PkgPath Name
	Methods []Imethod // 接口上声明了哪些方法；Imethod 含方法名与函数类型描述（与 uncommon 方法匹配用）
}
```


**`ITab` 在解决什么问题**  
源码里某变量类型是接口 `I`，运行时装进去的是具体类型 `T` 的值。
调度时要回答：**对 `I` 的第 k 个方法，应跳到 `T` 的哪段机器码？**  
`ITab` 就是针对**这一对** `(I, T)` 的缓存：`Inter` 指向接口 `I` 的描述，`Type` 指向具体类型 `T` 的描述，`Fun` 里按 **`I` 的方法顺序**排好「跳转地址」，调用接口方法时按下标取 `Fun[i]` 即可。

以下为 **`runtime/iface.go` 中 `itabInit` 主干**

```go
// 检查“具体类型 T 是否实现了接口 I”，如果实现了就把每个接口方法对应的函数地址填到 m.Fun[k]
func itabInit(m *itab, firstTime bool) string {
	inter := m.Inter
	typ := m.Type
	x := typ.Uncommon()

	ni := len(inter.Methods)
	nt := int(x.Mcount)
	// 具体类型 T 的方法表（uncommon 区），按运行时布局切成可遍历切片。
	xmhdr := (*[1 << 16]abi.Method)(add(unsafe.Pointer(x), uintptr(x.Moff)))[:nt:nt]
	// j 是“类型方法表”的游标：只前进不回退，配合 k 做线性归并，而不是 O(ni*nt) 的全量回扫。
	j := 0
	// 把变长 Fun 区域视为长度 ni 的切片，按接口方法顺序写入目标代码指针。
	methods := (*[1 << 16]unsafe.Pointer)(unsafe.Pointer(&m.Fun[0]))[:ni:ni]
	// 第 0 个方法单独暂存：失败场景下保持 m.Fun[0]==0 作为“未实现”标记。
	var fun0 unsafe.Pointer
imethods:
	for k := 0; k < ni; k++ {
		i := &inter.Methods[k]
		itype := toRType(&inter.Type).typeOff(i.Typ)
		name := toRType(&inter.Type).nameOff(i.Name)
		iname := name.Name()
		ipkg := pkgPath(name)
		if ipkg == "" {
			ipkg = inter.PkgPath.Name()
		}
		for ; j < nt; j++ {
			t := &xmhdr[j]
			rtyp := toRType(typ)
			tname := rtyp.nameOff(t.Name)
			// 先匹配“方法签名 + 方法名”。
			if rtyp.typeOff(t.Mtyp) == itype && tname.Name() == iname {
				pkgPath := pkgPath(tname)
				if pkgPath == "" {
					pkgPath = rtyp.nameOff(x.PkgPath).Name()
				}
				// 再做可见性校验：导出方法或同包方法才算实现。
				if tname.IsExported() || pkgPath == ipkg {
					ifn := rtyp.textOff(t.Ifn)
					if k == 0 {
						// 第 0 个槽先不落盘，避免中途失败把 Fun[0] 写成非 0。
						fun0 = ifn
					} else if firstTime {
						methods[k] = ifn
					}
					// 当前接口方法匹配成功，继续匹配下一个接口方法。
					continue imethods
				}
			}
		}
		// 某个接口方法没找到实现：返回缺失方法名；调用方据此构造错误信息。
		return iname
	}
	if firstTime {
		// 全部匹配成功后，最后一步再写 Fun[0]，提交“该 itab 可用”。
		m.Fun[0] = uintptr(fun0)
	}
	return ""
}
```

按流程拆开：

1. 拿两份“方法清单”
	- inter.Methods：接口 I 要求的方法列表（必须实现这些）。
	- xmhdr：具体类型 T 真正拥有的方法列表。
2. 双指针扫描匹配
	- 外层 k 遍历接口方法。
	- 内层 j 遍历类型方法，但 j 只前进不回退，是线性扫描，效率更高。
	- 匹配条件不是只看名字，还要看：
		- 方法签名是否一致（itype vs t.Mtyp）
		- 方法名是否一致
		- 可见性是否允许（导出 or 同包）
3. 匹配成功就记录函数地址
	- ifn := rtyp.textOff(t.Ifn) 拿到真正代码地址。
	- 写入 Fun[k]，以后接口调用会跳到这个地址执行。
4. 为什么第一个方法 k==0 不立刻写？
	- 先存到 fun0，最后全部成功再写 m.Fun[0]。
	- 这样 Fun[0]==0 就能作为“这对 (I,T) 不可用/未完整初始化”的标记。
5. 匹配失败会怎样？
	- 只要某个接口方法找不到实现，立刻 return iname（缺失的方法名）。
	- 调用方据此报错（比如 type assertion failed）。


**`Fun` 为什么是 `[1]uintptr` 却又叫「变长」**  
Fun 明明只有 1 个元素，怎么存下接口所有方法？答案是：[1] 只是语法占位，不是实际容量。
真实情况是 runtime 分配 itab 时，会多申请一段尾部空间，把 Fun 当成“变长数组起点”。

**uncommon是什么**
是运行时类型元数据里的 `UncommonType` 区域，可以理解成：“这个类型额外携带的方法相关信息”。

- 为什么叫 uncommon：不是所有类型都需要这块信息，只有“有方法集”的类型才会携带。
- 里面常见字段：方法数量（`Mcount`）、方法表偏移（`Moff`）、包路径等。
- 在 `itabInit` 里会先 `x := typ.Uncommon()`，再用 `x.Mcount/x.Moff` 把具体类型的方法表切出来做匹配。
- 若类型连 `UncommonType` 都没有，通常表示没有可用于实现非空接口的方法集（`getitab` 会快速失败）。


---

## 3. `getitab`：查表、加锁构造、`itab` 缓存

在需要把“接口类型 I + 动态类型 T”配对的时候会调用 `getitab`，典型触发点有：

- 空接口转非空接口（如 `x.(io.Reader)`、`v, ok := x.(MyIface)`，走 `assertE2I/assertE2I2`）。
- `type switch` 里接口分支匹配（对每个 case 接口尝试 `getitab(caseIface, t, true)`）。
- 运行时需要构造非空接口值（`iface.tab` 需要对应 `(I,T)` 的 `itab`）。

一句话：凡是要回答“**T 是否实现 I**，并拿到方法派发表 `Fun`”的地方，都会走到 `getitab`。

下面按源码主干讲（省略非关键分支）：

```go
// 给你一对 (接口类型 I, 具体类型 T)，返回可用于动态派发的 *itab；没有就查缓存、必要时现场构造
func getitab(inter *interfacetype, typ *_type, canfail bool) *itab {
	// 1) 快速失败：T 连 uncommon 都没有，说明没有方法集，不可能实现非空接口
	if typ.TFlag&abi.TFlagUncommon == 0 {
		if canfail {
			return nil
		}
		panic(&TypeAssertionError{/* ... */})
	}

	// 2) 无锁快路径：先在全局 itabTable 查 (I,T)
	// 第一次遇到 (I,T)：getitab 可能要构造并放进表；后续再遇到同一对：直接查表命中，快速返回
	t := (*itabTableType)(atomic.Loadp(unsafe.Pointer(&itabTable)))
	if m := t.find(inter, typ); m != nil {
		goto finish
	}

	// 3) 慢路径：加锁后二次检查（防止并发期间别人刚好插入）
	lock(&itabLock)
	if m := itabTable.find(inter, typ); m != nil {
		unlock(&itabLock)
		goto finish
	}

	// 4) 仍未命中：分配新 itab（尾部给 Fun 预留 N 个槽）
	m := (*itab)(persistentalloc(
		unsafe.Sizeof(itab{})+uintptr(len(inter.Methods)-1)*goarch.PtrSize,
		0, &memstats.other_sys,
	))
	m.Inter = inter
	m.Type = typ
	m.Hash = 0 // 运行时动态构建的 itab 不走 type switch 的 hash 预计算路径

	// 5) 填 Fun：检查 T 是否实现 I，成功则写函数地址，失败返回缺失方法名
	missing := itabInit(m, true)
	itabAdd(m) // 放入全局缓存（开放寻址表）
	unlock(&itabLock)

	if missing != "" && !canfail {
		panic(&TypeAssertionError{/* missing method */})
	}

finish:
	// 6) 成功标志：Fun[0] != 0
	if m.Fun[0] != 0 {
		return m
	}
	if canfail {
		return nil
	}
	panic(&TypeAssertionError{/* ... */})
}
```

### 关键点

1) **为什么先无锁查，再加锁查？**  
- 绝大多数路径是“已缓存命中”，无锁更快。  
- 未命中才加锁，并且加锁后必须二次检查，避免重复构造同一 `(I,T)`。

2) **为什么用 `persistentalloc`？**  
- `itab` 会被全局缓存长期持有，生命周期近似进程级，放在 persistent 区更合适。  
- 同时可以一次性分配“头部 + Fun 变长尾部”。

3) **`canfail` 是什么语义？**  
- `canfail=true`：用于 `x, ok := ...` 这种不抛 panic 的路径，失败返回 `nil`。  
- `canfail=false`：用于必须成功的断言/转换，失败直接 panic。

4) **`m.Fun[0]` 为什么是最终判定位？**  
- `itabInit` 会在“所有方法都匹配成功”后，最后一步写入 `Fun[0]`。  
- 所以 `Fun[0]==0` 可视为“未实现/不可用/失败缓存”的统一标记。


---

## 5. data装箱：`convT`、`convT16/32/64`、`convTstring`、`convTslice`

data是“具体值表示”的入口地址：
- 装的是非指针值（如 int、struct）
	- 通常会有一份可被接口持有的副本（常见是堆上），data 指向这份副本。
- 装的是指针值（如 *T）
	- data 一般就是那个指针值本身（指向原对象），不会再复制整个对象。
- 装的是零值/特殊可复用值
	- 运行时可能让 data 指向静态零值区或只读小值表（某些 convT* 优化）

把具体值变成接口里的 **`data` 字**时，编译器按类型选择不同 `conv*`（均保证成功；**nil 输入按约定仍可成功**，与 `assert*` 不同，见 `runtime/iface.go` 顶部注释）。

- **`convT` / `convTnoptr`**：在堆上 `mallocgc` 一块，把 `v` 指着的值 **复制** 进去，返回指向该块的指针；带指针的 type 会走带写屏障的路径。

```go
func convT(t *_type, v unsafe.Pointer) unsafe.Pointer {
	...
	x := mallocgc(t.Size_, t, true)
	typedmemmove(t, x, v)
	return x
}
```

- **小整数 `convT16/32/64`**：小值可指向只读表 `staticuint64s`，减少分配。

```go
func convT16(val uint16) (x unsafe.Pointer) {
	if val < uint16(len(staticuint64s)) {
		x = unsafe.Pointer(&staticuint64s[val])
		if goarch.BigEndian {
			x = add(x, 6)
		}
	} else {
		x = mallocgc(2, uint16Type, false)
		*(*uint16)(x) = val
	}
	return
}
```

- **`convTstring` / `convTslice`**：空串、nil slice 可走静态零值，非空则堆分配再拷贝。

```go
func convTstring(val string) (x unsafe.Pointer) {
	if val == "" {
		x = unsafe.Pointer(&zeroVal[0])
	} else {
		x = mallocgc(unsafe.Sizeof(val), stringType, true)
		*(*string)(x) = val
	}
	return
}

func convTslice(val []byte) (x unsafe.Pointer) {
	// Note: this must work for any element type, not just byte.
	if (*slice)(unsafe.Pointer(&val)).array == nil {
		x = unsafe.Pointer(&zeroVal[0])
	} else {
		x = mallocgc(unsafe.Sizeof(val), sliceType, true)
		*(*[]byte)(x) = val
	}
	return
}
```

补充：
- `staticuint64s` 是只读小整数表，`convT16/32/64` 命中小值时可避免堆分配。
- `convTstring/convTslice` 分配的是“头部对象”（string/slice header），底层数据仍按其语义引用原数据。



