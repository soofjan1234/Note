# select 源码

## 前言

本文是 **Go 运行时 `runtime/select.go` 中 `selectgo` 及相关辅助逻辑** 的阅读笔记：从编译器与 runtime 约定的 `scase` 布局写起，顺着 `pollorder` / `lockorder` 的构造、`sellock` 持锁后的快路径与阻塞路径、`sudog` 入队与 `gopark` 唤醒后的收尾，把多路 channel 选择拆成可对照源码的步骤；阅读前若对 `select` 语句本身尚不熟悉，可先看过 [select] 中的概念与示意图。

---

### case 与 scase

```go
// 编译器与 runtime 约定：每个 case 对应一个 scase，记录 channel 与元素指针。
type scase struct {
	c    *hchan         // 参与本 case 的 channel，nil 表示该路被编译器/反射置空
	elem unsafe.Pointer // 发送源或接收目标地址
}
```

以下为 runtime/select.go 摘录。

```go
// 空 select {}：无任何 case，当前 G 永久 gopark（与 channel 无关）。
func block() {
	gopark(nil, nil, waitReasonSelectNoCases, traceBlockForever, 1) // forever
}

// 按 lockorder 顺序对涉及的 channel 加锁；相邻重复 channel 只加一次。
func sellock(scases []scase, lockorder []uint16) {
	var c *hchan
	for _, o := range lockorder {
		c0 := scases[o].c
		if c0 != c {
			c = c0
			lock(&c.lock)
		}
	}
}

// 与 sellock 逆序解锁；同一 channel 连续出现时只解最后一次对应的锁。
func selunlock(scases []scase, lockorder []uint16) {
	for i := len(lockorder) - 1; i >= 0; i-- {
		c := scases[lockorder[i]].c
		if i > 0 && c == scases[lockorder[i-1]].c {
			continue
		}
		unlock(&c.lock)
	}
}

// gopark 在 select 里用的 commit：按 gp.waiting 链表顺序解开各 channel 的锁，再让 G 休眠。
func selparkcommit(gp *g, _ unsafe.Pointer) bool {
	// ... 按 gp.waiting 解锁各 channel（与 gopark 配对），见 select.go 63–100 行
	return true
}
```

### selectgo 总览

1. 对每个非 nil case 用随机插入构造 pollorder，再按各 channel 地址堆排序得到 lockorder，然后 sellock 锁住本次 select 涉及的全部 channel。
2. 第一轮按 pollorder 看是否已有 case 可立即执行：接收看 sendq、buf、是否已关闭；发送看是否已关闭、recvq、buf 是否有空位。能则完成收发或缓冲区读写，selunlock，返回选中下标与 recvOK。recvOK 只对接收有意义（例如从已关闭且无数据的 channel 读会得到 false）。
3. 若 block 为 false（有 default）且第一轮无人能执行：selunlock，返回下标 -1，表示走 default。
4. 若 block 为 true（无 default）：为每个 case 建 sudog，按收发挂到 sendq 或 recvq，gopark；被唤醒后按 lockorder 从各队列摘掉未选中的 sudog，完成中奖 case，selunlock，返回下标与 recvOK。

---

### 入口与切片布局

函数参数：

1. cas0：指向栈上的 [ncases]scase（ncases = nsends + nrecvs，且 ncases ≤ 65536）。
	- 每个元素对应一个非 default 的收发 case；编译器已填好 c、elem。
	- selectgo 从中选一个 case 执行并返回其下标。
2. order0：指向栈上的 [2*ncases]uint16 连续缓冲区（一整块内存，不是两个独立数组）。编译器不会为它初始化内容；真正写入顺序的是 selectgo 内部逻辑：
	- 前半段（长度 ncases）当作 pollorder；
	- 后半段（长度 ncases）当作 lockorder（数组里存的是 scase 下标，不是 channel 指针；排序依据是各 case 对应 *hchan 的地址，保证全序加锁）。
