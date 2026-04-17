# GMP 源码（下）：调度循环、阻塞与 syscall

> **下篇：** 从 `mstart` 进入的 **`schedule -> findRunnable -> execute`**，到 **`gopark` / 抢占 / syscall`** 与状态收束。  
> **上篇** `GMP源码1.md`：类型 + **第 0～2 节**（鸟瞰、`schedinit`、`newproc`～`runqput`）。  
> 系列阅读：`GMP由来` → `GMP机制` → **`GMP源码1`（上）** → **`GMP源码2`（下）**  
> 术语口径：`G`=任务、`M`=线程、`P`=运行资源与本地队列、`schedt`=全局调度中心

## 这篇写给谁

- 已读完上篇第 0～2 节（或已熟悉启动与 `runqput`）。
- 想专注搞懂**调度循环、让出/阻塞、抢占与系统调用**这几条 runtime 主链。

## 阅读方式

本篇按「找活 → 触发调度 → 巡检与 syscall → 状态小结」读；与上篇拼起来才是完整 `proc.go` 鸟瞰。

---

## 1. 调度循环：`schedule -> findRunnable -> execute`

调度循环本身很短：

1. `findRunnable()` 找一个可运行 G。
2. `execute(gp, inheritTime)` 执行它。

### 1.1 `findRunnable` 的常见查找顺序

可简化为：

1. 先处理特殊任务（trace、GC worker 等）。
2. 周期性看全局队列（保证公平，不让本地长期独占）。
3. 看本地队列（`runqget`：先 `runnext`，再 `runq`）。
4. 看全局队列。
5. 看网络轮询（`netpoll`）是否有就绪 G。
6. 去别的 P 偷任务（`stealWork`）。
7. 仍无任务则让出 P 或阻塞等待。

这套顺序的核心目标：**低开销优先 + 全局公平 + 尽量不让 CPU 空转。**


```go
func schedule() {
    ...
    gp, inheritTime, tryWakeP := findRunnable()
    ...
    execute(gp, inheritTime)
}

func findRunnable() (gp *g, inheritTime, tryWakeP bool) {
    ...
    // 特殊 G（trace、GC worker）
    ...
    // 周期性看全局队列（公平性）
    if pp.schedtick%61 == 0 && !sched.runq.empty() { ... }
    // 本地 runq（先 runnext，再 runq）
    if gp, inheritTime := runqget(pp); gp != nil { ... }
    // 全局 runq
    if !sched.runq.empty() { ... }
    // netpoll
    if netpollinited() && netpollAnyWaiters() && ... { ... }
    // stealWork
    if mp.spinning || 2*sched.nmspinning.Load() < gomaxprocs-sched.npidle.Load() { ... }
    // 仍无任务 -> 让出 P / 阻塞
    ...
}
```

---

## 2. 触发调度：四条典型路径

### 2.1 正常调度

G 自然跑完或阶段完成，回到下一轮 `schedule`，这是最平滑的路径。

### 2.2 主动调度：`Gosched`

业务代码主动调用 `runtime.Gosched()` 后，大致做这些事：

1. G 从 `_Grunning` 改为 `_Grunnable`。
2. `dropg()` 解除当前 M 与该 G 的执行绑定。
3. `globrunqput(gp)` 把 G 放回全局可运行队列。
4. 进入 `schedule()` 继续调度其他 G。

一句话：**我先让位，回队列排队，大家轮着来。**


```go
func Gosched() {
    checkTimeouts()
    mcall(gosched_m)
}
func gosched_m(gp *g) {
    goschedImpl(gp, false)
}
func goschedImpl(gp *g, preempted bool) {
    ...
    casgstatus(gp, _Grunning, _Grunnable)
    dropg()
    lock(&sched.lock)
    globrunqput(gp)
    unlock(&sched.lock)
    schedule()
}
```

### 2.3 被动调度：`gopark` / `goready`

当 G 因 channel、锁、sleep、网络等待而无法继续：

1. `gopark` 把 G 从 running 变 waiting。
2. G 挂入对应等待结构（资源队列）。
3. 当前 M 去找别的活。

当条件满足时：

1. 通过 `goready/ready` 把 G 从 waiting 变 runnable。
2. `runqput` 放回某个可运行队列。
3. 必要时 `wakep()` 拉起更多工作能力。

一句话：**阻塞不是终止，是“下台等待 -> 条件满足 -> 再排队上台”。**


```go
// 被阻塞
func gopark(...) {
    ...
    mcall(park_m)
}
func park_m(gp *g) {
    ...
    casgstatus(gp, _Grunning, _Gwaiting)
    dropg()
    schedule()
}

