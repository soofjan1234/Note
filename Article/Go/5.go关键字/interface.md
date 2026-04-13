---
title: Go interface：语法、接口值与常见坑
description: 接口类型与隐式实现、双分量、内建 error、nil 坑、any、断言与 type switch；源码见 interface 源码笔记。
---

# interface

## 前言

Go 的 **interface** 描述的是「一组方法」所构成的抽象：变量可以持有**满足该方法集**的具体类型值，调用时走**动态派发**。

---

## 1. 接口类型：只关心行为

接口类型由 **方法列表** 定义：只写「能做什么」，不写「是谁」。

```go
type Reader interface {
	Read(p []byte) (n int, err error)
}
```

某具体类型 `T` 只要拥有与接口 **同名、同签名** 的全部方法（且满足导出/包可见性规则），就 **自动** 满足该接口，无需 `implements`。

```go
type fileReader struct{ path string }

func (f fileReader) Read(p []byte) (int, error) {
	// ... 真正实现 ...
	return 0, nil
}

var r Reader = fileReader{} // 编译期检查：fileReader 是否实现了 Reader
```

```go
func consume(r Reader) {
	// 只依赖 Read，可以是 *os.File、bytes.Reader、自定义类型等
	_, _ = r.Read(nil)
}
```
---

## 2. 接口值 = 动态类型 + 动态值

把值赋给接口类型的变量后，运行时会区分：

1. **动态类型**：当前装着的是哪一种具体类型。
2. **动态值**：该类型下的那份数据（可能是指针，也可能是小值的优化表示）。

```go
var r Reader
// r 尚未赋值：一般是「无动态类型 + 无动态值」的 nil 接口

var f fileReader
r = f
// 此时 r 的动态类型是 fileReader，动态值是 f 的副本（按赋值语义）
```

r = f 表示接口里记着「我现在是一个 fileReader」，并且里面存的是 当时 f 的一份拷贝，不是对 f 这个变量的引用。
讨论「接口是不是 nil」时，必须同时想 **类型与值两层**；只谈「里面指针是不是 nil」不够。

---

## 3. 运行时模型与构建主线

### 3.1 模型：接口值长什么样

运行时里，接口值有两种形态：

- **空接口**：`eface = (_type, data)`
- **非空接口**：`iface = (itab, data)`

可以把它理解成“两个槽位”：

1. 第一格存“当前具体类型是谁”
   - `eface` 用 `_type`
   - `iface` 用 `itab`（里面还带方法跳转表 `Fun[]`）
2. 第二格 `data` 存“具体值放在哪”

`data` 常见三种情况：

- **值副本地址**：如 `int/struct` 装进接口，常见是拷贝后由 `data` 指向
- **原指针值**：如 `*T` 装进接口，`data` 通常就是这根指针
- **静态区地址**：小整数/空串/nil slice 等优化场景，`data` 可指向只读或零值区域

**例 1：非指针值放进接口**

```go
var x int = 7
var i any = x
```

`i` 里：

- 类型信息：`int`
- `data`：指向「7」的那份接口持有副本（不是变量 `x` 本身地址）

所以后面改 `x`，`i` 里的值不会变。

**例 2：指针值放进接口**

```go
type S struct{ A int }

s := &S{A: 1}
var i any = s
```

`i` 里：

- 类型信息：`*S`
- `data`：就是指针 `s` 指向的对象地址

所以改 `s.A = 2`，从 `i.(*S).A` 读到的是 `2`（同一对象）。

**例 3：nil 指针放进接口**

```go
type S struct{ A int }

var p *S = nil
var i any = p
```

`i` 里：

- 类型信息：`*S`（动态类型已确定）
- `data`：`nil`

因此 `i != nil`（接口整体不是「空接口值」），但 `i.(*S)` 解出来仍是 `nil` 指针。这是「装着 nil 指针的接口」与「接口本身为 nil」的经典区分，详见下文 **§4**。

### 3.2 主线：接口值是怎么“建出来并调用”的

1. **赋值到接口**
   - `var i any = x` 或 `var r Reader = v`
   - runtime 先处理 `data`（分配/拷贝/小值优化）
   - 编译器可能插入 `convT*`，`data` 指向堆副本/指针/静态区

2. **需要非空接口匹配时**
   - 例如断言、接口转换、type switch 的接口分支
   - 会走 `getitab(I, T, canfail)`，判断 `T` 是否实现 `I`
   - **`getitab` 大致流程**（runtime 里可理解为「查缓存 → 没有再建」）：
     - 若 `T` 没有方法扩展信息（没有 `UncommonType`），直接判定无法实现非空接口；`canfail` 为真则返回 `nil`，否则 panic。
     - **无锁快路径**：在全局 `itabTable` 里按 `(I, T)` 查找；命中则直接返回已有 `itab`。
     - **慢路径**：加锁后再查一次（避免并发刚插入）；仍无则 `persistentalloc` 分配一块 `itab`（含变长的 `Fun` 槽位），调用 `itabInit` 填方法表，再插入全局表。
     - 收尾：若 `m.Fun[0] != 0` 表示 `(I,T)` 可用；否则按 `canfail` 返回 `nil` 或 panic。

