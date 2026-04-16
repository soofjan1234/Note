import json
import os
import random
from dataclasses import dataclass


OUT_DIR = r"D:\Note\Article\其它\网络\Excalidraw\3"


@dataclass
class DiagramSpec:
    filename: str
    title: str
    lanes: list[str]
    steps: list[str]
    footer: str


def rid(n: int = 8) -> str:
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(random.choice(chars) for _ in range(n))


def base_element(t: str, x: float, y: float, w: float, h: float, stroke="#1e40af", bg="transparent"):
    return {
        "id": rid(),
        "type": t,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "angle": 0,
        "strokeColor": stroke,
        "backgroundColor": bg,
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "roundness": {"type": 3} if t == "rectangle" else None,
        "seed": random.randint(1, 2_000_000_000),
        "version": 1,
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
    }


def text_element(x: float, y: float, text: str, size: int = 18, color="#374151"):
    h = max(24, int(size * 1.25 * (text.count("\n") + 1)))
    w = max(80, int(max(len(line) for line in text.split("\n")) * size * 0.95))
    d = base_element("text", x, y, w, h, stroke=color, bg="transparent")
    d.update(
        {
            "text": text,
            "fontSize": size,
            "fontFamily": 5,
            "textAlign": "left",
            "verticalAlign": "top",
            "containerId": None,
            "originalText": text,
            "autoResize": True,
            "lineHeight": 1.25,
        }
    )
    return d


def line_arrow(x1: float, y1: float, x2: float, y2: float, color="#3b82f6"):
    d = base_element("arrow", x1, y1, abs(x2 - x1) or 1, abs(y2 - y1) or 1, stroke=color, bg="transparent")
    d.update(
        {
            "points": [[0, 0], [x2 - x1, y2 - y1]],
            "lastCommittedPoint": [x2 - x1, y2 - y1],
            "startArrowhead": None,
            "endArrowhead": "arrow",
        }
    )
    return d


def build_diagram(spec: DiagramSpec):
    elements = []
    elements.append(text_element(320, 30, spec.title, 26, "#1e40af"))
    elements.append(base_element("rectangle", 40, 70, 1120, 670, stroke="#cbd5e1", bg="#f8fafc"))

    lane_y = 110
    for i, lane in enumerate(spec.lanes):
        x = 80 + i * (1000 / max(1, len(spec.lanes) - 1))
        elements.append(base_element("rectangle", x - 70, lane_y, 140, 42, stroke="#1e40af", bg="#a5d8ff"))
        elements.append(text_element(x - 50, lane_y + 10, lane, 18, "#1e40af"))

    step_y = 200
    for i, step in enumerate(spec.steps):
        box = base_element("rectangle", 110 + (i % 2) * 540, step_y, 460, 72, stroke="#3b82f6", bg="#e7f5ff")
        elements.append(box)
        elements.append(text_element(box["x"] + 16, box["y"] + 20, step, 16))
        if i > 0:
            prev_y = 200 + (i - 1) * 94 + 72
            elements.append(line_arrow(340, prev_y, 340, step_y, "#3b82f6"))
        step_y += 94

    elements.append(base_element("rectangle", 110, 700, 1000, 32, stroke="#f59e0b", bg="#fff3bf"))
    elements.append(text_element(130, 707, spec.footer, 16, "#92400e"))

    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin",
        "elements": elements,
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    }


