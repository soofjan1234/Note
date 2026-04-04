# select 配图提示词（严格依据 select.md / select源码.md）

已生成图稿（Obsidian Excalidraw）：Article/go关键字/Excalidraw/selectgo.主路径.md（同目录另有 selectgo.主路径.json 便于脚本复用）。用插件打开该 md 切换 Excalidraw 视图即可编辑。

---

以下整段为一张图的提示词，可直接交给绘图 AI。内容须与 select.md、select源码.md 一致，不得编造未出现的运行时细节。

---

推荐图表类型：单张流程图（自上而下，含少量决策菱形与侧栏注释）。

版式与风格：参考画图skill。画布约 1200×800，四周留白不少于 50px；浅色填充矩形区分步骤（浅蓝起始、浅绿结束、浅黄决策、浅紫中间步骤）；描边用同色系深色；正文标签不小于 16px；不要使用 Emoji。

---

提示词（单图：selectgo 全路径）

> 画一张中文流程图，一张图内包含主链与两处侧注，标题置顶居中：「select 运行时 selectgo 主路径」。
>
> 主链自上而下：
> 1）准备：得到各 case 描述 scases；在栈上缓冲区里生成 pollorder（随机插入，减轻饥饿）与 lockorder（按 channel 地址排序，用于全序加锁防死锁）。
> 2）sellock：按 lockorder 依次锁住本次涉及的 channel。防止状态被改变
> 3）pass1：按 pollorder 轮询尝试快路径——接收侧优先「与对端交接、再读缓冲、再判关闭」；发送侧先判关闭再「与对端交接、再写缓冲」；若任一 case 能立刻完成则 selunlock、返回（角落小字注：recvOK 仅对接收 case 有意义）。
> 4）菱形决策：若存在 default 且 pass1 无人能执行 → selunlock，返回下标负一表示走 default → 结束。
> 5）若无 default 且 pass1 无人能执行：多路各挂等待项、入队，gopark 睡眠（旁注：休眠前 selparkcommit 释放 channel 锁）。
> 6）被唤醒后：再次 sellock；从唤醒者给出的信息识别中奖的那一路；沿 lockorder 摘掉其余路上的等待项；selunlock、返回。
>
> 主图左侧或底部用窄条两格注释放不下主链的概念（不必单独成图）：一格写「pollorder：打乱本轮检查顺序」；一格写「lockorder：按地址加锁顺序」；底注一句「二者分工不同」。
>
> 不要画函数签名或完整代码；源码级标识如 sudog、gp.param 可改为「等待项」「中奖信息」等口语。

---

自检（交付前）：成图后核对是否仅表达上述文档中已有语义；若绘图 AI 擅自加入未约定的包名、函数列表或与其它语言混淆的语法，应删改提示词后重画。
