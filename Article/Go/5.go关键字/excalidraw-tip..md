# interface 配图提示词（严格依据 `interface.md` 文案）

参考画图skill。

---

## 1. 概览：接口类型 + 隐式实现 + 双分量

请绘制「interface 概览」心智图，覆盖 `interface.md` **§1、§2**：

1. 接口只描述**一组方法**（行为），不关心具体是哪种类型。
2. 具体类型 `T` 只要方法**同名、同签名**且满足**导出/包可见性**，即**自动**满足接口，无需 `implements`。
3. 接口值 = **动态类型** + **动态值**；讨论 nil 必须同时想两层。

画面布局建议：

1. 中心卡片：`interface = 方法集合抽象`。
2. 一侧画「隐式实现」：`T 的方法 ≡ 接口要求` → `自动满足`。
3. 另一侧画「双分量」两个并列框：`动态类型`、`动态值`，下方小字：`nil 判断要看整体`。

**输出**：保存为 `Excalidraw/interface.概览_隐式实现_双分量.md`

---

## 2. 运行时布局：`eface` 与 `iface` + `data` 三种情况

请绘制「接口值在内存里长什么样」对比图，覆盖 `interface.md` **§3.1**（含三个小例子的要点，不必贴大段代码）：

1. **空接口**：`eface = (_type, data)`。
2. **非空接口**：`iface = (itab, data)`；`itab` 内含类型信息 + 方法跳转表 `Fun[]`。
3. `data` 三种常见形态：
   - 值类型装进接口：常指向**接口持有的副本**（改原变量不一定影响接口里那份）。
   - 指针装进接口：`data` 常是**那根指针**，改指向对象字段可透过接口看到。
   - 优化路径：小整数、空串、nil slice 等可指向**只读表或零值区**。
4. **nil 指针装进 `any`**：动态类型已是 `*T`，`data` 为 nil → **接口整体 `!= nil`**，与「空接口 nil」区分（与 §4 呼应，图中可画一条虚线指向下一图）。

画面布局建议：

1. 左右两列大框：`eface` | `iface`，每列两行槽位标注 `_type/itab` 与 `data`。
2. 下方三个小卡片：`值副本`、`指针`、`静态/优化`，各用短箭头指向 `data` 槽。
3. 右下角单独小框：`var i any = (*T)(nil)` → 标注「类型非空、data 为空」。

**输出**：保存为 `Excalidraw/interface.eface与iface与data.md`

---

## 3. 构建与调用主线：`convT*` → `getitab` → `itabInit` → `Fun[i]`

请绘制「从赋值到动态派发」**流程图**，覆盖 `interface.md` **§3.2**：

1. **赋值到接口**：可能走 `convT*` 准备 `data`（分配/拷贝/小值优化）。
2. **需要 `(I,T)` 配对**：走 `getitab(I,T,canfail)`。
3. **`getitab` 主线**：查全局 `itabTable` → 未命中则加锁再查 → 仍无则分配 `itab` 并 `itabInit` → 插入缓存；`Fun[0]` 表示是否可用。
4. **`itabInit`**：按接口方法顺序匹配具体类型方法，填 `Fun[]`；失败则返回缺失方法名（图中可用「失败分支」小框）。
5. **调用**：从 `iface.tab` 取 `itab`，按编译期方法下标取 `Fun[i]`，对 `data` 做间接调用。

画面布局建议：

1. 自上而下泳道式：`赋值/装箱` → `getitab` → `itabInit` → `调用`。
2. `getitab` 旁画菱形：`itabTable 命中？` → 是则跳过构造；否则进入「加锁 + 构造」。
3. 最后一步画「查表 + 跳转」：`Fun[i]` 箭头指向「目标函数」。

**输出**：保存为 `Excalidraw/interface.构建主线_getitab_itabInit_派发.md`

---

## 4. 经典坑：空接口 nil vs 装着 nil 指针的接口

请绘制「对比图」，覆盖 `interface.md` **§4**（可配合 `error` 示例语义，不必写完整代码）：

1. `var e1 error` 且未赋值：`e1 == nil` 为 true（**类型与值都空**）。
2. `var p *MyError; var e2 error = p`：`e2 == nil` 为 false（**动态类型已是 `*MyError`，仅 data 为 nil**）。
3. 一句结论：对接口做 `== nil` 判的是**整个接口值**是否「未持有任何具体类型」。

画面布局建议：

1. 左右两栏对比：`空 error 接口` vs `装着 nil 指针的 error`。
2. 每栏画两个小格：`类型槽`、`data 槽`，用颜色区分「空/非空」。
3. 底部统一结论条：`errors.Is` / `errors.As` 何时更稳妥（关键词即可）。

**输出**：保存为 `Excalidraw/interface.nil接口与nil指针对比.md`

---

## 5. `any`、类型断言与 `type switch`

请绘制「一张图分两区」，覆盖 `interface.md` **§5～§7**：

1. **`any` 与 `interface{}`**：完全等价别名；能装任意类型，**不**自带运算能力。
2. **类型断言**：单返回值失败 panic；双返回值 `ok` 形式不 panic。
3. **`type switch`**：`x` 必须是接口类型；`case nil` 只匹配**接口本身 nil**，与「动态类型为 `*T` 且指针值为 nil」不同。

画面布局建议：

1. 左上：`any ≡ interface{}`。
2. 右上：两个小分支：`x.(T)` 与 `x.(T), ok`。
3. 下半：`switch x.(type)` 画分支树，`case nil` 单独高亮，旁边注释「与 *T 的 nil 不同」。

**输出**：保存为 `Excalidraw/interface.any_断言_typeSwitch.md`

---

## 使用说明

- 配图文件建议放在本目录下 `Excalidraw/`，文件名与上各节 **输出** 一致，便于和 [[interface]]、`[[interface源码]]` 双向链接。
- 请遵守仓库内 `excalidraw-diagram` 技能的 frontmatter 与画布规范。
