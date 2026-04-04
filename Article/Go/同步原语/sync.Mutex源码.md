## sync.Mutex

```go
type Mutex struct {
	_ noCopy

	mu isync.Mutex
}

// isync "internal/sync"
type Mutex struct {
	state int32 // 一个 int32 里用位表示「是否加锁、是否唤醒中、是否饥饿、等待者个数」
	sema  uint32 // 信号量，用来在抢不到锁时 sleep / 被 Unlock 时 wake 一个 waiter。
}

const (
	mutexLocked      = 1 << 0   // 1：当前有人持有锁
	mutexWoken       = 1 << 1   // 2：已有 goroutine 被唤醒（或正在自旋），Unlock 不必再唤醒别人
	mutexStarving    = 1 << 2   // 4：饥饿模式
	mutexWaiterShift = 3        // 高 29 位：等待者数量
)
```

### Lock

1. **快速路径**：当前 state == 0（没人持锁、没人等），CAS 成 mutexLocked 就拿到锁，直接 return。
2. **否则**进 **lockSlow()**，里面做自旋、排队、饥饿切换等。

```go
func (m *Mutex) Lock() {
	if atomic.CompareAndSwapInt32(&m.state, 0, mutexLocked) {
		...
		return
	}
	m.lockSlow()
}
```

```go
func (m *Mutex) lockSlow() {
	...
	for {
		// 当前有人持锁且不是饥饿模式，开始自旋
		if old&(mutexLocked|mutexStarving) == mutexLocked && runtime_canSpin(iter) {
			if !awoke && old&mutexWoken == 0 && old>>mutexWaiterShift != 0 &&
				atomic.CompareAndSwapInt32(&m.state, old, old|mutexWoken) {
				//别去叫醒队列里的兄弟了，我已经在这等着抢了
				awoke = true
			}
			runtime_doSpin()
			iter++
			old = m.state
			continue
		}
		new := old
		if old&mutexStarving == 0 {
			new |= mutexLocked // 只要不是饥饿模式，就尝试抢锁
		}
		if old&(mutexLocked|mutexStarving) != 0 {
			new += 1 << mutexWaiterShift // 如果锁被占或在饥饿模式，自己乖乖去排队，等待者+1
		}
		if starving && old&mutexLocked != 0 {
			new |= mutexStarving // 如果我已经等了超过 1ms，就把锁标记为饥饿模式
		}
		...
		if atomic.CompareAndSwapInt32(&m.state, old, new) {
			if old&(mutexLocked|mutexStarving) == 0 {
				break // 成功抢到锁，大功告成
			}
			// 抢不到，调用信号量进入休眠
			queueLifo := waitStartTime != 0
			if waitStartTime == 0 {
				waitStartTime = runtime_nanotime()
			}
			runtime_SemacquireMutex(&m.sema, queueLifo, 2)
			// 被唤醒后，检查自己等了多久，如果太久，开启饥饿标记
			starving = starving || runtime_nanotime()-waitStartTime > starvationThresholdNs
			// 睡眠期间别的 G 可能已 `Unlock`、改过 `state`，唤醒后必须重新读
			old = m.state
			// 全局已处于饥饿模式。Unlock 走 handoff，不会在 state 里先替你置 mutexLocked；
			// 被唤醒者看到的是中间态：锁位未按常规置上，但等待者计数里还有你。
			if old&mutexStarving != 0 {
				// handoff：所有权从上一个 Unlock 交给队首等待者
				if old&(mutexLocked|mutexWoken) != 0 || old>>mutexWaiterShift == 0 {
					throw("sync: inconsistent mutex state")
				}
				// delta 一次性修正：+mutexLocked 表示本 G 已持锁；-waiterShift 把自己从等待者里减掉
				delta := int32(mutexLocked - 1<<mutexWaiterShift)
				if !starving || old>>mutexWaiterShift == 1 {
					// 如果我是最后一个人，或者我等的没那么久了，退出饥饿模式
					delta -= mutexStarving
				}
				atomic.AddInt32(&m.state, delta)
				break // 饥饿路径上锁与 waiter 数已对齐，等价加锁成功
			}
			// 正常模式下被唤醒，继续循环去 CAS 抢锁
			awoke = true
			iter = 0
		} else {
			old = m.state
		}
	}

	if race.Enabled {
		race.Acquire(unsafe.Pointer(m))
	}
}
```

1. 谁先醒来？是不是「同一个 G」？
不管饥饿还是正常，从 runtime_SemacquireMutex 醒来的，始终是「当初调用 Lock()、在信号量上睡下去的那一个 G」，不会偷偷换成别的 goroutine。
所以不存在「正常 = 刚刚的 go、饥饿 = 另一个 go」这种对比；醒来的永远是排队睡着的那个自己。

2. 饥饿分支 vs 正常分支，差在「全局状态」和「拿锁方式」
- old & mutexStarving != 0（走 83–95 这段）
表示此时 mutex 整体处在饥饿模式。上一次 Unlock 走的是 handoff（详情看下文）：把锁交给 等待队列队首 的那一个 waiter，并且 不会在 state 里按平常那样先帮你把 mutexLocked 置好。
所以能进这个分支的，就是 这次被 handoff 唤醒的、队首等待者（也就是你问的「饥饿时队首」——对）。

