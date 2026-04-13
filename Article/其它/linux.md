## 1. 知道正在运行的项目名字，如何知道端口

思路：**先确认进程名/PID，再查该进程监听了哪些端口**（或反过来用端口反查进程）。

**用 `ss`（推荐，现代发行版常见）**

```bash
# 按名字过滤（进程名在最后一列 user:("name",pid=...)）
sudo ss -tulnp | grep -i 你的项目名或关键字
```

**用 `lsof`**

```bash
sudo lsof -i -P -n | grep -i 进程名或关键字
# 或已知 PID：
sudo lsof -i -P -n -p PID
```

**先 PID 再端口**

```bash
pgrep -a 进程名          # 或 ps aux | grep ...
sudo ss -tulnp | grep pid=12345
```

## 2. `kill`、`pkill -f` 和 `kill -9` 的区别

**先分清两件事**：`kill` / `pkill` 是**怎么选中进程**；`-9` 是**发什么信号**（可和 `kill` 或 `pkill` 组合）。

### `kill`（按 PID）

```bash
kill 1234          # 默认 SIGTERM（15）
kill -9 1234       # SIGKILL（9）
```

- 必须知道 **PID**（`ps`、`pgrep` 等先查）。
- 默认 **SIGTERM（15）**：进程可捕获、做清理后退出；忽略或卡死时可能迟迟不结束。
- **`kill -9`**：发 **SIGKILL**，内核强杀，**不可捕获**；无清理机会，可能半写文件、锁未释放等，**应作为最后手段**。

### `pkill`（按名字/模式匹配）

```bash
pkill nginx                    # 匹配「进程名」含 nginx 的（实现依系统，常等价于 comm）
pkill -f "java -jar app.jar"   # -f：对「整条命令行」做匹配
```

- **不用先查 PID**，按模式结束**一个或多个**进程，写脚本省事。
- **`-f`**：关键字出现在完整启动命令里才算（适合 `java -jar xxx`、`python main.py` 这种）；**没有 `-f`** 时往往只比进程名，容易误杀或杀不到。
- 默认同样发 **SIGTERM**；要强杀可 **`pkill -9 -f '...'`**（同样慎用）。
- 模式写太宽会**误杀**，先用 **`pgrep -f '...'`** 看会命中哪些 PID，再 `pkill`。

### 对照小结

|  | 选中方式 | 默认信号 | 注意 |
| --- | --- | --- | --- |
| `kill PID` | 精确 PID | SIGTERM | 一次一个 PID；可 `kill 1 2 3` |
| `pkill -f 模式` | 命令行子串 | SIGTERM | 可能多进程；先 `pgrep -f` 核对 |
| `kill -9` / `pkill -9` | 同上 | **SIGKILL** | 强杀，最后手段 |

## 3. shell脚本的第一行
第一行一般是：#!/bin/bash或：#!/usr/bin/env bash

作用：告诉系统用哪个解释器执行这个脚本（#! 叫 shebang）。

#!/bin/bash：固定用 /bin/bash。
#!/usr/bin/env bash：在 PATH 里找 bash，换机器时路径更灵活。

注意：shebang 必须是文件第一行，前面不能有空行或 BOM 干扰（有的编辑器会加 UTF-8 BOM，会导致 shebang 失效）。

shebang 是告诉操作系统**「这个文本文件该交给哪个解释器执行」；不写也能在终端里手动 bash foo.sh 跑，但当可执行脚本直接 ./foo.sh 时**，就需要它（或你每次都显式写解释器）