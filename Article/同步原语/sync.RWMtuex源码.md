## sync.RWMutex

`RWMutex` 是「读写锁」：
- 可以被多个读者（多个 goroutine）同时持有（`RLock`）
- 也可以被一个写者（单个 goroutine）独占持有（`Lock`）

零值可用：`RWMutex` 的零值表示“未加锁”。

### 内部结构（先建立直觉）

```go
type RWMutex struct {
	w           Mutex        // 写者之间的互斥：有 pending writers 时会用它排队
	writerSem   uint32       // 写者：等待“读者全部离开”的信号量
	readerSem   uint32       // 读者：等待“写者完成”的信号量
	readerCount atomic.Int32 // 读者计数：正数=活跃读者；负数=有写者待处理（编码）
	readerWait  atomic.Int32 // 正在退出的最后那部分读者数量：用于唤醒 writer
}

const rwmutexMaxReaders = 1 << 30
```

> 你看到的关键点是：RWMutex 不是一个 state+sema（像 Mutex 那样只有一份状态和一个 sema），而是：
> - 用 `readerCount` 来编码“读者数量/是否有写者等待”
> - 用 `readerSem` / `writerSem` 两套信号量分别控制“读者睡在等待写者完成”和“写者睡在等待读者离开”

### RLock

1. **快速路径**：`readerCount.Add(1) >= 0`，说明当前没有写者在等待/切换阶段，直接 return（自己变成一个活跃读者）。
2. **慢路径（被写者挡住）**：如果 `readerCount.Add(1) < 0`，说明已有写者待处理（读会被阻塞），就进入
   `runtime_SemacquireRWMutex(&rw.readerSem, ...)` 等写者完成。

```go
func (rw *RWMutex) RLock() {
	if rw.readerCount.Add(1) < 0 {
		runtime_SemacquireRWMutex(&rw.readerSem, false, 0)
	}
}
```

### TryRLock

1. **若 `readerCount` 为负**（表示写者 pending），直接返回 `false`。
2. 否则用 CAS 把 `readerCount` 从 `c` 改为 `c+1`，成功返回 `true`，失败重试。

```go
func (rw *RWMutex) TryRLock() bool {
	for {
		c := rw.readerCount.Load()
		if c < 0 {
			return false
		}
		if rw.readerCount.CompareAndSwap(c, c+1) {
			return true
		}
	}
}
```

### RUnlock

`RUnlock` 只影响“读者数量”，不影响其他同时读者。

1. **快速路径**：把 `readerCount` 减 1 后，如果结果仍合法且不表示需要特殊处理，就 return。
2. **慢路径（有写者 pending）**：当 `readerCount.Add(-1)` 得到的 `r < 0` 时，说明这次 unlock 可能触发写者：进入 `rUnlockSlow(r)`。
   - 如果这是“最后一个需要唤醒 writer 的读者”，就调用 `runtime_Semrelease(&rw.writerSem, ...)` 唤醒 writer。

```go
func (rw *RWMutex) RUnlock() {
	if r := rw.readerCount.Add(-1); r < 0 {
		rw.rUnlockSlow(r)
	}
}

func (rw *RWMutex) rUnlockSlow(r int32) {
	// A writer is pending.
	if rw.readerWait.Add(-1) == 0 {
		runtime_Semrelease(&rw.writerSem, false, 1)
	}
}
```

### Lock

写锁的核心目标是：**等所有活跃读者离开**，并且阻止新读者进入（直到写者拿到锁）。

1. **先解决写者之间竞争**：`rw.w.Lock()`，保证只有一个 writer 在“争写锁”。
2. **宣布写者 pending，阻塞新读者**：
   - 把 `readerCount` 做一个减法编码：`rw.readerCount.Add(-rwmutexMaxReaders)`。
   - 这样 `readerCount` 变成负数，后续读者 `RLock` 的快速路径会失败，进入等待。
3. **等待当前活跃读者离开**：
   - 计算出“当前还剩多少活跃读者”。
   - 如果 `r != 0` 且 `rw.readerWait.Add(r) != 0`，就阻塞到
     `runtime_SemacquireRWMutex(&rw.writerSem, ...)`。

```go
func (rw *RWMutex) Lock() {
	rw.w.Lock()
	r := rw.readerCount.Add(-rwmutexMaxReaders) + rwmutexMaxReaders
	if r != 0 && rw.readerWait.Add(r) != 0 {
		runtime_SemacquireRWMutex(&rw.writerSem, false, 0)
	}
}
```

### TryLock

1. 先 `rw.w.TryLock()`：如果别的 writer 正在持有/争抢，直接返回 `false`。
2. 再用 CAS 判断是否能把 `readerCount` 从 `0` 改到 `-rwmutexMaxReaders`：
   - 这表示“没有活跃读者，且把 future readers 挡住”的条件。
3. 成功返回 `true`，否则解锁 `rw.w` 并返回 `false`。

```go
func (rw *RWMutex) TryLock() bool {
	if !rw.w.TryLock() {
		return false
	}
	if !rw.readerCount.CompareAndSwap(0, -rwmutexMaxReaders) {
		rw.w.Unlock()
		return false
	}
	return true
}
```

### UnLock

写锁释放的核心是两件事：
- **释放写者状态：让等待的读者继续**
- **放行下一个 writer：rw.w.Unlock()**

1. **宣布没有 active writer**：`rw.readerCount.Add(rwmutexMaxReaders)`。
2. **唤醒被阻塞的读者**：如果释放后 `r` 表示“可以唤醒的 reader 数量”，就循环 `runtime_Semrelease(&rw.readerSem, ...)` 把对应数量的 reader 释放出来。
3. **允许其他 writer**：`rw.w.Unlock()`。

```go
func (rw *RWMutex) Unlock() {
	r := rw.readerCount.Add(rwmutexMaxReaders)
	for i := 0; i < int(r); i++ {
		runtime_Semrelease(&rw.readerSem, false, 0)
	}
	rw.w.Unlock()
}
```