- mutexStarving == 0（走下面 awoke = true; iter = 0）
表示 不是 饥饿模式下的那次 handoff。你被 Unlock 用普通的 Semrelease 叫醒，锁在语义上仍是大家抢，没有在「饥饿协议」里把所有权直接塞给你。
所以你要 再绕 for 一圈，用 CAS 去抢锁，还可能和新来的 G 竞争——不是「正常 = 刚刚的 go、饥饿 = 队首」这种二分，而是 正常 = 全局未饥饿，按老规则抢；饥饿 = 全局饥饿，你是队首且按 handoff 规则用 delta 把状态补齐。

### TryLock

1. 若已经**加锁**或处于**饥饿**（饥饿时锁要交给 waiter，不能给 TryLock），直接返回 false。
2. 否则 CAS 把 **mutexLocked** 置 1，成功返回 true，失败返回 false。**不排队、不自旋**。

```go
func (m *Mutex) TryLock() bool {
	old := m.state
	if old&(mutexLocked|mutexStarving) != 0 {
		return false
	}

	if !atomic.CompareAndSwapInt32(&m.state, old, old|mutexLocked) {
		return false
	}

	if race.Enabled {
		race.Acquire(unsafe.Pointer(m))
	}
	return true
}
```

### UnLock

```go
func (m *Mutex) Unlock() {
	if race.Enabled {
		_ = m.state
		race.Release(unsafe.Pointer(m))
	}

	// Fast path: drop lock bit.
	new := atomic.AddInt32(&m.state, -mutexLocked)
	if new != 0 {
		// Outlined slow path to allow inlining the fast path.
		// To hide unlockSlow during tracing we skip one extra frame when tracing GoUnblock.
		m.unlockSlow(new)
	}
}
```

- **检查**：若 (new+mutexLocked)&mutexLocked == 0，说明本来就没锁，**fatal("unlock of unlocked mutex")**。
- **非饥饿**：
    - 若没有 waiter，或已经有别人把锁/唤醒拿走了，直接 return。
    - 否则 CAS：waiter 数减 1、置上 **mutexWoken**，成功则 **runtime_Semrelease(&m.sema, ...)** 唤醒一个 waiter。
- **饥饿**：
    - 不抢锁，直接把**锁交给队头 waiter**

```go
func (m *Mutex) unlockSlow(new int32) {
	if (new+mutexLocked)&mutexLocked == 0 {
		fatal("sync: unlock of unlocked mutex")
	}
	if new&mutexStarving == 0 {
		old := new
		for {
			if old>>mutexWaiterShift == 0 || old&(mutexLocked|mutexWoken|mutexStarving) != 0 {
				return
			}
			// Grab the right to wake someone.
			new = (old - 1<<mutexWaiterShift) | mutexWoken
			if atomic.CompareAndSwapInt32(&m.state, old, new) {
				runtime_Semrelease(&m.sema, false, 2)
				return
			}
			old = m.state
		}
	} else {
		runtime_Semrelease(&m.sema, true, 2)
	}
}
```
### 补充

```go
// SemacquireMutex 与 Semacquire 类似，但用于带性能剖析的 Mutex / RWMutex 争用场景。
// lifo 为 true 时，把 waiter 放到等待队列头部（后进先出）。
// skipframes 为在 tracing 时要跳过的栈帧数，从 runtime_SemacquireMutex 的调用者算起。
// 该函数的不同形式只影响 runtime 如何在回溯里展示等待原因，以及部分指标计算；
// 除此以外行为上是一样的。
//
//go:linkname runtime_SemacquireMutex
func runtime_SemacquireMutex(s *uint32, lifo bool, skipframes int)

// Semrelease 原子地执行 *s + 1，若有 goroutine 阻塞在 Semacquire 上则唤醒其中一个。
// 用作同步库里的简单唤醒原语，不应对业务代码直接调用。
// handoff 为 true 时，把本次释放的许可直接交给队首等待者（handoff 语义）。
// skipframes 为 tracing 时要跳过的栈帧数，从 runtime_Semrelease 的调用者算起。
//
//go:linkname runtime_Semrelease
func runtime_Semrelease(s *uint32, handoff bool, skipframes int)
```


- `runtime_SemacquireMutex(&m.sema, ...)`：  
  - 先尝试：m.sema 现在“许可是否够用”
  - 如果许可够：不睡，直接返回，继续走 Lock() 后续（继续 CAS 抢锁）
  - 如果许可不够（常见是 0）：把当前 goroutine park（睡眠），并把它挂到“以 &m.sema 为标识的等待队列”上
- `runtime_Semrelease(&m.sema, ...)`：  
  - `Unlock()` 看到有人在等时，会“释放一个名额”并且**叫醒**某个睡着的 waiter。  
  - `handoff=true` 可以理解成更偏向“把这次机会直接交给队首第一个 waiter”（减少新来的插队）。