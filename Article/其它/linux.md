# Linux 常考题

## 1. 知道项目名，怎么查端口？

| 工具 | 核心用途 | 优点 | 缺点 |
| --- | --- | --- | --- |
| `ps -ef` | 看进程详情 | 能看到完整启动路径和参数 | 结果杂乱，常包含 `grep` 自身 |
| `pgrep` | 拿进程 PID | 结果简洁，适合脚本调用 | 看不到详细启动参数 |
| `netstat` | 看网络端口 | 普及率高，老系统常见 | 性能较差，新系统可能缺失 |
| `ss` | 看网络详情 | 性能更好，信息更底层 | 部分老旧系统可能没装 |

## 2. `kill`、`pkill -f`、`kill -9` 区别？
- `kill PID`：按 PID 发信号，默认 `SIGTERM`（可清理退出）。
- `pkill -f pattern`：按完整命令行匹配，可能匹配多个进程。
- `-9`：`SIGKILL`，强制终止，不可捕获，最后手段。

## 3. 脚本第一行（shebang）作用？
告诉系统用哪个解释器执行脚本。

```bash
#!/bin/bash
#!/usr/bin/env bash
```

前者路径固定，后者更便携（从 `PATH` 找 bash）。

## 4. Linux 权限 `rwx` 和 `755` 是什么？
- 权限位：`r` 读，`w` 写，`x` 执行。
- 三组身份：所有者 / 所属组 / 其他人。
- `755 = rwx r-x r-x`，`644 = rw- r-- r--`。

## 5. `chmod`、`chown` 区别？
- `chmod`：改权限位。
- `chown`：改文件所有者和组。

```bash
chmod 755 app.sh
chown user:group file.txt
```

## 6. 如何查看 CPU、内存、磁盘使用？

```bash
top            # 或 htop，实时查看系统的整体负载、CPU 占用、内存消耗以及进程列表
free -h  #  内存使用情况
df -h  #  磁盘使用情况
du -sh *  #  文件和目录的大小
```

## 7. 线程和进程区别？
- 进程：资源分配基本单位，地址空间独立。
- 线程：CPU 调度基本单位，共享进程内存。
- 线程切换开销通常小于进程切换。

## 8. 如何查某端口被谁占用？

```bash
ss -lntp | rg :8080
lsof -i :8080
```

## 9. 查看日志常用命令？

```bash
journalctl -u nginx -f
tail -f /var/log/nginx/access.log
```
