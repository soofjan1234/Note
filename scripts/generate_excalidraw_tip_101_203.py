import json
import os
import random


OUT_DIR = r"D:\Note\Article\其它\网络\Excalidraw\3"


def rid(n: int = 8) -> str:
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(random.choice(chars) for _ in range(n))


def base_element(t: str, x: float, y: float, w: float, h: float, stroke="#1e40af", bg="transparent", style="solid"):
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
        "strokeStyle": style,
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
    safe = text.replace('"', "『").replace("(", "「").replace(")", "」")
    lines = safe.split("\n")
    h = max(24, int(size * 1.25 * len(lines)))
    w = max(80, int(max(len(line) for line in lines) * size * 0.95))
    d = base_element("text", x, y, w, h, stroke=color, bg="transparent")
    d.update(
        {
            "text": safe,
            "fontSize": size,
            "fontFamily": 5,
            "textAlign": "left",
            "verticalAlign": "top",
            "containerId": None,
            "originalText": safe,
            "autoResize": True,
            "lineHeight": 1.25,
        }
    )
    return d


def line_arrow(x1: float, y1: float, x2: float, y2: float, color="#3b82f6", style="solid"):
    d = base_element("arrow", x1, y1, max(1, abs(x2 - x1)), max(1, abs(y2 - y1)), stroke=color, bg="transparent", style=style)
    d.update(
        {
            "points": [[0, 0], [x2 - x1, y2 - y1]],
            "lastCommittedPoint": [x2 - x1, y2 - y1],
            "startArrowhead": None,
            "endArrowhead": "arrow",
        }
    )
    return d


def poly_arrow(x: float, y: float, points: list[list[float]], color="#3b82f6", style="solid"):
    end = points[-1]
    d = base_element("arrow", x, y, max(1, abs(end[0])), max(1, abs(end[1])), stroke=color, bg="transparent", style=style)
    d.update(
        {
            "points": points,
            "lastCommittedPoint": end,
            "startArrowhead": None,
            "endArrowhead": "arrow",
        }
    )
    return d


def wrap(title: str, elements: list[dict]) -> dict:
    elements.insert(0, text_element(80, 28, title, 24, "#1e40af"))
    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin",
        "elements": elements,
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    }


def build_rto_arq():
    e = []
    e.append(base_element("rectangle", 40, 80, 1120, 680, stroke="#94a3b8", bg="#f8fafc"))
    e.append(base_element("rectangle", 120, 140, 360, 540, stroke="#1e40af", bg="#dbeafe"))
    e.append(base_element("rectangle", 720, 140, 360, 540, stroke="#1e40af", bg="#dbeafe"))
    e.append(text_element(235, 150, "发送方", 20, "#1e40af"))
    e.append(text_element(835, 150, "接收方", 20, "#1e40af"))
    e.append(line_arrow(600, 170, 600, 650, "#64748b", "dashed"))
    e.append(text_element(545, 655, "时间", 16, "#64748b"))

    e.append(base_element("rectangle", 220, 220, 220, 60, stroke="#1e40af", bg="#a5d8ff"))
    e.append(text_element(248, 239, "发送数据段", 16))
    e.append(poly_arrow(440, 250, [[0, 0], [220, 0]], "#3b82f6"))
    e.append(base_element("rectangle", 760, 220, 220, 60, stroke="#1e40af", bg="#a5d8ff"))
    e.append(text_element(790, 239, "回 ACK", 16))
    e.append(poly_arrow(760, 280, [[0, 0], [-220, 0]], "#3b82f6"))

    e.append(base_element("diamond", 520, 330, 160, 100, stroke="#b91c1c", bg="#ffc9c9"))
    e.append(text_element(548, 365, "数据段或\nACK 丢失", 16, "#991b1b"))

    e.append(base_element("rectangle", 130, 470, 360, 80, stroke="#c2410c", bg="#ffd8a8"))
    e.append(text_element(150, 495, "超时分支：RTO 到期 -> 重传 -> 去重 ACK", 16, "#9a3412"))
    e.append(poly_arrow(540, 420, [[0, 0], [-140, 0], [-140, 50]], "#c2410c"))

    e.append(base_element("rectangle", 710, 470, 360, 80, stroke="#15803d", bg="#b2f2bb"))
    e.append(text_element(732, 495, "快速分支：dupACK -> 快速重传「不等 RTO」", 16, "#166534"))
    e.append(poly_arrow(680, 420, [[0, 0], [160, 0], [160, 50]], "#15803d"))

    card_x = [120, 420, 720]
    card_text = ["停等 ARQ\n低效", "GBN\n回退重发", "SR\n精准重传"]
    for i in range(3):
        e.append(base_element("rectangle", card_x[i], 590, 240, 86, stroke="#7c3aed", bg="#d0bfff"))
        e.append(text_element(card_x[i] + 84, 615, card_text[i], 16, "#5b21b6"))

    e.append(base_element("rectangle", 120, 700, 960, 44, stroke="#ca8a04", bg="#fff3bf"))
    e.append(text_element(140, 714, "RTO 是兜底，快速重传是提速；TCP 是 ARQ 的工程化实现", 16, "#854d0e"))
    return wrap("RTO + ARQ 重传路径「双泳道 + 分支」", e)


