# 日志 配图提示词

遵照 excalidraw-diagram skill。以下用于 `Article/MySQL/new/日志/`，与 `6.1-Redo Log与崩溃恢复.md`、`6.2-Undo Log与Purge机制.md`、`6.3-Binlog.md`、`6.4-核心串联：一条更新语句的完整流程.md` 配套；偏流程与对照，少画源码级字段。

**通用设计规范（出图时遵守 Skill）**：

- **字体**：`fontFamily: 5`；正文最小 `16px`。
- **颜色**：遵循 Skill 色板，描边用填充色深色同系。
- **禁止**：不要使用 Emoji。

---

## 6.1 Redo Log 与崩溃恢复

### 1. 环形日志与双指针（示意图 / 对比图）

- **图类型**：横向「跑道」或长条矩形表示一组 `ib_logfile`，头尾箭头表示**循环覆盖**。
- **元素**：**Write Pos**（写指针，靠前）、**Checkpoint**（检查点，靠后或未覆盖段边界）；中间可用浅色表示「可覆盖 / 待落盘」两段，旁注「Checkpoint 前：页已落盘，日志可重用」。
- **图注**：Write Pos 追上 Checkpoint 时要刷脏、推进检查点，否则阻塞。

### 2. WAL：随机写页 vs 顺序写 Redo（对比图）

- **图类型**：左右对比。
- **左**：多个散点「数据页」+ 曲折箭头，标注「随机 I/O」。
- **右**：单一磁带式长条「Redo 文件」+ 单向箭头追加，标注「顺序 I/O」。
- **中间或底栏**：一句「先写 Redo，页异步刷」。

### 3. Redo 内存到磁盘（流程图）

- **路径**：`Buffer Pool 脏页` →（旁注「变更产生」）→ `Redo Log Buffer` → `ib_logfile`。
- **旁挂小框**：`innodb_flush_log_at_trx_commit` 三档 `0 / 1 / 2`（各一行：提交是否 fsync、风险与性能），不要写太长。

### 4. LSN 与崩溃恢复（关系图 / 小流程图）

- **三个节点**：`日志 LSN 推进`、`Checkpoint LSN`、`FIL_PAGE_LSN（页头）`。
- **箭头**：恢复起点「从 Checkpoint 往后扫」；页「若页 LSN < 应到达的日志 → 对该页 Redo」。
- **浅黄旁注**：页物理损坏时 Redo 无法单独修复，需 Doublewrite / 备份（点到为止）。

---

## 6.2 Undo Log 与 Purge 机制

### 1. Insert Undo vs Update/Delete Undo（对比图）

- **图类型**：左右两栏卡片。
- **左 Insert**：小体积、提交后可快速回收；关键词「定位新行、回滚删行」。
- **右 Update/Delete**：带 before image、MVCC；关键词「提交后仍可能保留、等 Purge」。


### 3. History List 与 Purge（流程图 / 链式图）

- **水平链表**：左「头（最老）」右「尾」；**COMMIT** 箭头指向「挂尾」；**Purge** 小人/线程从**头**向尾扫。
- **分支**：遇到「仍被 ReadView 需要」→ 旁注「暂停 / 不可删」；否则「回收 Undo 页」。
- **第二轨（可选）**：`Delete Mark` 行 → Purge 真正从 B+ 树摘掉，与「回收 Undo」并列两条职责。

---

## 6.3 Binlog

### 1. `binlog_format` 三模式（对比图）

- **图类型**：三列卡片。
- **STATEMENT**：SQL 文本；旁注「省空间 / 函数主从不一致风险」。
- **ROW**：行前/后镜像；旁注「体积大 / 重放稳」。
- **MIXED**：Server 择优切换；旁注「折中」。

### 2. 层级与三种日志分工（层级图）

- **上层**：`MySQL Server` 框内 **Binlog**（复制、PITR、审计）。
- **下层**：`InnoDB` 框内 **Redo**（崩溃恢复）、**Undo**（回滚、MVCC）。
- **虚线**：`2PC` 连接 Redo 与 Binlog，标注「提交时对齐」。

### 3. Redo vs Binlog 对照（对比图）

- **图类型**：与正文表格同维度的双列表格化呈现（层级、用途、内容形态、写入方式、循环 vs 追加），用色块区分两列，避免文字过密可拆成上下两半张图。

---

## 6.4 核心串联：一条更新语句的完整流程

### 1. UPDATE 执行到提交（泳道 / 时间线图）

- **图类型**：自上而下或从左到右流程图。
- **步骤串联**：`Buffer Pool 改脏页` → `写 Undo` → `Redo Log Buffer` →（Prepare：`Redo 刷盘 + prepare 标记`）→ `写 Binlog 刷盘` → `Redo commit`。
- **旁注**：数据文件 `.ibd` 此阶段仍可旧，符合 WAL。

### 2. 崩溃恢复与 prepare（流程图）

- **入口**：Redo 见某事务 `prepare`。
- **菱形**：Binlog 是否有对应完整记录？
  - **是** → 补成 commit。
  - **否** → 回滚。
- **图注**：防止 InnoDB 与 Binlog 单边落地。

---

