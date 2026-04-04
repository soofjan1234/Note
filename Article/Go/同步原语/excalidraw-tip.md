# 同步原语篇 · Excalidraw 作画清单

本文与项目内 **Excalidraw Diagram** 技能对齐：用 Obsidian 格式将图写到本地 `.md`，在 Obsidian 中切到 **Excalidraw** 视图编辑。

## 1.md
### sync.Mutex
一个锁图标 连接两个圆角框 
一个是API 写了三个函数和用途（你会用到的 API
一个是内部结构和用途

再下面是讲state
长一点的框 4个格子  表示32位整数
有对应的箭头表示 这里是干嘛干嘛的

### 加锁
流程节点（按时间顺序）：
- `Lock()`
- 分支：`state/locked 是否空闲？`
- 快路径节点：`CAS 抢锁成功 -> 返回`
- 慢路径节点：`自旋（正常模式下的短暂重试）`
- 分支节点：`自旋失败 / 或不允许自旋？`
- 节点：`登记自己到 state（waiter count + 需要等待）`
- 节点：`睡眠 park`
- 节点：`醒来时记录等待时长，并判断是否要进入饥饿（starving）`
- 节点：`被 Unlock() unpark`
- 分支：`当前是否处于 starving（旧 state 里 starving 位为 1）？`
- 子分支 1（正常模式）：`回到 Lock() 的状态检查/尝试抢锁（可能仍竞争失败）`
- 子分支 2（饥饿模式）：`锁所有权直接交接给我 -> 退出循环（获得锁）`


### 解锁
流程节点（按时间顺序）：
- `Unlock()`
- 分支：`是否有人在等？`
- 快路径节点：`清 locked -> 无需唤醒 -> 返回`
- 慢路径节点：`选择唤醒策略（看 starving / woken）`
- 子分支 1（正常模式）：`通常唤醒一个等待者（sema unpark）`
- 子分支 2（饥饿模式）：`更偏向直接交接给队首等待者（减少新来占便宜）`
- 节点：`更新 woken / 交接链状态（避免重复唤醒）`
- 节点：`等待者被 unpark 后 -> 回到 Lock() 继续尝试抢锁`

### sema
建议画一张“sema 的语义图”，把 `sema` 理解成“许可计数器 + 等待入口”，并画出 acquire/park 与 release/unpark 的对应关系。

节点清单：
- `m.sema (uint32)`
- `runtime_SemacquireMutex(&m.sema)`
- 分支：`能否获得许可？`
- 节点：`能 -> 继续执行（不 park）`
- 节点：`不能 -> park（挂起 goroutine）`
- 节点：`加入等待队列（用 &m.sema 作为标识）`
- `runtime_Semrelease(&m.sema, handoff, ...)`
- 节点：`释放/唤醒等待队列中的一个 goroutine（unpark）`
- 节点：`被唤醒后回到 Lock() 的后续流程（仍可能竞争失败）`

---

## 已生成的图稿（Obsidian 中打开对应 `.md` → 切 Excalidraw 视图）

| 清单小节 | 文件路径 |
|----------|----------|
| sync.Mutex + state 四格 | [`excalidraw/sync.Mutex.1md.概览与state.md`](sync.Mutex.概览与state.md) |
| 加锁 | [`excalidraw/sync.Mutex.1md.Lock流程.md`](sync.Mutex.Lock流程.md) |
| 解锁 | [`excalidraw/sync.Mutex.1md.Unlock流程.md`](sync.Mutex.Unlock流程.md) |
| sema | [`excalidraw/sync.Mutex.1md.sema语义.md`](sync.Mutex.sema语义.md) |

以上四份与本文 `## 1.md` 各小节一一对应；若改文案，可改正文 `1.md` 后再按需微调图内文字。