def build_flow_control():
    e = []
    e.append(base_element("rectangle", 40, 80, 1120, 680, stroke="#94a3b8", bg="#f8fafc"))
    e.append(base_element("rectangle", 120, 120, 360, 180, stroke="#1e40af", bg="#a5d8ff"))
    e.append(text_element(155, 145, "接收方 rwnd", 20, "#1e40af"))
    e.append(text_element(155, 190, "ACK 中窗口通告", 16))
    e.append(base_element("rectangle", 660, 120, 360, 180, stroke="#166534", bg="#b2f2bb"))
    e.append(text_element(745, 145, "发送方", 20, "#166534"))
    e.append(text_element(695, 190, "接收通告后更新发送上限", 16, "#14532d"))
    e.append(line_arrow(480, 205, 660, 205, "#3b82f6"))
    e.append(text_element(525, 175, "ACK: rwnd", 16, "#1d4ed8"))

    e.append(base_element("rectangle", 120, 360, 920, 120, stroke="#1e40af", bg="#eef2ff"))
    e.append(base_element("rectangle", 150, 390, 280, 60, stroke="#1e3a8a", bg="#a5d8ff"))
    e.append(text_element(220, 410, "已发未确认", 16, "#1e3a8a"))
    e.append(base_element("rectangle", 430, 390, 280, 60, stroke="#166534", bg="#b2f2bb"))
    e.append(text_element(505, 410, "可发未发", 16, "#166534"))
    e.append(base_element("rectangle", 710, 390, 300, 60, stroke="#c2410c", bg="#ffd8a8"))
    e.append(text_element(772, 410, "窗口外不可发", 16, "#9a3412"))
    e.append(line_arrow(150, 480, 150, 520, "#334155"))
    e.append(text_element(110, 525, "SND.UNA", 16))
    e.append(line_arrow(430, 480, 430, 520, "#334155"))
    e.append(text_element(392, 525, "SND.NXT", 16))
    e.append(line_arrow(710, 480, 710, 520, "#334155"))
    e.append(text_element(672, 525, "SND.WND", 16))

    e.append(base_element("rectangle", 120, 560, 320, 100, stroke="#9a3412", bg="#ffd8a8"))
    e.append(text_element(145, 590, "rwnd=0 -> 零窗口 -> 探测", 16, "#9a3412"))
    e.append(poly_arrow(440, 610, [[0, 0], [130, 0], [130, -30]], "#9a3412", "dashed"))

    e.append(base_element("rectangle", 500, 560, 540, 100, stroke="#ca8a04", bg="#fff3bf"))
    e.append(text_element(525, 590, "发送上限 ~= rwnd\n完整：有效窗口 = min「rwnd, cwnd」", 16, "#854d0e"))
    return wrap("流量控制 · 发送窗口与接收窗口", e)


