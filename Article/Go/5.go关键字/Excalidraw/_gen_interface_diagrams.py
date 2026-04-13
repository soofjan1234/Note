# -*- coding: utf-8 -*-
"""Generate Obsidian Excalidraw .md files for interface.md topics."""
from __future__ import annotations

import json
import os
from typing import Any, List

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

def base(seed: int) -> dict[str, Any]:
    return {
        "angle": 0,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "roundness": {"type": 3},
        "seed": seed,
        "version": 1,
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
    }


def rect(
    eid: str,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    *,
    bg: str,
    stroke: str,
    seed: int,
    fs: int = 18,
) -> List[dict[str, Any]]:
    tw = max(len(text), 4) * fs * 0.55
    th = fs * 1.35
    tx = x + (w - min(tw, w - 16)) / 2
    ty = y + (h - th) / 2
    r = {
        "type": "rectangle",
        "id": eid + "-r",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "strokeColor": stroke,
        "backgroundColor": bg,
        "fillStyle": "solid",
        "strokeWidth": 2,
        **base(seed),
    }
    txt = {
        "type": "text",
        "id": eid + "-t",
        "x": tx,
        "y": ty,
        "width": w - 20,
        "height": th + 4,
        "text": text,
        "fontSize": fs,
        "fontFamily": 5,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": None,
        "originalText": text,
        "lineHeight": 1.25,
        "strokeColor": "#374151",
        "backgroundColor": "transparent",
        **base(seed + 1),
    }
    return [r, txt]


def arrow(
    eid: str,
    x: float,
    y: float,
    dx: float,
    dy: float,
    seed: int,
) -> dict[str, Any]:
    return {
        "type": "arrow",
        "id": eid,
        "x": x,
        "y": y,
        "width": dx,
        "height": dy,
        "strokeColor": "#3b82f6",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "points": [[0, 0], [dx, dy]],
        "lastCommittedPoint": None,
        "startBinding": None,
        "endBinding": None,
        "startArrowhead": None,
        "endArrowhead": "arrow",
        **base(seed),
    }


def title(txt: str, y: float, seed: int) -> List[dict[str, Any]]:
    w, h = 900, 44
    x = (1200 - w) / 2
    return rect("title", x, y, w, h, txt, bg="#dbeafe", stroke="#1e40af", seed=seed, fs=22)


def drawing(elements: List[dict[str, Any]]) -> dict[str, Any]:
    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin",
        "elements": elements,
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    }


