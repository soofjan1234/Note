# GMP 源码（上）：结构、启动与创建 G

> **上篇：** `G / M / P / schedt` 类型布局 + **全流程鸟瞰** + **`schedinit` 到 `runqput`（含 `newproc` / `gfget`）**。  
> **下篇** `GMP源码2.md`：**调度循环**、`gopark` / 抢占 / `syscall` 与状态收束。  
> 系列阅读：`GMP由来` → `GMP机制` → **`GMP源码1`（上）** → **`GMP源码2`（下）**  
> 术语口径：`G`=任务、`M`=线程、`P`=运行资源与本地队列、`schedt`=全局调度中心

## 这篇写给谁

- 已读过《由来》《机制》，准备啃 `runtime` 调度相关源码。
- 希望先对齐**类型与字段**，再弄清**进程如何把调度器立起来、第一条业务 G 如何入队**。

## 阅读方式

前一半是「类型地图」；后一半（第 0～2 节）是「从 rt0 到 `runqput`」的冷启动与创建 G 主链。

---

## GMP 结构

下面是与调度直接相关的核心类型节选

### G（Goroutine）

每个协程包含**执行上下文**（栈、指令指针等）和**调度状态**。

```go
type g struct {
	// ---- 执行上下文 ----
	stack       stack   // 栈内存范围 [lo, hi)
	stackguard0 uintptr // 栈增长检查 / 协作式抢占标记等
	sched       gobuf   // 被切走时保存的现场，恢复时从这里继续执行

	// ---- 调度状态 ----
	m            *m       // 当前正在执行本 G 的 M（OS 线程）
	atomicstatus uint32   // G 的状态：可运行 / 运行中 / 等待 / 系统调用等
	goid         uint64   // goroutine ID
	schedlink    guintptr // 在调度链表中的下一个 G
	waitsince    int64    // 进入等待状态的大致时间
	waitreason   waitReason // 等待原因（channel、锁、timer 等）
	// ...
}

type gobuf struct {
	sp   uintptr        // 栈指针，恢复时写回 CPU
	pc   uintptr        // 指令指针（下一条要执行的地址）
	g    guintptr       // 当前 gobuf 所属的 G（用于栈扫描等）
	ctxt unsafe.Pointer // 闭包 / 上下文，恢复时写回
	// ...
}
```

### M（Machine）

一个操作系统线程

```go
type m struct {
	g0   *g // 持有调度栈的 goroutine（运行时线程在 g0 上跑调度逻辑）
	curg *g // 在当前线程上运行的用户 goroutine

	p               puintptr // 这条线程当前绑定的 P（processor）
	nextp           puintptr // 即将绑定的 P
	oldp            puintptr // 进系统调用前绑定的 P
	// ...
}
```

`g0` 深度参与运行时调度：创建 goroutine、部分大内存分配、CGO 等与**调度栈 / 系统栈**相关的路径往往走在 `g0` 上，避免和用户 G 的栈混用。

### P（Processor）

管理**本地运行队列**等运行资源，决定哪些 G 在本 P 上优先被取出执行（与 `findRunnable`、`runqput` 等紧密配合）。

```go
type p struct {
	m muintptr

	// 本地运行队列（固定长度 256，多数访问无锁）
	runqhead uint32
	runqtail uint32
	runq     [256]guintptr

	runnext  guintptr // 优先于 runq 跑的下一个 G（例如被当前 G ready 的 G

	// 各类缓存 比如
	mcache      *mcache // 小对象缓存
	pcache      pageCache // 页级缓存
	gFree gList // 空闲 G 的本地缓存，执行完的 G 可放回这里复用
	deferpool    []*_defer // 复用 _defer，执行 defer 时少 malloc
	deferpoolbuf [32]*_defer
	// ...
}
```

**和内存管理相关**
1. mcache
- 是什么：每个 P 自带的一块小对象分配缓存，和调度里的「每个 P 一份资源」是同一套思路。
- 干什么用：分配很小的对象时，优先从本 P 的 mcache 里拿，减少去全局堆 / 中心结构抢锁，分配路径更快。
- 和 GMP 的关系：G 在 M 上跑，M 绑 P，所以业务 goroutine 做小对象分配时，往往走的是当前 P 的 mcache，和调度器把计算绑在 P 上是一致的。

2. pageCache
- 是什么：挂在 P 上的页级缓存，按「页」为单位缓存从堆上拿到的内存。
- 干什么用：需要向堆申请/归还整页时，先在本 P 的 pageCache 里周转，减少频繁进全局分配器，和 mcache 一样是「本地快路径」。
- 和 mcache 的区别（直觉）：mcache 更偏按 size class 的小对象；pageCache 更偏页这一层的批量与缓存，粒度更大。