// 被唤醒
func goready(gp *g, traceskip int) {
    systemstack(func() { ready(gp, traceskip, true) })
}
func ready(gp *g, traceskip int, next bool) {
    ...
    casgstatus(gp, _Gwaiting, _Grunnable)
    runqput(mp.p.ptr(), gp, next)
    wakep()
}
```

**网络阻塞和普通阻塞的区别**

相同点：两者都会让 `G` 从 `_Grunning` 进入 `_Gwaiting`，随后被唤醒为 `_Grunnable`，再进入 run queue 等待执行。

不同点主要在“挂哪儿、谁唤醒”：

1. 普通阻塞（channel/锁/sleep）

- 挂载位置：channel 的收发队列、mutex/sema 等待队列、timer 等待结构。
- 唤醒来源：通常是其他 `G` 的同步操作或定时器到期。
- 典型路径：`gopark -> goready/ready -> runqput -> (可能 wakep)`。

2. 网络阻塞（netpoll）

- 挂载位置：fd 对应的 pollDesc / netpoll 关注结构。
- 唤醒来源：内核 I/O 就绪事件（可读/可写）。
- 典型路径：`gopark` 挂起后，netpoll 收到事件，把就绪 `G` 注入可运行队列（本质上也是回到 runnable 再被调度）。

一句话：**普通阻塞等“运行时内部条件”，网络阻塞等“内核外部事件”；但最终都会收敛到同一调度闭环。**

#### 2.4 抢占调度和系统调用
抢占调度和系统调用，详情见下文

---

## 3. 抢占与接管：轮到 `sysmon` 出场

`sysmon` 跑在**独立线程**上，不占用 P，相当于调度器的**巡检员**：周期醒来一圈，负责**抢占**、**syscall 回收 P**、**补 netpoll**、**必要时强扭 GC** 等。

```go
func sysmon() {
	...
	var delay uint32 = 20 // μs，初始休眠约 20μs
	var idle int64      // 连续多少轮几乎没干事
	for {
		if idle == 0 {
			delay = 20
		} else if idle > 50 {
			delay *= 2
		}
		if delay > 10*1000 { // 上限约 10ms，别睡太死
			delay = 10 * 1000
		}
		usleep(delay)
		now := nanotime()

		// 若很久没 poll 过网络，可能把就绪的 G 拎出来注入全局队列
		lastpoll := sched.lastpoll.Load()
		if netpollinited() && lastpoll != 0 && lastpoll+10*60*1e9 < now {
			list, delta := netpoll(0) // 非阻塞扫一轮
			...
			injectglist(&list)
			...
		}

		// Retake：syscall 过久则 handoffp；Running 过久则 preemptone
		if retake(now) != 0 {
			idle = 0
		} else {
			idle++
		}

		// 例如太久没 GC 时，可注入专门跑 GC 的 G（具体条件见源码）
		if ... need forced GC ... {
			injectglist(&list)
			...
		}
		...
	}
}
```

### 3.1 `sysmon` 常见职责

1. **抢占长时间运行的 G（Preemption）**：结合 `retake` / `preemptone`，对跑得太久的 G 打标或发信号，逼它让出 CPU（具体时间片与 `forcePreemptNS` 等常量以源码为准，量级常在 **10ms 级**）。
2. **接管 syscall 里拖太久的 P（Retake）**：G 进了内核还占着 P 不干活时，`sysmon` 通过 `handoffp` 把 **P 还给调度器**，让别的 M 接着用这个 P 跑别的 G。
3. **网络轮询（Netpoll）**：正常路径里调度器很忙时可能久未 `netpoll`；`sysmon` 可**顺手**拉一把就绪的网络 I/O，把对应 G 唤醒/入队。
4. **强制 GC（Force GC）**：例如系统**很久**没发生过 GC 时，可注入辅助 goroutine 推动一轮回收（条件与间隔以 `proc.go` / `mgc.go` 为准）。

### 3.2 `retake`：谁在跑太久？syscall 要不要把手？

`retake` 会扫 `allp`，对每个 P 看 `status`，在 **`_Prunning` / `_Psyscall`** 下做近似下面两类事（**分支顺序、阈值与真实 `proc.go` 可能略有出入，以你本机源码为准**）：

- **Running + 同一 G 霸占过久**：`schedtick` 等手段判断「多久没换 G」，到点则 **`preemptone`**。
- **Syscall + 卡住太久或有用 P 更紧迫**：在**队列真没活可挪**且**不缺乏并行度**等条件下可以**先不抢**；否则 **`handoffp`** 把 P 交出去。

```go
func retake(now int64) uint32 {
	var n uint32
	for i := 0; i < len(allp); i++ {
		pp := allp[i]
		...
		s := pp.status
		if s == _Psyscall {
			t := &pp.sysmontick
			if t.syscallwhen == 0 {
				t.syscallwhen = now
				continue
			}
			if t.syscalltick != pp.syscalltick {
				// 进过 syscall 核心里了，tick 更新过 → 这次先不 handoff
				t.syscallwhen = now
				t.syscalltick = pp.syscalltick
				continue
			}
			// 超过约 10μs 且在「有排队且没有闲粮」等条件下才 handoff（条件与源码一致）
			if runqempty(pp) &&
				sched.nmspinning.Load()+sched.npidle.Load() > 0 &&
				t.syscallwhen+10*1000 > now {
				continue
			}
			if handoffp(pp) {
				n++
			}
			continue
		}
		if s == _Prunning {
			t := &pp.sysmontick
			if t.schedwhen == 0 {
				t.schedwhen = now
				continue
			}
			if t.schedtick != pp.schedtick {
				// 发生过调度，说明换过事了
				t.schedwhen = now
				t.schedtick = pp.schedtick
				continue
			}
			// 同一轮上 schedtick 没变，且超过抢占阈值
			if now-t.schedwhen >= forcePreemptNS {
				preemptone(pp)
			}
			...
		}
	}
	return n
}
```

### 3.3 `preemptone` / `preemptM`：协作标记 + 信号

```go
func preemptone(pp *p) bool {
	mp := pp.m.ptr()
	if mp == nil || mp.curg == nil {
		return false
	}
	gp := mp.curg
	...

	// 协作式路径：打标 + stack guard，等函数序言里的检查触发
	gp.preempt = true
	gp.stackguard0 = stackPreempt

	// 异步抢占：对绑定 M 发 SIGURG（或等价信号），内核打断后走进抢占逻辑
	if preemptMSupported && debug.asyncpreemptoff == 0 {
		pp.preempt = true
		preemptM(mp)
	}
	return true
}

