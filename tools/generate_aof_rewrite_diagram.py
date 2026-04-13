import json
from pathlib import Path


def rect(eid, x, y, w, h, text, stroke="#1e40af", bg="#dbeafe", fs=18):
    shape = {
        "id": f"{eid}_box",
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
        "seed": abs(hash(f"{eid}_box")) % 1000000,
        "version": 1,
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
    }
    txt = {
        "id": f"{eid}_text",
        "type": "text",
        "x": x + 20,
        "y": y + 18,
        "width": int(w - 40),
        "height": int(fs * 1.25 * (text.count("\n") + 1)),
        "angle": 0,
        "strokeColor": "#374151",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "roundness": None,
        "seed": abs(hash(f"{eid}_text")) % 1000000,
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
        "autoResize": False,
        "lineHeight": 1.25,
    }
    return [shape, txt]


def arrow(eid, x, y, dx, dy, label="", color="#3b82f6", dashed=False):
    a = {
        "id": eid,
        "type": "arrow",
        "x": x,
        "y": y,
        "width": abs(dx),
        "height": abs(dy),
        "angle": 0,
        "strokeColor": color,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2 if not dashed else 3,
        "strokeStyle": "dashed" if dashed else "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "roundness": None,
        "seed": abs(hash(eid)) % 1000000,
        "version": 1,
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
        "points": [[0, 0], [dx, dy]],
        "lastCommittedPoint": [dx, dy],
        "startBinding": None,
        "endBinding": None,
        "startArrowhead": None,
        "endArrowhead": "arrow",
    }
    if label:
        a["label"] = {"text": label, "fontSize": 16, "fontFamily": 5}
    return a


elements = []

# Main vertical flow
elements += rect("start", 500, 40, 260, 60, "开始重写\nBGREWRITEAOF", "#1e40af", "#a5d8ff", 18)
elements += rect("fork", 500, 130, 260, 60, "fork 子进程", "#1e40af", "#dbe4ff", 20)
elements += rect("child_write", 500, 230, 260, 72, "子进程按内存快照\n写 New AOF.tmp", "#7e22ce", "#d0bfff", 18)
elements += rect("child_done", 500, 335, 260, 60, "子进程完成并通知主进程", "#7e22ce", "#eebefa", 17)
elements += rect("append_tail", 500, 430, 260, 72, "主进程追加\nAOF Rewrite Buffer", "#b45309", "#ffd8a8", 18)
elements += rect("rename", 500, 535, 260, 60, "atomic rename\n替换旧 AOF", "#15803d", "#b2f2bb", 18)
elements += rect("end", 500, 625, 260, 60, "结束", "#15803d", "#c3fae8", 20)

elements.append(arrow("m1", 630, 100, 0, 30))
elements.append(arrow("m2", 630, 190, 0, 40))
elements.append(arrow("m3", 630, 302, 0, 33))
elements.append(arrow("m4", 630, 395, 0, 35))
elements.append(arrow("m5", 630, 502, 0, 33))
elements.append(arrow("m6", 630, 595, 0, 30))

# Side branch: main process keeps serving writes
elements += rect("serve", 120, 175, 300, 60, "主进程继续处理写请求", "#1e40af", "#dbe4ff", 18)
elements += rect("double_write", 120, 275, 300, 72, "每条新命令双写：\nAOF Buffer + Rewrite Buffer", "#b45309", "#fff3bf", 17)
elements += rect("aof_path", 70, 395, 400, 95, "AOF Buffer -> write -> Page Cache\n-> fsync/回写 -> Old AOF", "#0f766e", "#c3fae8", 17)

elements.append(arrow("b1", 500, 160, -80, 45, "并行分支", "#f59e0b", True))
elements.append(arrow("b2", 270, 235, 0, 40, "持续发生", "#f59e0b", True))
elements.append(arrow("b3", 270, 347, 0, 48, "旧 AOF 持续可用", "#f59e0b", True))

# Child write path explicit page cache
elements += rect("cache_path", 835, 255, 330, 80, "Child -> write -> Page Cache\n-> fsync/回写 -> New AOF.tmp", "#1e40af", "#c3fae8", 17)
elements.append(arrow("c1", 760, 266, 75, 20, "子进程写盘链路", "#3b82f6"))

data = {
    "type": "excalidraw",
    "version": 2,
    "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin",
    "elements": elements,
    "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
    "files": {},
}

doc = """---
excalidraw-plugin: parsed
tags: [excalidraw]
---
==⚠  Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠== You can decompress Drawing data with the command palette: 'Decompress current Excalidraw file'. For more info check in plugin settings under 'Saving'

# Excalidraw Data

## Text Elements
%%
## Drawing
```json
"""
doc += json.dumps(data, ensure_ascii=False, indent=2)
doc += "\n```\n%%\n"

out = Path(r"D:\Note\Article\Redis\Excalidraw\3\AOF重写流程图.流程图.md")
out.write_text(doc, encoding="utf-8")
print(str(out))