3. pc0：仅在 -race 构建下指向栈上 [ncases]uintptr，记录各 case 的调用 PC，供 race 标注；非 race 构建为 nil。
4. nsends、nrecvs：scases 里前 nsends 个为发送，后 nrecvs 个为接收（编译器生成时的约定顺序）。
5. block：false 表示有 default（可以非阻塞返回）；true 表示没有 default，第一轮无人可执行时必须阻塞。

函数返回值：

1. int：选中的 scase 下标（与源码里 case 顺序一致；选 default 时为 -1）。
2. bool（recvOK）：仅当选中的是接收 case 时有意义——是否真正收到一个值（例如从已关闭且无缓冲数据的 channel 读时为 false）。发送 case 不关心此返回值。

```go
func selectgo(cas0 *scase, order0 *uint16, pc0 *uintptr, nsends, nrecvs int, block bool) (int, bool) {
	gp := getg()
	cas1 := (*[1 << 16]scase)(unsafe.Pointer(cas0))
	order1 := (*[1 << 17]uint16)(unsafe.Pointer(order0))
	ncases := nsends + nrecvs
	scases := cas1[:ncases:ncases]
	pollorder := order1[:ncases:ncases]           // 指向前 ncases 个 uint16：随机轮询顺序（存 case 下标）
	lockorder := order1[ncases:][:ncases:ncases] // 指向后 ncases 个 uint16：加锁顺序（存 case 下标）
```

Go 里除了常见的 s[low:high]，还可以写 s[low:high:max]
1. pollorder := order1[:ncases:ncases]
	- 长度 len = ncases（最多能装 ncases 个 uint16）；容量 cap 也 = ncases
2. lockorder := order1[ncases:][:ncases:ncases]
	- 先 order1[ncases:]：从下标 ncases 切到末尾，即指向「后半段」起点。
	- 再 [:ncases:ncases]：在这后半段里再取前 ncases 个元素，容量也是 ncases。
	- 效果：lockorder 只覆盖「后半段」这 ncases 个槽。

---

### pollorder：随机插入

对每个非 nil case 用随机插入构造 pollorder，避免总是优先检查固定下标的 case（公平性）。norder 同时用于截断 pollorder、lockorder 的有效长度。

```go
	norder := 0
	for i := range scases {
		cas := &scases[i]
		if cas.c == nil {
			cas.elem = nil
			continue
		}
		// ... synctest、timer，略
		j := cheaprandn(uint32(norder + 1)) // j 在 [0, norder] 上均匀随机
		pollorder[norder] = pollorder[j]
		pollorder[j] = uint16(i)
		norder++
	}
	pollorder = pollorder[:norder]
	lockorder = lockorder[:norder]
```

最终有效排列长度是 norder

---

### lockorder：按 channel 地址排序

对 lockorder 按各 Hchan 地址做堆排序，保证全序加锁，避免死锁。算法分两段，都是经典堆操作

```go
for i := range lockorder {
	j := i
	// Start with the pollorder to permute cases on the same channel.
	c := scases[pollorder[i]].c
	for j > 0 && scases[lockorder[(j-1)/2]].c.sortkey() < c.sortkey() {
		k := (j - 1) / 2
		lockorder[j] = lockorder[k]
		j = k
	}
	lockorder[j] = pollorder[i]
}
for i := len(lockorder) - 1; i >= 0; i-- {
	o := lockorder[i]
	c := scases[o].c
	lockorder[i] = lockorder[0]
	j := 0
	for {
		k := j*2 + 1
		if k >= i {
			break
		}
		if k+1 < i && scases[lockorder[k]].c.sortkey() < scases[lockorder[k+1]].c.sortkey() {
			k++
		}
		if c.sortkey() < scases[lockorder[k]].c.sortkey() {
			lockorder[j] = lockorder[k]
			j = k
			continue
		}
		break
	}
	lockorder[j] = o
}
```

---

### sellock 与局部变量

waitReason 一般为 waitReasonSelect（synctest 等场景可替换）。sellock 之后才能在持锁状态下走快路径与阻塞路径。下面一组变量贯穿 pass2 唤醒与各个 goto 标签。