### 全局变量
```go
var (
	sched      schedt    
	
	m0         m         // 是主线程的 M 结构体，用于初始化调度器和运行时的其余部分
	g0         g         // g0 负责执行与 Goroutine 调度相关的底层操作，例如切换上下文、栈切换等
)
```

**schedt（Scheduler Type）**

全局调度中心：全局 G 队列、空闲 M / P 链表等。

```go
type schedt struct {
	lock mutex // 保护 schedt 内若干字段

	midle        muintptr // 空闲 M 链表
	nmidle       int32    // 空闲 M 数量

	pidle      puintptr // 空闲 P 链表
	npidle     uint32   // 空闲 P 数量

	// 全局可运行 G 队列
	runq     gQueue
	runqsize int32

	// 全局 _Gdead 等可回收的 G（分有栈 / 无栈列表）
	gFree struct {
		lock    mutex
		stack   gList // 带栈的 G
		noStack gList // 不带栈的 G
	}

	// ...
}
```


### 为啥G、M、P互相指来指去的

核心原因：**调度热路径要“常数时间定位 + 少锁”**。

1. **快速拿到当前运行关系**

- `m.curg -> g`：线程立刻知道“我当前在跑哪个 goroutine”
- `g.m -> m`：goroutine 立刻知道“我挂在哪个线程上”
- `m.p -> p` / `p.m -> m`：线程与执行资源绑定时，O(1) 找到对方

2. **调度切换时要同时改多方状态**

例如 `G` 从 `_Grunning` 变 `_Gwaiting`，`M` 要切下一个 `G`，`P` 的 `runq/runnext` 也可能变化。  
有了互指，切换路径可以直接改相关对象，不用先查全局结构再定位。

3. **减少全局锁竞争**

如果只靠全局表（如 `gid -> m`、`mid -> p`），高频调度下会大量加锁/原子操作。  
“本地直连指针 + 少量原子位”是 runtime 常见的性能手段。

4. **便于处理动态迁移场景**

在 `syscall` / `cgo` / 抢占 / `park-unpark` 过程中，`G-M-P` 关系会暂时断开或迁移。  
明确的互指关系让 runtime 能快速判断：谁持有 `P`、谁可抢占、谁应该入队。

> 这不是永久强绑定，而是“瞬时运行关系”：  
> 常态是 `G` 跑在某个 `M` 上、`M` 持有某个 `P`；调度时三者都可能变化（如 `M` 进 syscall 丢 `P`，`P` 被其他 `M` 接管，`G` 迁移到别的 `M/P`）。

一句话：互指不是为了增加耦合，而是为了在高频调度路径上做到**低延迟、低锁开销**。

---

## 调度流程
一眼看全流程

主流程可以先背成这条链：

`rt0_go -> schedinit -> newproc -> mstart -> schedule -> findRunnable -> execute`

1. **程序刚起来**先进 `rt0_go`（入口汇编/引导）
2. 接着 **`schedinit` 把调度器、P 的数量、内存/GC 等“场子”铺好**
3. 再用 **`newproc` 捏出第一个要跑的 goroutine（比如 main）并塞进队列**
4. 当前线程 **`mstart` 说“我开始上班”**
5. 进入 **`schedule` 这个大循环**：每一圈先 **`findRunnable` 找一个能干活的 G**，找到了就 **`execute` 真正去跑它**。跑不下去（让出、阻塞、被抢占等）又会回到 `schedule`，周而复始。

### 0. 真正的入口：runtime·rt0_go
Go程序的真正启动函数 runtime·rt0_go，会经历几件关键事：

1. 初始化 `m0` 和 `g0`，绑定 g0 和 m0。
2. `schedinit` 完成调度器、内存、GC、P 等初始化。
3. 按 `GOMAXPROCS` 设置 P 的数量（`procresize`）。
4. `newproc` 创建第一个业务 goroutine，并塞进队列。
5. `mstart` 进入调度循环。

这里最关键的理解是：**Go 先把「舞台」搭好（M/P/sched），再把业务 G 推上台。**

