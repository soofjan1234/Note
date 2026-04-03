# 内存回收源码（二）：并发标记与 Assist

## 前言

本文接第一篇中的 **II. 并发标记阶段**，展开 **1）Worker**（`gcBgMarkWorker`、三种 `gcDrainMarkWorker*`）与 **2）Assist**（`gcAssistBytes`、`gcAssistAlloc` 链、`gcDrainN`、`gcParkAssist`）。三色与写屏障见第三篇。

---

### II. 并发标记阶段（续）

**1）Worker**

调度器通过 **`gcController.findRunnableGCWorker`** 唤醒每个 P 上的 **`gcBgMarkWorker`**。真正「吃根任务、从 `gcWork` 取址、`scanobject`」的活都由底层的 **`gcDrain`** 完成（详见「三色标记法」）；三种 **`gcDrainMarkWorker*`** 只是给它套上**不同的抢占与退出条件**，好控制 CPU 占用和调度公平性。

`runtime/mgc.go`：

```go
type gcMarkWorkerMode int

const (
	gcMarkWorkerNotWorker gcMarkWorkerMode = iota

	// 这颗 P 专门跑标记，尽量把活干满 
	gcMarkWorkerDedicatedMode

	// 让 GC 标记工作占用 CPU 的比例严格等于 25%
	gcMarkWorkerFractionalMode

	// P 上没有普通 G 可跑时，用空档帮 GC.
	gcMarkWorkerIdleMode
)
```

Dedicated是只要 GC 没完，它就占死这个 CPU 核心，不被抢占。
Go GC 的设计目标是消耗全站 25% 的 CPU 预算。假设你的电脑是 6 核（GOMAXPROCS = 6），那么6 * 25% = 1.5 个核心。
如果开 1 个 Dedicated Worker（专职），只用了 1/6，干活慢了。如果开 2 个 Dedicated Worker（专职），用了 2/6，业务受影响了。
这时候，那个 “0.5” 的缺口，就由 Fractional 来补齐。

**`gcBgMarkWorker` 在做什么**

1. 初始化：这个专门跑后台标记的 goroutine 已经完成自己的初始化，并通过 ready channel 通知「我可以进入后面的 gopark 等待被调度了」。
2. 大循环：
	1. 本轮开始干活前：在真正把 G 挂起之前多做两件事：放还 M、把 node 还回池子。
	2. 记账 nwait：对 work.nwait 做原子减一，表示有一个 worker 从「闲着」变成「正在 drain」。
	3. 在 systemstack 上：把当前 G 切成可被挂起扫描的状态，再调用三种 gcDrainMarkWorker 之一。
	4. 收尾：对 nwait 原子加一，表示这一轮 drain 做完、槽位还回去。
	5. 若此时 nwait 已等于 nproc（大家都还完槽），且 gcMarkWorkAvailable 认为全局也没有更多标记活，就 releasem 并调用 gcMarkDone，进入分布式收尾。

摘录骨架（省略 trace、limiter 等，`runtime/mgc.go`）：

```go
func gcBgMarkWorker(ready chan struct{}) {
	// 第一步：初始化
	gp := getg()
	// ... 短暂 preemptoff，堆上 new node，node.gp / node.m ...
	// 标记 G 已经就绪
	ready <- struct{}{}

	// 第二步：大循环
	for {
		// 平时在 gopark 里睡眠，入睡前要执行的收尾
		gopark(func(g *g, nodep unsafe.Pointer) bool {
			node := (*gcBgMarkWorkerNode)(nodep)
			if mp := node.m.ptr(); mp != nil {
				releasem(mp)
			}
			gcBgMarkWorkerPool.push(&node.node)
			return true
		}, unsafe.Pointer(node), waitReasonGCWorkerIdle, traceBlockSystemGoroutine, 0)

		// ... 
		// 有一个 worker 从闲着变成正在 drain
		atomic.Xadd(&work.nwait, -1)
		systemstack(func() {
			// 切状态
			casGToWaitingForSuspendG(gp, _Grunning, waitReasonGCWorkerActive)
			// 调用对应的worker
			switch pp.gcMarkWorkerMode {
			case gcMarkWorkerDedicatedMode:
				gcDrainMarkWorkerDedicated(&pp.gcw, true)
				// 若 preempt：runqdrain → globrunqputbatch
				gcDrainMarkWorkerDedicated(&pp.gcw, false)
			case gcMarkWorkerFractionalMode:
				gcDrainMarkWorkerFractional(&pp.gcw)
			case gcMarkWorkerIdleMode:
				gcDrainMarkWorkerIdle(&pp.gcw)
			}
			casgstatus(gp, _Gwaiting, _Grunning)
		})

		// ...

		// 这一轮 drain 结束，这个 worker 还槽
		incnwait := atomic.Xadd(&work.nwait, +1)
		
		// ...
		
		// 从 worker 视角看，标记可以收摊了
		pp.gcMarkWorkerMode = gcMarkWorkerNotWorker
		if incnwait == work.nproc && !gcMarkWorkAvailable(nil) {
			releasem(node.m.ptr())
			node.m.set(nil)
			gcMarkDone()
		}
	}
}
```