def to_markdown(diagram: dict):
    return f"""---
excalidraw-plugin: parsed
tags: [excalidraw]
---
==⚠  Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠== You can decompress Drawing data with the command palette: 'Decompress current Excalidraw file'. For more info check in plugin settings under 'Saving'

# Excalidraw Data

## Text Elements
%%
## Drawing
```json
{json.dumps(diagram, ensure_ascii=False, indent=2)}
```
%%
"""


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    specs = [
        DiagramSpec("3.1-TCP三次握手报文与状态.md", "TCP 三次握手：报文 + 状态", ["客户端", "服务器"], ["① SYN: SYN=1, seq=x；客户端 SYN_SENT", "② SYN+ACK: ack=x+1, seq=y；服务器 SYN_RCVD", "③ ACK: ack=y+1；双方 ESTABLISHED"], "同步初始序号 ISN；第三次握手可携带数据"),
        DiagramSpec("3.1-TCP四次挥手与半关闭.md", "TCP 四次挥手：半关闭 + 状态", ["客户端", "服务器"], ["① FIN: 客户端 FIN_WAIT_1", "② ACK: 服务器 CLOSE_WAIT；客户端 FIN_WAIT_2", "③ FIN: 服务器 LAST_ACK", "④ ACK: 客户端 TIME_WAIT；服务器 CLOSED"], "全双工连接断开需要四步；CLOSE_WAIT 期间可继续发送尾部数据"),
        DiagramSpec("3.1-四次挥手ACK丢失与时序分支.md", "四次挥手异常：ACK 丢失与时序分支", ["客户端", "服务器"], ["场景一: ACK 丢失 -> 客户端 RTO 重传 FIN", "场景二: FIN_WAIT_2 收到 FIN -> ACK -> TIME_WAIT", "场景三: 同时关闭 -> CLOSING -> TIME_WAIT"], "ACK 丢失与同时关闭是两类不同时序"),
        DiagramSpec("3.2-TCP可靠性机制总览.md", "TCP 可靠性机制总览", ["编号 seq", "累积 ACK", "去重/校验", "重传", "流量控制 rwnd", "拥塞控制 cwnd"], ["可靠传输 = 发现丢乱 + 触发补发", "重传路径: RTO 兜底 + dupACK 快速重传", "发送有效窗口受 rwnd 与 cwnd 双重约束"], "先发现问题，再补偿问题，最后控制发送速率"),
        DiagramSpec("3.2-RTO与ARQ重传路径.md", "RTO + ARQ 重传路径", ["发送方", "接收方"], ["主路径: 发送数据 -> 接收 ACK", "异常节点: 数据段或 ACK 丢失", "超时分支: RTO 到期 -> 重传", "快速分支: dupACK -> 快速重传"], "RTO 是兜底，快速重传是提速；TCP 是 ARQ 工程化实现"),
        DiagramSpec("3.2-流量控制rwnd与发送窗口.md", "流量控制：rwnd 与发送窗口", ["接收方", "发送方"], ["接收方在 ACK 中通告 rwnd", "发送方维护 SND.UNA / SND.NXT / SND.WND", "已发未确认 与 可发未发 两段区域", "rwnd=0 时进入零窗口探测"], "发送上限约等于 rwnd；完整形式为 min(rwnd, cwnd)"),
        DiagramSpec("3.2-拥塞控制慢启动到快速恢复.md", "拥塞控制四阶段", ["慢启动", "拥塞避免", "快速重传", "快速恢复"], ["① cwnd 近似指数增长", "② 超过 ssthresh 后线性增长", "③ 3 个 dupACK 触发快速重传", "④ 减速但不停摆，进入恢复/避免"], "dupACK 与 RTO 都是拥塞信号，RTO 通常更激烈"),
        DiagramSpec("3.3-UDP与TCP头部与语义对比.md", "UDP 与 TCP：头部与语义对比", ["UDP", "TCP"], ["UDP 8 字节头: 源端口/目的端口/长度/校验和", "TCP 头更复杂: 序号/确认/窗口/标志位/选项", "UDP: 无连接、尽力交付、不保证顺序", "TCP: 面向连接、可靠字节流"], "若要求可靠但选 UDP，需要应用层补机制"),
        DiagramSpec("3.3-QUIC在UDP之上叠栈.md", "QUIC 叠栈：UDP 只是底座", ["HTTP/3", "QUIC", "UDP", "IP"], ["应用层: HTTP/3 语义", "QUIC 层: 流/可靠/拥塞/握手", "UDP 层: 报文承载与端口复用", "IP 层: 路由转发"], "QUIC 在用户态迭代，绕开内核 TCP 演进慢的问题"),
        DiagramSpec("3.3-QUIC对TCP加TLS痛点四卡.md", "QUIC 对 TCP+TLS 痛点四卡", ["建连", "迁移", "HOL 阻塞", "默认加密"], ["建连: 合并握手，首包更快", "迁移: Connection ID，切网少断", "阻塞: 多 Stream，单流卡顿不连坐", "安全: TLS 1.3 深度集成"], "0-RTT 存在重放风险，更适合幂等请求"),
    ]

    for spec in specs:
        diagram = build_diagram(spec)
        text = to_markdown(diagram)
        with open(os.path.join(OUT_DIR, spec.filename), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(f"generated: {spec.filename}")


if __name__ == "__main__":
    main()