def build_congestion_story():
    e = []
    e.append(base_element("rectangle", 40, 80, 1120, 680, stroke="#94a3b8", bg="#f8fafc"))
    cards = [
        ("① 慢启动", "cwnd 近似指数爬升", "#a5d8ff", "#1e3a8a"),
        ("② 拥塞避免", "过 ssthresh 后线性", "#b2f2bb", "#166534"),
        ("③ 快速重传", "3 个 dupACK 触发", "#ffd8a8", "#9a3412"),
        ("④ 快速恢复", "减速继续，不砍最小", "#d0bfff", "#5b21b6"),
    ]
    x = 90
    for i, (t, body, bg, stroke) in enumerate(cards):
        e.append(base_element("rectangle", x, 180, 240, 210, stroke=stroke, bg=bg))
        e.append(text_element(x + 20, 215, t, 20, stroke))
        e.append(text_element(x + 20, 275, body, 16, "#374151"))
        if i < 3:
            e.append(line_arrow(x + 240, 285, x + 270, 285, "#3b82f6"))
        x += 270

    e.append(base_element("rectangle", 120, 450, 450, 120, stroke="#166534", bg="#b2f2bb"))
    e.append(text_element(145, 485, "出口 A：dupACK\n通常进入快速重传/恢复", 16, "#166534"))
    e.append(base_element("rectangle", 640, 450, 450, 120, stroke="#b91c1c", bg="#ffc9c9"))
    e.append(text_element(665, 485, "出口 B：RTO 超时\n通常降得更狠", 16, "#991b1b"))
    e.append(base_element("rectangle", 120, 620, 970, 50, stroke="#ca8a04", bg="#fff3bf"))
    e.append(text_element(410, 635, "有效窗口 = min「rwnd, cwnd」", 18, "#854d0e"))
    return wrap("拥塞控制「四阶段故事板」", e)


def build_udp_tcp_compare():
    e = []
    e.append(base_element("rectangle", 40, 80, 1120, 680, stroke="#94a3b8", bg="#f8fafc"))
    e.append(base_element("rectangle", 90, 150, 430, 470, stroke="#1e3a8a", bg="#a5d8ff"))
    e.append(base_element("rectangle", 680, 150, 430, 470, stroke="#166534", bg="#b2f2bb"))
    e.append(text_element(260, 170, "UDP", 22, "#1e3a8a"))
    e.append(text_element(850, 170, "TCP", 22, "#166534"))
    e.append(base_element("rectangle", 130, 240, 350, 70, stroke="#1e3a8a", bg="#dbeafe"))
    e.append(text_element(155, 267, "8 字节头：源端口·目的端口", 16, "#1e3a8a"))
    e.append(base_element("rectangle", 130, 325, 350, 70, stroke="#1e3a8a", bg="#dbeafe"))
    e.append(text_element(155, 352, "长度 · 校验和", 16, "#1e3a8a"))
    e.append(text_element(145, 445, "无连接\n尽力交付\n不保证顺序", 18, "#1e3a8a"))

    e.append(base_element("rectangle", 720, 240, 350, 70, stroke="#166534", bg="#dcfce7"))
    e.append(text_element(745, 267, "更长头：序号/确认/窗口", 16, "#166534"))
    e.append(base_element("rectangle", 720, 325, 350, 70, stroke="#166534", bg="#dcfce7"))
    e.append(text_element(745, 352, "标志位/选项更多", 16, "#166534"))
    e.append(text_element(735, 445, "面向连接\n可靠字节流", 18, "#166534"))

    e.append(base_element("rectangle", 535, 220, 120, 350, stroke="#7c3aed", bg="#e9d5ff"))
    e.append(text_element(550, 300, "语义对照", 18, "#6d28d9"))
    e.append(line_arrow(520, 300, 480, 300, "#7c3aed"))
    e.append(line_arrow(655, 300, 695, 300, "#7c3aed"))
    e.append(base_element("rectangle", 120, 650, 980, 44, stroke="#ca8a04", bg="#fff3bf"))
    e.append(text_element(275, 665, "可靠若要 UDP 做 = 应用层自己补", 18, "#854d0e"))
    return wrap("UDP「极简头部」+ 与 TCP 对照", e)