func preemptM(mp *m) {
	...
	signalM(mp, _SIGURG) // 实际符号名见平台实现，语义：让该 M 上跑的 G 尽快进入可抢占点
	...
}
```

### 3.4 `handoffp`：P 交给谁？

`handoffp` 决定「这个 P 是立刻 **`startm` 拉人干活**，还是 **`pidleput` 挂回空闲链表**」。大意如下：

```go
func handoffp(pp *p) {
	lock(&sched.lock)

	// 本地或全局还有 runnable → 直接找 M 接 P
	if !runqempty(pp) || sched.runqsize != 0 {
		startm(pp, false, false)
		unlock(&sched.lock)
		return
	}
	// trace reader / GC mark 等有专活要跑在当前 P 上
	if (traceEnabled() || traceShuttingDown()) && traceReaderAvailable() != nil {
		startm(pp, false, false)
		unlock(&sched.lock)
		return
	}
	if gcBlackenEnabled != 0 && gcMarkWorkAvailable(pp) {
		startm(pp, false, false)
		unlock(&sched.lock)
		return
	}
	// 既没队列活，也没有自旋/空闲 M 在找活 → 可能需要强行 spin 一枚 M 避免全员睡死
	if sched.nmspinning.Load()+sched.npidle.Load() == 0 &&
		sched.nmspinning.CompareAndSwap(0, 1) {
		sched.needspinning.Store(0)
		startm(pp, true, false)
		unlock(&sched.lock)
		return
	}
	...
	unlock(&sched.lock)

	// 没有马上要的活：P 进空闲链表，等以后 `wakep` 等路径再捞起来
	when := pp.timers.wakeTime()
	pidleput(pp, 0)
	if when != 0 {
		wakeNetPoller(when)
	}
}
```

---

## 4. 系统调用链路：`Syscall` → `entersyscall` / `exitsyscall`

系统调用是吞吐痛点：**G 进内核后，P 不宜长期被占死**。用户态常用 `syscall.Syscall` 一类封装，进/出内核前后会 hook runtime。

### 4.1 `syscall.Syscall`：薄封装

```go
func Syscall(trap, a1, a2, a3 uintptr) (r1, r2 uintptr, err Errno) {
	Entersyscall()
	r, _, err := syscall6(..., trap, a1, a2, a3, 0, 0, 0)
	Exitsyscall()
	return r, 0, err
}
```

不同平台 `syscall6` 名/参数略不同；要点是：**前后各有一句** `Entersyscall` / `Exitsyscall`（或等价的 `reentersyscall` 路径）。

### 4.2 进入 syscall：先解绑 P

`entersyscall` 只做取栈帧并转 `reentersyscall`；**解绑与改 P 状态**在 `reentersyscall`：

1. `gp.m.oldp`：记下「我是从哪个 P 下来的」，**退出时优先认领**。
2. `pp.m = 0`、`gp.m.p = 0`：**M 与 P 暂时分手**，别的 M 才能通过 `handoffp` 等手段借走这个 P。
3. `pp.status = _Psyscall`：**sysmon / retake** 依赖该状态做「是否回收 P」的判断。

```go
func entersyscall() {
	fp := getcallerfp()
	reentersyscall(sys.GetCallerPC(), sys.GetCallerSP(), fp)
}

