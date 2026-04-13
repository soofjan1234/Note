import json
from pathlib import Path


BASE = Path(r"d:\Note\Article\Go\内存管理\excalidraw")


def _common(element_id, kind, x, y, w, h, stroke="#1e40af", fill="#a5d8ff"):
    return {
        "id": element_id,
        "type": kind,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "angle": 0,
        "strokeColor": stroke,
        "backgroundColor": fill,
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "roundness": {"type": 3},
        "seed": abs(hash(element_id)) % 1_000_000_000,
        "version": 1,
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
    }


def rect(element_id, x, y, w, h, fill="#a5d8ff", stroke="#1e40af"):
    return _common(element_id, "rectangle", x, y, w, h, stroke=stroke, fill=fill)


def diamond(element_id, x, y, w, h, fill="#fff3bf", stroke="#f59e0b"):
    return _common(element_id, "diamond", x, y, w, h, stroke=stroke, fill=fill)


def text(element_id, x, y, content, size=18, stroke="#374151"):
    base = _common(
        element_id,
        "text",
        x,
        y,
        max(120, len(content) * size * 0.95),
        max(30, int(size * 1.6)),
        stroke=stroke,
        fill="transparent",
    )
    base.update(
        {
            "backgroundColor": "transparent",
            "text": content,
            "fontSize": size,
            "fontFamily": 5,
            "textAlign": "center",
            "verticalAlign": "middle",
            "containerId": None,
            "originalText": content,
            "autoResize": True,
            "lineHeight": 1.25,
        }
    )
    return base


def arrow(element_id, x, y, points, stroke="#3b82f6", dashed=False):
    base = _common(element_id, "arrow", x, y, 100, 0, stroke=stroke, fill="transparent")
    base.update(
        {
            "points": points,
            "lastCommittedPoint": points[-1],
            "startBinding": None,
            "endBinding": None,
            "startArrowhead": None,
            "endArrowhead": "arrow",
            "backgroundColor": "transparent",
            "roundness": {"type": 2},
            "elbowed": False,
        }
    )
    if dashed:
        base["strokeStyle"] = "dashed"
    return base


def wrap_md(scene_json):
    return """---
excalidraw-plugin: parsed
tags: [excalidraw]
---
==⚠  Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠== You can decompress Drawing data with the command palette: 'Decompress current Excalidraw file'. For more info check in plugin settings under 'Saving'

# Excalidraw Data

## Text Elements
%%
## Drawing
```json
""" + json.dumps(scene_json, ensure_ascii=False, indent=2) + """
```
%%
"""


def escape_scene():
    e = []
    e.append(text("title", 360, 30, "Go 逃逸分析：栈 vs 堆", 26, "#1e40af"))
    e.append(rect("local", 80, 120, 180, 80, "#c3fae8", "#0f766e"))
    e.append(text("local_t", 110, 145, "局部变量", 18))
    e.append(diamond("judge", 320, 110, 220, 100))
    e.append(text("judge_t", 340, 145, "生命周期是否超出\n当前栈帧？", 16, "#92400e"))
    e.append(rect("stack", 620, 70, 200, 80, "#b2f2bb", "#15803d"))
    e.append(text("stack_t", 650, 95, "栈分配", 18, "#15803d"))
    e.append(rect("heap", 620, 200, 220, 90, "#ffc9c9", "#b91c1c"))
    e.append(text("heap_t", 655, 230, "堆分配", 18, "#b91c1c"))
    e.append(rect("gc", 900, 200, 220, 90, "#ffd8a8", "#c2410c"))
    e.append(text("gc_t", 925, 230, "GC 压力可能上升", 17, "#c2410c"))

    e.append(arrow("a1", 260, 160, [[0, 0], [60, 0]], "#3b82f6"))
    e.append(arrow("a2", 540, 160, [[0, 0], [80, -40]], "#16a34a"))
    e.append(text("yes_no1", 555, 95, "否", 16, "#15803d"))
    e.append(arrow("a3", 540, 180, [[0, 0], [80, 60]], "#ef4444"))
    e.append(text("yes_no2", 555, 245, "是", 16, "#b91c1c"))
    e.append(arrow("a4", 840, 245, [[0, 0], [60, 0]], "#f97316"))

    cards = [
        "return &T{}",
        "&T -> channel",
        "[]*T 指针元素",
        "append 扩容",
        "闭包捕获",
        "反射/interface 调用",
    ]
    x0, y0 = 70, 350
    for i, c in enumerate(cards):
        cx = x0 + (i % 3) * 280
        cy = y0 + (i // 3) * 110
        e.append(rect(f"card_{i}", cx, cy, 250, 70, "#d0bfff", "#6d28d9"))
        e.append(text(f"cardt_{i}", cx + 25, cy + 20, c, 16, "#5b21b6"))
        e.append(arrow(f"link_{i}", 730, 290, [[0, 0], [cx - 730 + 120, cy - 290]], "#8b5cf6", dashed=True))

    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin",
        "elements": e,
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    }


def leak_scene():
    e = []
    e.append(text("title2", 330, 30, "Go 内存泄漏：长期可达才是关键", 24, "#1e40af"))
    e.append(rect("root", 80, 120, 220, 80, "#a5d8ff", "#1e40af"))
    e.append(text("root_t", 110, 145, "GC 根\n全局/栈", 17))
    e.append(rect("chain", 380, 120, 220, 80, "#d0bfff", "#6d28d9"))
    e.append(text("chain_t", 410, 145, "引用链", 18))
    e.append(rect("live", 680, 120, 260, 80, "#ffc9c9", "#b91c1c"))
    e.append(text("live_t", 710, 145, "对象仍可达 -> 不回收", 17, "#b91c1c"))
    e.append(rect("dead", 680, 240, 260, 80, "#b2f2bb", "#15803d"))
    e.append(text("dead_t", 710, 265, "对象不可达 -> 可回收", 17, "#15803d"))

    e.append(arrow("l1", 300, 160, [[0, 0], [80, 0]], "#3b82f6"))
    e.append(arrow("l2", 600, 160, [[0, 0], [80, 0]], "#ef4444"))
    e.append(arrow("l3", 600, 180, [[0, 0], [80, 100]], "#16a34a", dashed=True))

    items = [
        "全局 map/缓存只增不减",
        "goroutine 阻塞不退出",
        "循环里误用 time.After",
        "回调/订阅不注销",
        "文件/连接未关闭",
    ]
    for i, c in enumerate(items):
        y = 370 + i * 85
        e.append(rect(f"leak_{i}", 80, y, 340, 60, "#ffd8a8", "#c2410c"))
        e.append(text(f"leakt_{i}", 105, y + 18, c, 16, "#9a3412"))
        e.append(arrow(f"llink_{i}", 420, y + 30, [[0, 0], [260, -240 + i * 10]], "#f97316", dashed=True))

    e.append(rect("tip", 760, 400, 360, 130, "#fff3bf", "#a16207"))
    e.append(text("tip_t", 790, 430, "纠偏：循环引用在 Go 里通常不是根因\n关键看是否仍从 GC 根可达", 16, "#92400e"))

    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin",
        "elements": e,
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    }


def main():
    BASE.mkdir(parents=True, exist_ok=True)
    files = {
        "内存逃逸.流程图.md": escape_scene(),
        "内存泄漏.关系图.md": leak_scene(),
    }
    for name, payload in files.items():
        (BASE / name).write_text(wrap_md(payload), encoding="utf-8")
    print("generated:", ", ".join(files.keys()))


if __name__ == "__main__":
    main()