```s
// src/runtime/asm_arm64.s
TEXT runtime·rt0_go(SB),NOSPLIT|TOPFRAME,$0
	// SP = stack; R0 = argc; R1 = argv

	SUB	$32, RSP
	MOVW	R0, 8(RSP) // argc
	MOVD	R1, 16(RSP) // argv

...

MOVD	$runtime·m0(SB), R0
// 绑定 g0 和 m0
MOVD	g, m_g0(R0)
MOVD	R0, g_m(g)

...

BL	runtime·args(SB)
BL	runtime·osinit(SB)
BL	runtime·schedinit(SB)

 // 创建一个新的 goroutine 来启动程序
MOVD	$runtime·mainPC(SB), R0
// ...
BL	runtime·newproc(SB)

 // 开始启动调度器的调度循环
BL	runtime·mstart(SB)

...

DATA	runtime·mainPC+0(SB)/8,$runtime·main<ABIInternal>(SB) // main函数入口地址
GLOBL	runtime·mainPC(SB),RODATA,$8

```

---

### 1. 启动阶段：先把调度器搭起来

```go
// src/runtime/proc.go
// The bootstrap sequence is:
//
//	call osinit
//	call schedinit
//	make & queue new G
//	call runtime·mstart

// 调度器初始化
func schedinit() {
    ...
    // 设置机器线程数M最大为10000
    sched.maxmcount = 10000
    ...
    // 栈、内存分配器相关初始化
    stackinit()          // 初始化栈
    mallocinit()         // 初始化内存分配器
    ...
    // 初始化当前系统线程 M0
    mcommoninit(_g_.m, -1)
    ...
    // GC初始化
    gcinit()
    ...
    // 设置P的值为GOMAXPROCS个数
    procs := ncpu
    if n, ok := atoi32(gogetenv("GOMAXPROCS")); ok && n > 0 {
        procs = n
    }
    // 调用procresize调整 P 列表
    if procresize(procs) != nil {
        throw("unknown runnable goroutine during bootstrap")
    }
    ...
}
```

**GOMAXPROCS**
GOMAXPROCS表示 Go 调度器里可同时运行 Go 代码的 P 的数量上限，也就是同一时刻能并行跑多少个 goroutine
默认通常是机器可用 CPU 核数（更准确是 runtime 看到的可用 CPU 数）。

---

## 2. 创建 G：`newproc -> newproc1 -> runqput`

当你写下 `go f()`，大致会走这条路：

1. `newproc` 在用户 G 上用 `systemstack` 切到 **g0 栈**，避免在用户栈上做复杂调度逻辑。
2. `newproc1` 里通过 `gfget` **优先复用** P 本地 / 全局 `gFree` 中的 G，不够再新建；把状态设为 `_Grunnable`（少数 parked 路径为 `_Gwaiting`）。
3. `runqput` 把新 G 放进当前 P 的队列（常优先 `runnext`）；若 `main` 已启动则 `wakep` 必要时拉起空闲 M。

### 2.1 `newproc`

```go
func newproc(fn *funcval) {
	gp := getg()
	pc := sys.GetCallerPC()
	systemstack(func() {
		newg := newproc1(fn, gp, pc, false, waitReasonZero)

		pp := getg().m.p.ptr()
		runqput(pp, newg, true)

		if mainStarted {
			wakep()
		}
	})
}
```

### 2.2 初始化：`newproc1` 与 `gfget`

`newproc1` 负责装配 `*g`：从 `gfget` 拿到或新建 G，填好入口、栈等，再设调度状态。

```go
// 获取或创建 g，再设为 _Grunnable（或 _Gwaiting）
func newproc1(...) *g {
	...
	newg := gfget(pp)
	...
	var status uint32 = _Grunnable
	if parked {
		status = _Gwaiting
	}
	...
}
```

在 **`gfget`** 里：先从当前 P 的本地 **`gFree`** `pop` 一个 G；若本地空了，会**加锁**从全局 **`sched.gFree`** 一次最多搬一批到本地（常见实现上限与「凑够可用」相关，下文用 `32` 表示数量级），再 `pop`。

拿到 G 后根据栈情况处理：栈尺寸仍匹配则**沿用**；否则**释放旧栈**再按需分配；无栈则**新分配启动栈**并设置 **`stackguard0`** 等，最终返回可用的 `*g`。这就是 goroutine 创建往往很快的原因之一：**对象与栈走复用路径**，不总是冷启动。