def write_md(name: str, elements: List[dict[str, Any]]) -> None:
    path = os.path.join(OUT_DIR, name)
    body = json.dumps(drawing(elements), ensure_ascii=False, separators=(",", ":"))
    md = f"""---
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
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    print("wrote", path)


def diag1() -> None:
    els: List[dict[str, Any]] = []
    s = 1000
    els.extend(title("interface 概览：方法集合抽象", 36, s))
    s += 10
    els.extend(rect("c", 360, 120, 480, 88, "接口 = 一组方法「行为」", bg="#a5d8ff", stroke="#1e40af", seed=s))
    s += 20
    els.extend(rect("l1", 80, 260, 260, 100, "具体类型 T\n同名同签名方法", bg="#c3fae8", stroke="#15803d", seed=s))
    s += 5
    els.extend(rect("l2", 80, 400, 260, 72, "自动满足接口\n无需 implements", bg="#b2f2bb", stroke="#15803d", seed=s))
    s += 5
    els.append(arrow("a1", 340, 310, 30, -50, s))
    s += 1
    els.append(arrow("a2", 340, 360, 30, 20, s))
    s += 1
    els.extend(rect("r1", 820, 260, 300, 88, "动态类型\n当前装着哪种具体类型", bg="#d0bfff", stroke="#5b21b6", seed=s))
    s += 5
    els.extend(rect("r2", 820, 380, 300, 88, "动态值\ndata 指向副本或指针等", bg="#ffd8a8", stroke="#c2410c", seed=s))
    s += 5
    els.append(arrow("a3", 840, 208, -40, 60, s))
    s += 1
    els.append(arrow("a4", 840, 348, -40, 40, s))
    s += 1
    els.extend(rect("b", 320, 520, 560, 72, "nil 判断：同时看「类型槽 + 值槽」两层", bg="#fff3bf", stroke="#b45309", seed=s, fs=17))
    write_md("interface.概览_隐式实现_双分量.md", els)


def diag2() -> None:
    els: List[dict[str, Any]] = []
    s = 2000
    els.extend(title("eface 与 iface 与 data", 36, s))
    s += 10
    els.extend(rect("h1", 60, 110, 480, 56, "空接口 any / interface{}", bg="#dbeafe", stroke="#1e40af", seed=s, fs=20))
    s += 5
    els.extend(rect("e1", 60, 190, 480, 70, "槽1：_type", bg="#a5d8ff", stroke="#1e40af", seed=s))
    s += 5
    els.extend(rect("e2", 60, 280, 480, 70, "槽2：data", bg="#c3fae8", stroke="#15803d", seed=s))
    s += 5
    els.extend(rect("h2", 660, 110, 480, 56, "非空接口「有方法」", bg="#ede9fe", stroke="#5b21b6", seed=s, fs=20))
    s += 5
    els.extend(rect("i1", 660, 190, 480, 70, "槽1：itab「含 Fun[]」", bg="#d0bfff", stroke="#5b21b6", seed=s))
    s += 5
    els.extend(rect("i2", 660, 280, 480, 70, "槽2：data", bg="#c3fae8", stroke="#15803d", seed=s))
    s += 5
    els.extend(rect("d1", 60, 400, 300, 88, "值副本\nint struct 等", bg="#ffd8a8", stroke="#c2410c", seed=s))
    s += 5
    els.extend(rect("d2", 390, 400, 300, 88, "指针 *T\ndata 常是这根指针", bg="#ffc9c9", stroke="#b91c1c", seed=s))
    s += 5
    els.extend(rect("d3", 720, 400, 420, 88, "优化：小整数 空串 nil slice\n可指向只读表或零值区", bg="#fff3bf", stroke="#b45309", seed=s, fs=16))
    s += 5
    els.extend(rect("n", 200, 520, 800, 88, "例：var i any = 「*S」「nil」 → 类型槽非空 data 为 nil → i != nil", bg="#eebefa", stroke="#7c3aed", seed=s, fs=16))
    write_md("interface.eface与iface与data.md", els)


def diag3() -> None:
    els: List[dict[str, Any]] = []
    s = 3000
    els.extend(title("构建主线：convT → getitab → itabInit → 派发", 28, s))
    s += 10
    ys = [120, 230, 360, 500, 640]
    boxes = [
        ("1 赋值到接口", "可能 convT* 准备 data"),
        ("2 getitab「I,T」", "查 itabTable 缓存\n未命中加锁再建"),
        ("3 itabInit", "匹配方法填 Fun[]\n失败 Fun[0] 为 0"),
        ("4 调用", "取 itab.Fun[i] 间接调用\ndata 作接收者"),
    ]
    x, w, h = 200, 800, 88
    for i, (t1, t2) in enumerate(boxes):
        els.extend(rect(f"st{i}", x, ys[i], w, h, f"{t1}\n{t2}", bg="#a5d8ff" if i % 2 == 0 else "#d0bfff", stroke="#1e40af", seed=s, fs=17))
        s += 3
        if i < len(boxes) - 1:
            els.append(arrow(f"da{i}", x + w // 2 - 5, ys[i] + h, 0, ys[i + 1] - ys[i] - h - 4, s))
            s += 1
    els.extend(rect("note", 80, 720, 1040, 56, "一句话：接口调用 = 类型信息 + data + Fun[] 跳转表", bg="#fff3bf", stroke="#b45309", seed=s, fs=17))
    write_md("interface.构建主线_getitab_itabInit_派发.md", els)


def diag4() -> None:
    els: List[dict[str, Any]] = []
    s = 4000
    els.extend(title("nil：空接口 vs 装着 nil 指针的接口", 36, s))
    s += 10
    els.extend(rect("L", 80, 120, 480, 200, "var e1 error 未赋值\n类型槽：空\ndata：空\ne1 == nil 为 true", bg="#b2f2bb", stroke="#15803d", seed=s, fs=17))
    s += 5
    els.extend(rect("R", 640, 120, 480, 200, "var p *MyError = nil\nvar e2 error = p\n类型槽：*MyError\ndata：nil\ne2 == nil 为 false", bg="#ffc9c9", stroke="#b91c1c", seed=s, fs=16))
    s += 5
    els.extend(rect("sum", 200, 360, 800, 100, "对接口 == nil 判的是「整个接口值」是否从未持有具体类型\n需要时用 errors.Is / errors.As", bg="#fff3bf", stroke="#b45309", seed=s, fs=17))
    write_md("interface.nil接口与nil指针对比.md", els)


def diag5() -> None:
    els: List[dict[str, Any]] = []
    s = 5000
    els.extend(title("any、类型断言、type switch", 36, s))
    s += 10
    els.extend(rect("any", 120, 120, 320, 80, "any ≡ interface{}", bg="#dbeafe", stroke="#1e40af", seed=s, fs=18))
    s += 5
    els.extend(rect("any2", 120, 220, 320, 100, "能装任意类型\n不自带运算能力", bg="#a5d8ff", stroke="#1e40af", seed=s, fs=17))
    s += 5
    els.extend(rect("as1", 520, 120, 320, 72, "x.(T) 失败 panic", bg="#ffd8a8", stroke="#c2410c", seed=s))
    s += 5
    els.extend(rect("as2", 520, 210, 320, 100, "x.(T), ok\n失败不 panic", bg="#d0bfff", stroke="#5b21b6", seed=s, fs=17))
    s += 5
    els.extend(rect("sw", 120, 380, 920, 160, "switch x.(type)\ncase nil 只匹配「接口本身 nil」\n与 动态类型 *T 且指针 nil 不同", bg="#c3fae8", stroke="#15803d", seed=s, fs=18))
    write_md("interface.any_断言_typeSwitch.md", els)


def main() -> None:
    diag1()
    diag2()
    diag3()
    diag4()
    diag5()


if __name__ == "__main__":
    main()