3. **`getitab` 未命中缓存时真正干活的是 `itabInit`**
   - 创建 `itab` 后调用 `itabInit`，按**接口方法顺序**在**具体类型方法表**里逐个匹配，把每个接口方法对应的**函数代码地址**写入 `Fun[k]`。
   - **`itabInit` 大致流程**：
     - 从接口 `I` 取第 `k` 个方法的名字与签名；在 `T` 的方法表里线性扫描匹配（签名一致、名字一致，且满足导出/同包可见性）。
     - 全部匹配成功后才把第一个方法的地址写入 `Fun[0]`（中途失败可保持 `Fun[0]==0`，表示「未实现」一类状态，供上层判断）。
     - 任一接口方法在 `T` 上找不到实现，返回缺失的方法名，供断言错误信息使用。

4. **调用接口方法**
   - 非空接口值里是 `iface{tab: *itab, data: ...}`；`tab` 指向上面建好的 `itab`。
   - 编译器为本次调用选定**接口方法下标** `i`（与 `I` 的方法声明顺序一致），执行时从 `itab.Fun[i]` 取出代码地址，以 `data` 作为接收者数据源做**间接调用**（动态派发）。直观上可记成「查表 + 跳转」，不必和手写虚表一一对应。

一句话总结：**接口调用 = 类型信息（`_type/itab`）+ `data` + `Fun[]` 方法跳转表。**

---

## 4. 经典坑：`nil` 接口 vs「装着 nil 指针的接口」

在 Go 里，`error` 大致等价于下面这样的接口：

```go
type error interface {
	Error() string
}
```

结合 `error`，看清为什么 `err == nil` 有时会误判。

```go
type MyError struct{ msg string }

func (e *MyError) Error() string { return e.msg }

var e1 error
var p *MyError
var e2 error = p

fmt.Println(e1 == nil) // true：接口值「类型、值」都空
fmt.Println(e2 == nil) // false：动态类型已是 *MyError，只是 data 为 nil
```

原因概括：**对接口做 `== nil` 判断的是「整个接口值」是否为「未持有任何具体类型的空接口」**；`e2` 已携带 `*MyError` 这一动态类型，仅动态值为 nil，**整体不是 nil 接口值**。

再举一个「传参回来」的场景：

```go
func mayFail() error {
	var p *MyError
	return p // 返回的是 (类型=*MyError, 值=nil) 的 error，调用方 err == nil 为 false
}

func okPattern() error {
	return nil // 返回的是「空 error 接口」
}
```

处理错误时，不要只依赖 `err == nil`，需要区分「有没有包装类型」时，用 **`errors.Is` / `errors.As`** 等更稳妥。


---

## 5. `any` 与空接口 `interface{}`

- **`interface{}`**：方法列表为 **空** 的接口类型，表示「可以装任意类型的值」。
- **`any`**：从 **Go 1.18** 起，是 `interface{}` 的**预声明别名**，二者**完全等价**，写法上 `any` 更短、更常见。

```go
var a any
a = 42
a = "hi"
a = []int{1, 2, 3}

// 标准库里常见：先以 any 接进来，再在内部断言或反射
func Println(a ...any) { /* ... */ }

// JSON：先把结构变成「通用树」，再编码
var v any
_ = json.Unmarshal(data, &v)
```

**注意：** `any` 只是「能装任何东西」，**没有**带来任何新方法；要对值做运算，仍要**断言回具体类型**，或配合反射 / 泛型。

---

## 6. 类型断言

```go
var x any = 3.14
if i, ok := x.(int); ok {
	fmt.Println("int", i)
} else if f, ok := x.(float64); ok {
	fmt.Println("float64", f)
}
```

- **单返回值 `x.(T)`**：类型不对 → **panic**。
- **双返回值 `x.(T, ok)`**：类型不对 → **不 panic**，`ok == false`。

对 **nil 接口值**（从未赋过具体类型的 `var x any`）做断言，同样会失败或 panic，因为**没有动态类型可供匹配**。

```go
var x any
_ = x.(string) // panic: interface conversion
```

---

## 7. 类型 switch

```go
func describe(x any) {
	switch v := x.(type) {
	case int:
		fmt.Println("int", v)
	case string:
		fmt.Println("string", v)
	case nil:
		// 整个接口值为「空」：例如 var x any 从未赋值
		fmt.Println("nil interface value")
	default:
		fmt.Printf("其它类型 %T\n", v)
	}
}
```

`x` 必须是**接口类型**（含 `any`）。在带 `v := x.(type)` 的分支里，除 `nil` 分支外，`v` 在该 `case` 内是具有对应**具体类型**的值。`case nil` 只匹配 **接口本身为 nil**（没有任何动态类型），与「动态类型是 `*T`、指针值为 nil」不同。

```go
var p *int
var i any = p
switch i.(type) {
case *int:
	// 会进这里：动态类型是 *int，即使 p 本身是 nil
case nil:
	// 若 i 从未持有类型，才进这里
}
```

与类型断言一样，要注意 **nil 接口** 与 **装着 nil 的具体值** 的分支表现。

