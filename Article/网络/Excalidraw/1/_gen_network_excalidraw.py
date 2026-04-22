# -*- coding: utf-8 -*-
"""Generate Obsidian Excalidraw parsed JSON for 网络/1 系列图."""
import json
import os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

FF = 5
LH = 1.25


def base_rect(i, x, y, w, h, text, bg, stroke="#1e40af", fs=16):
    return {
        "type": "rectangle",
        "id": i,
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
        "roundness": {"type": 3},
        "seed": hash(i) % 10**9,
        "version": 1,
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
    }


def txt(i, x, y, w, h, text, fs=16, color="#374151", align="center"):
    return {
        "type": "text",
        "id": i,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "angle": 0,
        "strokeColor": color,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "roundness": None,
        "seed": hash(i + "t") % 10**9,
        "version": 1,
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
        "text": text,
        "fontSize": fs,
        "fontFamily": FF,
        "textAlign": align,
        "verticalAlign": "middle",
        "containerId": None,
        "originalText": text,
        "autoResize": True,
        "lineHeight": LH,
    }


def arrow_el(
    i, x, y, points, color="#3b82f6", start_arrow=None, end_arrow="arrow"
):
    w = max(p[0] for p in points) - min(p[0] for p in points)
    h = max(p[1] for p in points) - min(p[1] for p in points)
    if w < 1:
        w = 1
    if h < 1:
        h = 1
    return {
        "type": "arrow",
        "id": i,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "angle": 0,
        "strokeColor": color,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "roundness": None,
        "seed": hash(i + "a") % 10**9,
        "version": 1,
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
        "points": points,
        "startArrowhead": start_arrow,
        "endArrowhead": end_arrow,
    }


def line_dashed(i, x, y, x2, y2, color="#64748b"):
    dx, dy = x2 - x, y2 - y
    return {
        "type": "line",
        "id": i,
        "x": x,
        "y": y,
        "width": abs(dx) or 1,
        "height": abs(dy) or 1,
        "angle": 0,
        "strokeColor": color,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "dashed",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "roundness": None,
        "seed": hash(i + "l") % 10**9,
        "version": 1,
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
        "points": [[0, 0], [dx, dy]],
    }