**2）Assist**

如果说 **Worker** 是在按部就班地「打扫卫生」，那么 **Assist（辅助回收）** 就是一种强行的「交通管制」。

#### 1. 为什么需要 Assist？

在并发标记阶段，Worker（后台工人）按 25% CPU 预算扫描。如果 Mutator（业务 Goroutine）分配太快，Worker 忙不过来，堆就会炸。
Assist 的本质：强制让“跑得快”的 G 停下来，把分配内存的时间用来做标记，实现谁污染谁治理。

#### 2. 怎么运作？

1. 账户

g 上有字段 gcAssistBytes：正数可分配额度，负数要先做标记还债。
bgScanCredit：后台标记线程已经「干完」、但还没被 assist 立刻领走的「扫描工作量余额」

- 每轮标记前清零gcAssistBytes
- gcAssistBytes变多：assist 或偷 bgScanCredit 会攒正数
- bgScanCredit变多：G 退出时正余额可 flush 到全局 bgScanCredit。

```go
// runtime/mgc.go — gcResetMarkState
forEachG(func(gp *g) {
	gp.gcscandone = false
	gp.gcAssistBytes = 0
})
```

```go
// runtime/proc.go — goexit 片段
if gcBlackenEnabled != 0 && gp.gcAssistBytes > 0 {
	assistWorkPerByte := gcController.assistWorkPerByte.Load()
	scanCredit := int64(assistWorkPerByte * float64(gp.gcAssistBytes))
	gcController.bgScanCredit.Add(scanCredit)
	gp.gcAssistBytes = 0
}
```

2. deductAssistCredit

分配记账，扣成负数就调 gcAssistAlloc。

```go
// runtime/malloc.go
func deductAssistCredit(size uintptr) {
	assistG := getg()
	if assistG.m.curg != nil {
		assistG = assistG.m.curg
	}
	assistG.gcAssistBytes -= int64(size)
	if assistG.gcAssistBytes < 0 {
		gcAssistAlloc(assistG)
	}
}
```

3. gcAssistAlloc

- 把 gp.gcAssistBytes（协助额度，负的表示欠债）算成要完成的 scan work
- 欠债很小时，会故意让你多干一点点活（gcOverAssistWork），否则「每次只还一点点」，进进出出 assist 本身的开销反而比干活还大。
- 能蹭后台：偷 bgScanCredit 则只改账户不扫堆
- 否则自己干： systemstack 进 gcAssistAlloc1。在系统栈上真的去扫一阵（gcDrainN 那种），把剩下的 scanWork 做掉

```go
// runtime/mgcmark.go — gcAssistAlloc（节选）
func gcAssistAlloc(gp *g) {
	// ... 
retry:
	// ... 

	// 从 gcController 取「每分配 1 字节应对应多少 scan work」及「每单位 work 可折算多少字节额度」
	assistWorkPerByte := gcController.assistWorkPerByte.Load()
	assistBytesPerWork := gcController.assistBytesPerWork.Load()
	debtBytes := -gp.gcAssistBytes // 当前欠债（分配记账扣成负的绝对值）
	scanWork := int64(assistWorkPerByte * float64(debtBytes))

	// 过小则抬到 gcOverAssistWork，并反算 debtBytes：多 assist 一点，摊薄进 assist 的固定开销
	if scanWork < gcOverAssistWork {
		scanWork = gcOverAssistWork
		debtBytes = int64(assistBytesPerWork * float64(scanWork))
	}

	// 先用后台标记线程积累的 bgScanCredit「抵债」，只改账户，不一定真的扫堆
	bgScanCredit := gcController.bgScanCredit.Load()
	stolen := int64(0)
	if bgScanCredit > 0 {
		if bgScanCredit < scanWork {
			stolen = bgScanCredit
			gp.gcAssistBytes += 1 + int64(assistBytesPerWork*float64(stolen))
		} else {
			stolen = scanWork
			gp.gcAssistBytes += debtBytes
		}
		gcController.bgScanCredit.Add(-stolen)
		scanWork -= stolen
		if scanWork == 0 {
			return // 偷来的信用已覆盖本轮 scanWork，无需 gcAssistAlloc1
		}
	}

	// 剩余 scanWork 在系统栈上 gcDrainN；避免用户栈在标记过程中移动
	systemstack(func() {
		gcAssistAlloc1(gp, scanWork)
	})

	// gcAssistAlloc1 若让本轮 mark 全局收尾，会置 gp.param
	completed := gp.param != nil
	gp.param = nil
	if completed {
		gcMarkDone()
	}
	// 仍欠债：抢占点则让出后再 retry；否则进 assist 队列等后台 credit（或周期结束）
	if gp.gcAssistBytes < 0 {
		// 不立刻去排队睡觉，而是 Gosched() 主动让出
		if gp.preempt {
			Gosched()
			goto retry
		}
		if !gcParkAssist() {
			goto retry
		}
	}
	// ... trace GCMarkAssistDone ...
}
```

