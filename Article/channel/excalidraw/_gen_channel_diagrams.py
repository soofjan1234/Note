# -*- coding: utf-8 -*-
"""Regenerate channel.*.md Excalidraw JSON. Run: python _gen_channel_diagrams.py"""
import json
import random

random.seed(42)


def nid():
    return "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=10))


def rect(x, y, w, h, bg, stroke, text, fs=16):
    rid_ = nid()
    return [
        {
            "id": rid_,
            "type": "rectangle",
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
            "seed": random.randint(1, 999999999),
            "version": 1,
            "isDeleted": False,
            "boundElements": None,
            "updated": 1,
            "link": None,
            "locked": False,
        },
        {
            "id": nid(),
            "type": "text",
            "x": x + 10,
            "y": y + 6,
            "width": w - 20,
            "height": h - 12,
            "angle": 0,
            "strokeColor": "#374151",
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 1,
            "strokeStyle": "solid",
            "roughness": 1,
            "opacity": 100,
            "groupIds": [],
            "roundness": None,
            "seed": random.randint(1, 999999999),
            "version": 1,
            "isDeleted": False,
            "boundElements": None,
            "updated": 1,
            "link": None,
            "locked": False,
            "text": text,
            "fontSize": fs,
            "fontFamily": 5,
            "textAlign": "center",
            "verticalAlign": "middle",
            "containerId": None,
            "originalText": text,
            "lineHeight": 1.25,
            "autoResize": True,
        },
    ]


def arrow_el(x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    return {
        "id": nid(),
        "type": "arrow",
        "x": x1,
        "y": y1,
        "width": dx,
        "height": dy,
        "angle": 0,
        "strokeColor": "#3b82f6",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "roundness": {"type": 2},
        "seed": random.randint(1, 999999999),
        "version": 1,
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
        "points": [[0, 0], [dx, dy]],
        "lastCommittedPoint": None,
        "startBinding": None,
        "endBinding": None,
        "startArrowhead": None,
        "endArrowhead": "arrow",
    }


def mind_map():
    els = []
    cx, cy, cw, ch = 420, 340, 300, 80
    els += rect(
        cx,
        cy,
        cw,
        ch,
        "#a5d8ff",
        "#1e40af",
        "Go channel 什么时候会被用到",
        20,
    )
    branches = [
        (420, 40, 300, 88, "#b2f2bb", "#15803d", "数据传递\n两个协程之间传数据"),
        (40, 180, 280, 88, "#c3fae8", "#0f766e", "事件通知\n等待某个任务完成"),
        (40, 400, 280, 100, "#d0bfff", "#5b21b6", "生产者与消费者\n持续进行，速度可能不同"),
        (40, 600, 280, 64, "#ffd8a8", "#c2410c", "限制并发数"),
        (880, 180, 300, 88, "#fff3bf", "#a16207", "多路复用与超时控制"),
        (
            860,
            400,
            340,
            120,
            "#ffc9c9",
            "#b91c1c",
            "任务取消\n关闭一个 channel，把取消通知\n广播给多个正在工作的 goroutine",
        ),
    ]
    centers = []
    for bx, by, bw, bh, bg, st, txt in branches:
        els += rect(bx, by, bw, bh, bg, st, txt, 16)
        centers.append((bx + bw / 2, by + bh / 2))
    tcx, tcy = cx + cw / 2, cy + ch / 2
    for bx_c, by_c in centers:
        els.append(arrow_el(tcx, tcy, bx_c, by_c))
    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin",
        "elements": els,
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    }


def common_cases():
    els = []

    def title(x, y, text):
        els.extend(rect(x, y, 340, 44, "#dbe4ff", "#1e40af", text, 20))

    title(40, 30, "阻塞")
    els += rect(
        40,
        90,
        360,
        100,
        "#c3fae8",
        "#0f766e",
        "nil channel 上发送或接收\n且无 select+default\n则进入阻塞流程",
        17,
    )
    els += rect(
        40,
        210,
        360,
        120,
        "#a5d8ff",
        "#1e40af",
        "发送阻塞：通道未关闭\n无 recvq 等待者\n且无缓冲空位\n无缓冲等价于没人接收\n有缓冲则 buf 已满",
        16,
    )
    els += rect(
        40,
        350,
        360,
        100,
        "#b2f2bb",
        "#15803d",
        "接收阻塞：sendq 为空\n且 buf 无数据",
        17,
    )

    title(440, 30, "panic")
    els += rect(
        440,
        90,
        360,
        110,
        "#ffc9c9",
        "#b91c1c",
        "向已关闭通道发送\n加锁后发现已关闭\npanic\nsend on closed channel\n不走等待队列",
        16,
    )
    els += rect(
        440,
        220,
        360,
        90,
        "#ffd8a8",
        "#c2410c",
        "关闭 nil channel\n或重复关闭已关闭通道\n也会 panic",
        17,
    )

    title(840, 30, "调度")
    els += rect(
        840,
        90,
        360,
        130,
        "#d0bfff",
        "#5b21b6",
        "nil 且需阻塞：gopark\n交给 recvq 接收者：\nsend 中对接收方 goready\n发不出/接不到：入队后 gopark",
        16,
    )
    els += rect(
        840,
        240,
        360,
        100,
        "#fff3bf",
        "#a16207",
        "close：锁内收集\nrecvq 与 sendq 上挂着的 G\n解锁后逐个 goready",
        17,
    )

    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin",
        "elements": els,
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    }


def write_md(path, drawing_json):
    body = f"""---
excalidraw-plugin: parsed
tags: [excalidraw]
---
==⚠  Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠== You can decompress Drawing data with the command palette: 'Decompress current Excalidraw file'. For more info check in plugin settings under 'Saving'

# Excalidraw Data

## Text Elements
%%
## Drawing
```json
{drawing_json}
```
%%
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)


def main():
    base = r"d:\Note\Article\channel\excalidraw"
    write_md(
        f"{base}\\channel.什么时候会被用到.md",
        json.dumps(mind_map(), ensure_ascii=False, indent=2),
    )
    write_md(
        f"{base}\\channel.常见情况.md",
        json.dumps(common_cases(), ensure_ascii=False, indent=2),
    )
    print("ok")


if __name__ == "__main__":
    main()