def build_quic_stack():
    e = []
    e.append(base_element("rectangle", 40, 80, 1120, 680, stroke="#94a3b8", bg="#f8fafc"))
    stack = [
        ("应用：HTTP/3", "#eebefa", "#9d174d"),
        ("QUIC：流·可靠·拥塞·握手", "#d0bfff", "#5b21b6"),
        ("UDP", "#a5d8ff", "#1e3a8a"),
        ("IP", "#c3fae8", "#0f766e"),
    ]
    y = 180
    for t, bg, sc in stack:
        e.append(base_element("rectangle", 260, y, 500, 95, stroke=sc, bg=bg))
        e.append(text_element(310, y + 35, t, 20, sc))
        y += 120

    e.append(poly_arrow(760, 228, [[0, 0], [180, 0]], "#166534", "dashed"))
    e.append(text_element(790, 205, "把可靠与安全做成一层", 16, "#166534"))
    e.append(poly_arrow(760, 470, [[0, 0], [180, 0]], "#1e3a8a", "dashed"))
    e.append(text_element(790, 445, "UDP 只负责\n把报文送到端口", 16, "#1e3a8a"))
    e.append(base_element("rectangle", 840, 560, 270, 110, stroke="#9a3412", bg="#ffd8a8"))
    e.append(text_element(865, 590, "用户态可迭代\n内核 TCP 难改", 16, "#9a3412"))
    return wrap("QUIC 叠栈「UDP 只是底座」", e)


def build_quic_four_cards():
    e = []
    e.append(base_element("rectangle", 40, 80, 1120, 680, stroke="#94a3b8", bg="#f8fafc"))
    cards = [
        ("建连", "多次 RTT", "合并握手", "首包更快"),
        ("迁移", "四元组绑死", "Connection ID", "切网少断"),
        ("队头阻塞", "单字节流连坐", "多 Stream", "一流卡不拖全局"),
        ("默认加密", "外挂 TLS", "TLS1.3 内建", "默认安全"),
    ]
    x = 70
    for idx, (title, pain, q, result) in enumerate(cards):
        color = ["#a5d8ff", "#b2f2bb", "#ffd8a8", "#d0bfff"][idx]
        stroke = ["#1e3a8a", "#166534", "#9a3412", "#5b21b6"][idx]
        e.append(base_element("rectangle", x, 180, 250, 300, stroke=stroke, bg=color))
        e.append(text_element(x + 88, 205, title, 20, stroke))
        e.append(text_element(x + 20, 260, f"痛点：{pain}", 16, "#374151"))
        e.append(text_element(x + 20, 315, f"QUIC：{q}", 16, stroke))
        e.append(text_element(x + 20, 370, f"结果：{result}", 16, "#374151"))
        x += 270
    e.append(base_element("rectangle", 120, 540, 960, 110, stroke="#ca8a04", bg="#fff3bf"))
    e.append(text_element(150, 570, "统一版式：痛点 -> QUIC -> 结果\n0-RTT 有重放风险，幂等请求更合适", 18, "#854d0e"))
    return wrap("QUIC 解决 TCP+TLS 痛点「四卡对照」", e)


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
    jobs = [
        ("3.2-RTO与ARQ重传路径.md", build_rto_arq),
        ("3.2-流量控制rwnd与发送窗口.md", build_flow_control),
        ("3.2-拥塞控制慢启动到快速恢复.md", build_congestion_story),
        ("3.3-UDP与TCP头部与语义对比.md", build_udp_tcp_compare),
        ("3.3-QUIC在UDP之上叠栈.md", build_quic_stack),
        ("3.3-QUIC对TCP加TLS痛点四卡.md", build_quic_four_cards),
    ]
    for name, builder in jobs:
        text = to_markdown(builder())
        out_path = os.path.join(OUT_DIR, name)
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(f"generated: {out_path}")


if __name__ == "__main__":
    main()