gcParkAssist()见下文

4. gcAssistAlloc1 与 gcDrainN

在系统栈上 确认还在不在 blacken
- gcBlackenEnabled != 0 ：这轮 GC 还在并发标记涂色阶段
- gcBlackenEnabled == 0 ：这轮标记阶段已经结束（或未到标记段）

短暂把自己当成并发 marker 的一员
用 gcDrainN 做定额扫描
按 workDone 还额度
若刚好 全员收工且无剩余 work 则 置 gp.param 让外层 gcMarkDone

```go
// runtime/mgcmark.go — gcAssistAlloc1（节选）
func gcAssistAlloc1(gp *g, scanWork int64) {
	gp.param = nil // 先清「本轮是否收尾整段 mark」标记；若下面置位，gcAssistAlloc 会 gcMarkDone
	if atomic.Load(&gcBlackenEnabled) == 0 {
		// 与 malloc 里对 gcBlackenEnabled 的判读竞态：在不可抢占的系统栈上再确认一次；标记阶段已结束则债一笔勾销
		gp.gcAssistBytes = 0
		return
	}
	// ... 

	// 参与「并发标记 worker」计数：暂离等待集合，gcDrainN 期间需可抢占
	decnwait := atomic.Xadd(&work.nwait, -1)
	casGToWaitingForSuspendG(gp, _Grunning, waitReasonGCAssistMarking)
	gcw := &getg().m.p.ptr().gcw
	workDone := gcDrainN(gcw, scanWork) // 在本 P 的 gcWork 上最多刷够 scanWork 的扫描量
	casgstatus(gp, _Gwaiting, _Grunning)

	// 按实际 workDone 折算成「分配额度」加回 gcAssistBytes；+1 为防 assistBytesPerWork 极小时加不出信用
	assistBytesPerWork := gcController.assistBytesPerWork.Load()
	gp.gcAssistBytes += 1 + int64(assistBytesPerWork*float64(workDone))
	incnwait := atomic.Xadd(&work.nwait, +1)
	// ... 
	// 若自己是「最后一个归队的 worker」且全局已没有更多 mark work，则通知外层：可走 gcMarkDone 收尾
	if incnwait == work.nproc && !gcMarkWorkAvailable(nil) {
		gp.param = unsafe.Pointer(gp) // 非 nil 即可，gcAssistAlloc 里据此调 gcMarkDone
	}
	// ... 
}
```

`gcDrainN` 消费本 P 上 `gcWork` 里的「待扫」队列（抽象上的**灰**对象/frontier），后台 marker 的 `gcDrain` 也是同类循环。三色不变式与写屏障为何能并发成立放在《内存回收源码(3)》。

5. gcParkAssist

仍欠账且未因抢占让出时，进 assist 队列 gopark；周期结束或 bgScanCredit 来了会醒。
- true：要么 mark 已结束不用睡，要么 睡完被正常唤醒，assist 队列这一程结束。
- false：已入队但又发现 bgScanCredit > 0，撤销入队，让调用方 retry 去偷信用

```go
// runtime/mgcmark.go — gcParkAssist（节选）
func gcParkAssist() bool {
	lock(&work.assistQueue.lock)
	if atomic.Load(&gcBlackenEnabled) == 0 {
		unlock(&work.assistQueue.lock)
		return true // GC 已结束，assist 无需再睡，上层可视为已还清
	}
	gp := getg()
	oldList := work.assistQueue.q
	work.assistQueue.q.pushBack(gp) // 先挂进队列
	// 入队后若已有 bgScanCredit，撤销入队并返回 false，让调用方 retry（与后台 flush 竞态）
	if gcController.bgScanCredit.Load() > 0 {
		work.assistQueue.q = oldList
		if oldList.tail != 0 {
			oldList.tail.ptr().schedlink.set(nil)
		}
		unlock(&work.assistQueue.lock)
		return false
	}
	goparkunlock(&work.assistQueue.lock, waitReasonGCAssistWait, traceBlockGCMarkAssist, 2)
	return true // 被唤醒：要么 credit 到了，要么周期结束
}
```

链：malloc 扣 gcAssistBytes 到 gcAssistAlloc 算账与偷信用，到 gcAssistAlloc1 调 gcDrainN，不够则 gcParkAssist。