```go
	// ... 按 Hchan 地址堆排序 lockorder（两处 for），见上文「lockorder」

	waitReason := waitReasonSelect
	// ... synctest 时可为 waitReasonSynctestSelect，略

	sellock(scases, lockorder) // 上文已有，已持锁后再做快路径与阻塞路径

	var (
		sg              *sudog
		c               *hchan
		cas             *scase
		casi            int
		caseSuccess     bool // 唤醒后：接收是否收到值 / 发送是否成功（关闭时为 false）
		caseReleaseTime int64 = -1
		recvOK          bool // 最终返回：对接收 case 表示是否收到有效值
		k               *scase
		sglist          *sudog
		sgnext          *sudog
		qp              unsafe.Pointer
		nextp           **sudog
	)
```

---

### pass 1：按 pollorder 快路径

语义与单独 chansend、chanrecv 快路径一致：接收优先与 sendq 交接、再读 buf、再处理关闭；发送先判关闭、再与 recvq 交接、再写 buf。

```go
	// pass 1：按 pollorder 尝试立即完成，语义与单独 chansend/chanrecv 快路径一致。
	for _, casei := range pollorder {
		casi = int(casei)
		cas = &scases[casi]
		c = cas.c
		if casi >= nsends {
			// 接收：先等有无人发送；再 buf；再关闭
			sg = c.sendq.dequeue()
			if sg != nil {
				goto recv // 与等待中的发送者直接交接
			}
			if c.qcount > 0 {
				goto bufrecv // 从环形 buf 读
			}
			if c.closed != 0 {
				goto rclose // 已关闭且无数据可读
			}
		} else {
			// 发送：先判关闭；再等接收者；再 buf
			if raceenabled {
				racereadpc(c.raceaddr(), casePC(casi), chansendpc)
			}
			if c.closed != 0 {
				goto sclose // 往已关闭 channel 发 → panic
			}
			sg = c.recvq.dequeue()
			if sg != nil {
				goto send // 与等待中的接收者交接
			}
			if c.qcount < c.dataqsiz {
				goto bufsend // 写入环形 buf
			}
		}
	}
```

分支在后文

---

### 有 default：直接返回 -1

有 default 且第一轮无人能执行时不阻塞，下标 -1 表示走 default。

```go
	if !block {
		selunlock(scases, lockorder)
		casi = -1
		goto retc
	}
```

---

### pass 2：入队与 gopark

无 default 时，每个 case 挂一个 sudog，可同时排在多个 channel 的等待队列上；gopark 时由 selparkcommit 释放 channel 锁。

```go
	// pass 2：无 default 时，每个 case 挂一个 sudog，同时排在多个 channel 的等待队列上。
	nextp = &gp.waiting
	for _, casei := range lockorder {
		...
		sg := acquireSudog()
		...
		if casi < nsends {
			c.sendq.enqueue(sg)
		} else {
			c.recvq.enqueue(sg)
		}
		if c.timer != nil {
			blockTimerChan(c)
		}
	}

	gp.param = nil
	gp.parkingOnChan.Store(true)
	gopark(selparkcommit, nil, waitReason, traceBlockSelect, 1) // selparkcommit 内会释放 channel 锁
	gp.activeStackChans = false
```

gopark+selparkcommit
1. 调用 gopark 时，当前还握着这次 select 在 sellock 里加上的那些 channel 锁。若带着锁去睡，别人就没法改 channel 状态，会死锁。
2. 所以 gopark 的 commit 回调用的是 selparkcommit：在 G 真正挂起前，沿着 gp.waiting 里 sudog 的顺序，按约定顺序把相关 channel 的锁都解开。这样别的 M 上的 goroutine 才能对同一批 channel 做收发，从而在将来唤醒你。
3. 上文有 selparkcommit 函数

---

### 唤醒：重新加锁与取出中奖 sudog

唤醒者把中奖的 sudog 指针放在 gp.param。

```go
	sellock(scases, lockorder) // 被唤醒后重新加锁
	gp.selectDone.Store(0)
	sg = (*sudog)(gp.param) // 唤醒者把中奖的 sudog 指针放在 gp.param
	gp.param = nil
```

---

### pass 3：沿 lockorder 摘掉未中奖 sudog