```go
func gfget(pp *p) *g {
retry:
	// ① 本地 gFree 空了且全局还有 → 加锁，从全局最多搬一批到本地，再重试
	if pp.gFree.empty() && (!sched.gFree.stack.empty() || !sched.gFree.noStack.empty()) {
		lock(&sched.gFree.lock)
		for pp.gFree.size < 32 {
			...
		}
		unlock(&sched.gFree.lock)
		goto retry
	}

	// ② 从本地 pop 一个；没有就返回 nil（调用方会 new 新 G）
	gp := pp.gFree.pop()
	if gp == nil {
		return nil
	}

	// ③ 有栈但尺寸已不是默认 → 释放旧栈，标记为无栈
	if gp.stack.lo != 0 && gp.stack.hi-gp.stack.lo != uintptr(startingStackSize) {
		...
	}

	// ④ 无栈 → 分配一块新启动栈并设 stackguard0
	if gp.stack.lo == 0 {
		...
	} else {
		...
	}
	return gp
}
```

### 2.3 `runqput`：放队列也有优先级

`runqput(pp, gp, next)` 的关键点：

1. `next=true` 时优先尝试放 `runnext`（下一跳位）。
2. 普通情况下放本地 `runq` 队尾。
3. 本地满了，走 `runqputslow`，把一部分搬到全局队列腾空间。

还有两个公平性保护：

1. 没有 `sysmon` 时会限制过度插队。
2. race 模式下会做随机化，避免测试隐式依赖固定调度顺序。


```go
const randomizeScheduler = raceenabled

func runqput(pp *p, gp *g, next bool) {
	// ① 无 sysmon 时不用 runnext，避免一对 G 占满时间片导致饥饿
	if !haveSysmon && next {
		next = false
	}
	// race 时 50% 放弃 runnext，随机化调度
	if randomizeScheduler && next && randn(2) == 0 {
		next = false
	}

	// ② next=true：CAS 把 gp 放进 pp.runnext；若挤掉原来的 runnext，把被挤掉的 G 当作 gp 放进下面队尾
	if next {
	retryNext:
		oldnext := pp.runnext
		if !pp.runnext.cas(oldnext, guintptr(unsafe.Pointer(gp))) {
			goto retryNext
		}
		if oldnext == 0 {
			return  // 原来没 runnext，只放了 gp，结束
		}
		gp = oldnext.ptr()  // 被挤出来的 G 要放进本地队尾
	}

retry:
	// ③ 本地 runq 未满：放到 runq[tail]，tail++
	h := atomic.LoadAcq(&pp.runqhead)
	t := pp.runqtail
	if t-h < uint32(len(pp.runq)) {
		pp.runq[t%uint32(len(pp.runq))].set(gp)
		atomic.StoreRel(&pp.runqtail, t+1)
		return
	}
	// ④ 本地满了：把一半本地 + gp 搬到全局队列，成功就返回
	if runqputslow(pp, gp, h, t) {
		return
	}
	goto retry  // 没搬成（队列被消费了），再试一次
}
```

**`next` 与 `runnext` 再捋一遍（对齐上面代码）：**

1. 对 `next=true` 进行了两次拦截：
    1. 没有监工（sysmon）时，不允许插队。因为两个 G 如果互相不停地创建对方并插队，就会永远霸占 CPU，导致其他 G 饿死。
    2. 竟态检测（randomizeScheduler）时，50% 几率踢出 VIP。
2. 如果 next 为 true，进入 `runnext`：
    1. 通过 CAS 把新 G 放进 `pp.runnext`，结束。
    2. 如果 `runnext` 有老 G，设现有 `gp` 为老 G。
3. 不管是新 G 还是老 G，都是 `gp`，走到现在都得放队尾了：
    1. 如果满了，通过 `runqputslow` 把一半本地 + `gp` 搬到全局队列，成功就返回。

关于 `randomizeScheduler = raceenabled`：

有些测试或代码其实**隐式依赖**「G 一定按某种顺序被调度」（例如以为 A 一定在 B 前面跑、或一定先被调度到）。顺序一变就挂，但平时看不出来。

开 `-race` 时给调度加随机，是为了揪出那些「以为 G 会按某种顺序跑」的隐藏依赖；通过 `-race` 的测试就不该再依赖调度顺序。

### 接上 `mstart`（进下篇之前）

本篇停在「首个业务 G 已通过 `runqput` 入队」：**当前 OS 线程**随后在 **`mstart`** 里进入调度主链——循环执行 **`schedule`**，在 **`findRunnable`** 里捞 G，再 **`execute`**。冷启动创建出来的 G 与后续 `go` 创建的 G，在入队之后共用同一套主循环；细节从 `GMP源码2.md` 第 1 节接着读即可。

---

> **续下篇：** 从 `mstart` 进入的 **`schedule -> findRunnable -> execute`** 起，见 `GMP源码2.md`。