def wrap_md(name, data):
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
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
{body}
```
%%
"""


def drawing(elements):
    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin",
        "elements": elements,
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    }


def gen1():
    els = []
    # Title
    els.append(txt("t1-title", 200, 28, 800, 36, "OSI 七层 ↔ 五层 ↔ TCP/IP 对照", 22, "#1e40af"))
    col_w, row_h = 200, 58
    x1, x2, x3 = 50, 380, 720
    y0 = 90
    osi = [
        "L7 应用",
        "L6 表示",
        "L5 会话",
        "L4 传输",
        "L3 网络",
        "L2 数据链路",
        "L1 物理",
    ]
    colors = ["#ffc9c9", "#ffd8a8", "#fff3bf", "#d3f9d8", "#a5d8ff", "#d0bfff", "#eebefa"]
    for i, (name, c) in enumerate(zip(osi, colors)):
        y = y0 + i * row_h
        els.append(base_rect(f"osi-{i}", x1, y, col_w, row_h - 6, name, c))
        els.append(txt(f"osi-t-{i}", x1, y + 8, col_w, 36, name, 16, "#374151"))

    w5 = ["应用", "传输", "网络", "数据链路", "物理"]
    c5 = ["#ffc9c9", "#d3f9d8", "#a5d8ff", "#d0bfff", "#eebefa"]
    h5 = [row_h * 3 - 6, row_h - 6, row_h - 6, row_h - 6, row_h - 6]
    y = y0
    for i, (name, c, hh) in enumerate(zip(w5, c5, h5)):
        els.append(base_rect(f"w5-{i}", x2, y, col_w, hh, name, c))
        els.append(txt(f"w5-t-{i}", x2, y + max(8, hh // 2 - 12), col_w, 28, name, 17, "#374151"))
        y += hh + 6

    # TCP/IP 4 layers
    tcp = [
        ("应用", "#ffc9c9", row_h * 3 - 6),
        ("传输", "#d3f9d8", row_h - 6),
        ("网际", "#a5d8ff", row_h - 6),
        ("网络接口\n「物理+链路」", "#d0bfff", row_h * 2 - 6),
    ]
    y = y0
    for i, (name, c, hh) in enumerate(tcp):
        els.append(base_rect(f"tcp-{i}", x3, y, col_w + 40, hh, name, c))
        els.append(
            txt(
                f"tcp-t-{i}",
                x3,
                y + max(8, hh // 2 - 20),
                col_w + 40,
                44,
                name.replace("\n", "\n"),
                16,
                "#374151",
            )
        )
        y += hh + 6

    els.append(txt("leg1", 50, 520, 1050, 24, "左：OSI 七层「上到下」  中：五层「会话/表示/应用合并为应用」  右：TCP/IP 四层", 15, "#64748b"))
    return drawing(els)


def gen2():
    els = []
    els.append(txt("t2", 280, 24, 640, 32, "五层协议栈与代表协议「自下而上」", 22, "#1e40af"))
    layers = [
        ("物理层", "网线 / 光纤 / Wi‑Fi", "#eebefa"),
        ("数据链路层", "以太网、ARP", "#d0bfff"),
        ("网络层", "IPv4/v6、ICMP", "#a5d8ff"),
        ("传输层", "TCP、UDP「端口」", "#d3f9d8"),
        ("应用层", "HTTP、DNS、SSH…", "#ffc9c9"),
    ]
    bx, bw, bh = 380, 300, 72
    y = 480
    for i, (title, sub, bg) in enumerate(layers):
        els.append(base_rect(f"L{i}", bx, y, bw, bh, title, bg))
        els.append(txt(f"Lt{i}", bx + 10, y + 10, bw - 20, 28, title, 18, "#1e40af", "left"))
        els.append(txt(f"Ls{i}", bx + 10, y + 38, bw - 20, 28, sub, 16, "#374151", "left"))
        y -= bh + 8

    els.append(
        txt(
            "note2",
            80,
            560,
            1040,
            48,
            "Wireshark 展开顺序常类似：Frame「链路」→ IP → TCP/UDP → 应用层载荷",
            16,
            "#64748b",
            "left",
        )
    )
    return drawing(els)


def gen3():
    els = []
    els.append(txt("t3", 320, 36, 560, 32, "封装与各层 PDU「套娃」", 22, "#1e40af"))
    cx, cy = 500, 330
    # 从外到内绘制，数组后者在上层；先画大框再画小框，保证内层在上
    layers_out_to_in = [
        ("比特流「物理」", 340, "#f3f4f6"),
        ("以太网帧「链路」", 280, "#d0bfff"),
        ("IP 数据报「分组」", 220, "#a5d8ff"),
        ("TCP 段 / UDP 报文", 150, "#d3f9d8"),
        ("应用数据", 80, "#ffc9c9"),
    ]
    for i, (label, size, bg) in enumerate(layers_out_to_in):
        x = cx - size / 2
        y = cy - size / 2
        els.append(base_rect(f"box{i}", x, y, size, size, label, bg, "#1e40af"))
        fs = 15 if len(label) < 14 else 13
        els.append(
            txt(
                f"boxt{i}",
                x + 10,
                y + size / 2 - 16,
                size - 20,
                36,
                label,
                fs,
                "#374151",
            )
        )

    els.append(arrow_el("a1", 860, 220, [[0, 0], [0, 100]], "#3b82f6"))
    els.append(txt("ad1", 875, 238, 180, 72, "发送端\n向下封装", 16, "#1e40af", "left"))
    els.append(arrow_el("a2", 860, 400, [[0, 100], [0, 0]], "#10b981"))
    els.append(txt("ad2", 875, 418, 180, 72, "接收端\n向上解封装", 16, "#15803d", "left"))
    return drawing(els)


def gen4():
    els = []
    els.append(txt("t4", 260, 20, 680, 32, "逐跳「二层 MAC」与端到端「IP / TCP」", 20, "#1e40af"))
    # devices
    devs = [(80, 280, "主机 A"), (300, 280, "路由器 R1"), (520, 280, "路由器 R2"), (740, 280, "主机 B")]
    for i, (x, y, lab) in enumerate(devs):
        els.append(base_rect(f"d{i}", x, y, 120, 64, lab, "#dbeafe" if i in (0, 3) else "#fff3bf"))
        els.append(txt(f"dt{i}", x, y + 18, 120, 28, lab, 16, "#374151"))

    # links
    for i, x in enumerate([200, 420, 640]):
        els.append(line_dashed(f"lnk{i}", x, 312, x + 100, 312, "#64748b"))
        els.append(
            txt(
                f"mac{i}",
                x + 15,
                318,
                90,
                40,
                "MAC\n每跳重写",
                14,
                "#b45309",
                "center",
            )
        )

    # IP band
    els.append(
        base_rect("ipband", 100, 200, 840, 48, "", "#a5d8ff", "#1e40af")
    )
    els[-1]["opacity"] = 45
    els.append(
        txt(
            "ipt",
            120,
            212,
            800,
            28,
            "IP：源 IP / 目的 IP 通常不变「无 NAT 时」",
            17,
            "#1e40af",
            "center",
        )
    )

    # TCP 端到端箭头
    els.append(arrow_el("tcpa1", 140, 140, [[0, 0], [660, 0]], "#15803d"))
    els[-1]["strokeStyle"] = "solid"
    els.append(
        txt(
            "tcpt",
            280,
            108,
            560,
            28,
            "TCP：端口与连接端到端，中间路由器不参与握手「除非防火墙/NAT」",
            16,
            "#15803d",
            "center",
        )
    )

    els.append(
        txt(
            "leg4",
            60,
            400,
            1080,
            80,
            "图例：橙色标注 = 二层逐跳  蓝色条带 = 三层端到端寻址  绿色 = 四层端到端连接语义",
            15,
            "#64748b",
            "left",
        )
    )
    return drawing(els)


def main():
    gens = [
        ("1-OSI-五层-TCP对照.md", gen1),
        ("1-五层协议栈与代表协议.md", gen2),
        ("1-封装与PDU套娃.md", gen3),
        ("1-逐跳与端到端-MAC-IP-TCP.md", gen4),
    ]
    for fname, fn in gens:
        path = os.path.join(OUT_DIR, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(wrap_md(fname, fn()))
        print("wrote", path)


if __name__ == "__main__":
    main()