func reentersyscall(pc, sp, bp uintptr) {
	...
	pp := gp.m.p.ptr() // 当前 G 绑定的 P
	pp.m = 0
	atomic.Store(&pp.status, _Psyscall)
	gp.m.oldp.set(pp)
	gp.m.p = 0
	...
}
```

### 4.3 退出 syscall：快路径 vs 慢路径

G 从 syscall 返回时要**先抢到一个 P** 才能继续跑用户代码。

1. **`exitsyscallfast`**：尽量**认领 `oldp`**，或从 **`sched.pidle`** 捞一个空闲 P；成功则 `wirep` 绑回去，**仍在当前 M 上**接着跑。
2. **`exitsyscall0`（经 `mcall`）**：**所有 P 都忙/抢不到**，则把 G 置为 `_Grunnable`，**解除与当前 M 的绑定**，进全局队列（或后续 `pidleget` 成功则 `acquirep` 后直接 `execute`）；当前 M 可能 `stopm` / `schedule` **去睡觉或找别的活**。

```go
func exitsyscall() {
	gp := getg()
	...
	oldp := gp.m.oldp.ptr()
	gp.m.oldp = 0
	if exitsyscallfast(oldp) {
		...
		return
	}
	mcall(exitsyscall0)
}

func exitsyscallfast(oldp *p) bool {
	// 优先：尝试抢回离开 syscall 前记在 oldp 里的那个 P
	if oldp != nil && oldp.status == _Psyscall &&
		atomic.Cas(&oldp.status, _Psyscall, _Pidle) {
		wirep(oldp)
		...
		return true
	}
	// 其次：从全局空闲 P 链表拿一个（实现里常在 systemstack 上做）
	if sched.pidle != 0 {
		var ok bool
		systemstack(func() {
			ok = exitsyscallfast_pidle()
		})
		if ok {
			return true
		}
	}
	return false
}

func exitsyscall0(gp *g) {
	...
	casgstatus(gp, _Gsyscall, _Grunnable)
	...
	dropg()
	lock(&sched.lock)
	var pp *p
	if schedEnabled(gp) {
		pp, _ = pidleget(0)
	}
	if pp == nil {
		globrunqput(gp)
		...
		unlock(&sched.lock)
		stopm()
		schedule() // 当前 M 睡下或转去调度
	}
	...
	unlock(&sched.lock)
	acquirep(pp)
	execute(gp, false) // 不切走到这里：绑上 P 直接执行该 G
}
```

细节（`trace`、统计、`gc` 门槛等）以当前版本的 `proc.go` 为准；拎主线记这三步即可：**快路径抢 P → 慢路径入全局队列 → `stopm`/`schedule` 或 `acquirep`+`execute`**。

---

## 这篇你应该记住的 3 件事

1. 调度器主循环不复杂，复杂的是“找活顺序”和“状态管理”。
2. 抢占与 retake 是为了公平和吞吐，不是可有可无的优化项。
3. syscall 场景的关键是“P 不被长期占住”，所以有解绑、接管、快慢返回路径。