与 gp.param 匹配的那路即为中奖 case；其余 channel 上从对应队列 dequeueSudoG 摘掉并 releaseSudog。若选中发送且 channel 在等待期间关闭，caseSuccess 为 false，后续走 sclose panic。

```go
	// pass 3：沿 lockorder 摘掉未选中的 sudog；与 gp.param 匹配的那路即为中奖 case。
	casi = -1
	cas = nil
	caseSuccess = false
	sglist = gp.waiting
	// ... 遍历 gp.waiting，清除各 sudog 的 isSelect/elem/c；gp.waiting = nil

	for _, casei := range lockorder {
		k = &scases[casei]
		if k.c.timer != nil {
			unblockTimerChan(k.c)
		}
		if sg == sglist {
			casi = int(casei)
			cas = k
			caseSuccess = sglist.success
			if sglist.releasetime > 0 {
				caseReleaseTime = sglist.releasetime
			}
		} else {
			c = k.c
			if int(casei) < nsends {
				c.sendq.dequeueSudoG(sglist)
			} else {
				c.recvq.dequeueSudoG(sglist)
			}
		}
		sgnext = sglist.waitlink
		sglist.waitlink = nil
		releaseSudog(sglist)
		sglist = sgnext
	}
	if cas == nil {
		throw("selectgo: bad wakeup")
	}
	c = cas.c
	if casi < nsends {
		if !caseSuccess {
			goto sclose
		}
	} else {
		recvOK = caseSuccess // 接收：recvOK 即「是否收到值」
	}
	...
	selunlock(scases, lockorder)
	goto retc
```

---

### 标签 bufrecv / bufsend：环形缓冲区

快路径命中缓冲区时，从 recvx、sendx 读写环形 buf，更新 qcount 后解锁返回。

```go
bufrecv:
	// ... race/msan/asan，见 446–459 行
	recvOK = true
	qp = chanbuf(c, c.recvx) // 从环形缓冲区头部取一槽
	if cas.elem != nil {
		typedmemmove(c.elemtype, cas.elem, qp)
	}
	typedmemclr(c.elemtype, qp)
	c.recvx++
	if c.recvx == c.dataqsiz {
		c.recvx = 0
	}
	c.qcount--
	selunlock(scases, lockorder)
	goto retc
bufsend:
	// ... race/msan/asan，见 476–485 行
	typedmemmove(c.elemtype, chanbuf(c, c.sendx), cas.elem) // 写入环形缓冲区尾部
	c.sendx++
	if c.sendx == c.dataqsiz {
		c.sendx = 0
	}
	c.qcount++
	selunlock(scases, lockorder)
	goto retc
```

---

### 标签 recv / send：与对端 sudog 交接

与 chan.go 中的 recv、send 相同，解锁回调里调用 selunlock。

```go
recv:
	recv(c, sg, cas.elem, func() { selunlock(scases, lockorder) }, 2) // 与 chan.go 的 recv 相同
	recvOK = true
	goto retc
send:
	// ... race/msan/asan，见 518–526 行
	send(c, sg, cas.elem, func() { selunlock(scases, lockorder) }, 2) // 与 chan.go 的 send 相同
	goto retc
```

---

### 标签 rclose：已关闭且无数据

对应 v, ok := <-ch 中 ok 为 false；若有接收目标地址则清零。

```go
rclose:
	selunlock(scases, lockorder)
	recvOK = false // 已关闭且无数据，对应 v, ok := <-ch 中 ok 为 false
	if cas.elem != nil {
		typedmemclr(c.elemtype, cas.elem)
	}
	if raceenabled {
		raceacquire(c.raceaddr())
	}
	goto retc
```

---

### 返回与往已关闭 channel 发送

retc 里可做阻塞剖析；sclose 与 chansend 关闭语义一致。

```go
retc:
	if caseReleaseTime > 0 {
		blockevent(caseReleaseTime-t0, 1) // 阻塞剖析
	}
	return casi, recvOK
sclose:
	selunlock(scases, lockorder)
	panic(plainError("send on closed channel")) // 与 chansend 关闭语义一致
}
```
