# -*- coding: utf-8 -*-
"""Generate Obsidian Excalidraw .md for MySQL 数据一致性 series."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "excalidraw"


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


def diamond(element_id, x, y, w, h, fill="#fff3bf", stroke="#d97706"):
    return _common(element_id, "diamond", x, y, w, h, stroke=stroke, fill=fill)


def ellipse(element_id, x, y, w, h, fill="#c3fae8", stroke="#0f766e"):
    r = _common(element_id, "ellipse", x, y, w, h, stroke=stroke, fill=fill)
    r["roundness"] = {"type": 2}
    return r


def text(element_id, x, y, content, size=18, stroke="#374151", w=None, h=None):
    tw = w if w is not None else max(80, int(len(content) * size * 0.92))
    th = h if h is not None else max(28, int(size * 1.35 * (1 + content.count("\n"))))
    base = _common(element_id, "text", x, y, tw, th, stroke=stroke, fill="transparent")
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


def arrow(element_id, x, y, points, stroke="#3b82f6", dashed=False, start_arrow=False):
    base = _common(element_id, "arrow", x, y, 100, 0, stroke=stroke, fill="transparent")
    base.update(
        {
            "points": points,
            "lastCommittedPoint": points[-1],
            "startBinding": None,
            "endBinding": None,
            "startArrowhead": "arrow" if start_arrow else None,
            "endArrowhead": "arrow",
            "backgroundColor": "transparent",
            "roundness": {"type": 2},
            "elbowed": False,
        }
    )
    if dashed:
        base["strokeStyle"] = "dashed"
    return base


def line_poly(element_id, x, y, points, stroke="#3b82f6", dashed=False):
    base = _common(element_id, "line", x, y, 100, 0, stroke=stroke, fill="transparent")
    base.update(
        {
            "points": points,
            "lastCommittedPoint": points[-1],
            "startBinding": None,
            "endBinding": None,
            "startArrowhead": None,
            "endArrowhead": None,
            "backgroundColor": "transparent",
            "roundness": {"type": 2},
        }
    )
    if dashed:
        base["strokeStyle"] = "dashed"
    return base


def scene(elements):
    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin",
        "elements": elements,
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    }


def wrap_md(scene_json):
    return (
        """---
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
        + json.dumps(scene_json, ensure_ascii=False, indent=2)
        + """
```
%%
"""
    )


def acid_mindmap():
    e = []
    e.append(text("t0", 400, 28, "事务 ACID：C 是目标，A/I/D 是手段之一", 22, "#1e40af", 520, 36))
    e.append(ellipse("center", 480, 200, 200, 100, "#a5d8ff", "#1e40af"))
    e.append(text("tc", 520, 235, "事务\nTransaction", 18, "#1e40af", 120, 50))

    # A - top left
    e.append(rect("a", 120, 120, 200, 90, "#b2f2bb", "#15803d"))
    e.append(text("at", 140, 145, "A 原子性", 18, "#15803d"))
    e.append(rect("undo", 80, 40, 140, 56, "#c3fae8", "#0f766e"))
    e.append(text("undot", 95, 55, "Undo Log", 16, "#0f766e"))
    e.append(arrow("a1", 200, 96, [[0, 0], [40, 24]], "#15803d"))
    e.append(text("a_note", 210, 70, "翻车则按日志回滚", 16, "#374151", 180, 24))

    # C - top right
    e.append(rect("c", 840, 120, 220, 90, "#ffd8a8", "#c2410c"))
    e.append(text("ct", 870, 145, "C 一致性", 18, "#9a3412"))
    e.append(rect("rule", 900, 40, 200, 56, "#fff3bf", "#a16207"))
    e.append(text("rulet", 920, 55, "约束 / 业务规则", 16, "#92400e"))
    e.append(arrow("c1", 920, 96, [[0, 0], [-40, 24]], "#c2410c"))
    e.append(text("c_note", 720, 70, "结果合法，应用+约束兜底", 16, "#374151", 220, 24))

    # I - bottom left
    e.append(rect("i", 120, 360, 200, 90, "#d0bfff", "#6d28d9"))
    e.append(text("it", 150, 385, "I 隔离性", 18, "#5b21b6"))
    e.append(rect("lock", 40, 480, 100, 56, "#eebefa", "#86198f"))
    e.append(text("lockt", 55, 495, "锁", 17, "#701a75"))
    e.append(rect("mvcc", 180, 480, 120, 56, "#d0bfff", "#6d28d9"))
    e.append(text("mvcct", 195, 495, "MVCC", 16, "#5b21b6"))
    e.append(arrow("i1", 220, 450, [[0, 0], [0, 30]], "#6d28d9"))
    e.append(arrow("i2", 220, 450, [[0, 0], [80, 30]], "#6d28d9"))
    e.append(arrow("i3", 580, 420, [[0, 0], [-200, 80]], "#3b82f6", dashed=True))
    e.append(text("i_note", 600, 480, "虚线：见 5.2 MVCC", 16, "#3b82f6", 160, 24))

    # D - bottom right
    e.append(rect("d", 840, 360, 240, 90, "#ffc9c9", "#b91c1c"))
    e.append(text("dt", 890, 385, "D 持久性", 18, "#b91c1c"))
    e.append(rect("redo", 900, 480, 200, 70, "#c3fae8", "#0f766e"))
    e.append(text("redot", 920, 495, "Redo Log + WAL\n先记日志再刷页", 16, "#0f766e", 160, 44))
    e.append(arrow("d1", 960, 450, [[0, 0], [0, 30]], "#b91c1c"))

    e.append(arrow("to_a", 480, 200, [[0, 0], [-200, -40]], "#3b82f6"))
    e.append(arrow("to_c", 680, 200, [[0, 0], [200, -40]], "#3b82f6"))
    e.append(arrow("to_i", 480, 300, [[0, 0], [-200, 100]], "#3b82f6"))
    e.append(arrow("to_d", 680, 300, [[0, 0], [200, 100]], "#3b82f6"))

    e.append(rect("foot", 280, 600, 640, 70, "#fff3bf", "#a16207"))
    e.append(
        text(
            "foott",
            300,
            620,
            "图注：一致性是目标；原子性、隔离性、持久性是达成目标的工程手段",
            16,
            "#92400e",
            600,
            40,
        )
    )
    return scene(e)


def isolation_ladder():
    e = []
    e.append(text("t0", 320, 24, "隔离级别阶梯：从松到严", 24, "#1e40af", 400, 32))
    steps = [
        ("RU\n读未提交", "脏读风险高", "#ffc9c9", "#b91c1c"),
        ("RC\n读已提交", "每次读可能见新提交\n不可重复读", "#ffd8a8", "#c2410c"),
        ("RR\n可重复读", "InnoDB 默认\n快照 + 锁配合", "#fff3bf", "#a16207"),
        ("Serializable\n串行化", "读也加锁\n最严、并发最差", "#b2f2bb", "#15803d"),
    ]
    y0, w, h, gap = 100, 280, 100, 24
    for i, (title, note, fill, stroke) in enumerate(steps):
        y = y0 + i * (h + gap)
        x = 120 + i * 45
        e.append(rect(f"s{i}", x, y, w, h, fill, stroke))
        e.append(text(f"st{i}", x + 30, y + 18, title, 17, stroke, w - 60, 50))
        e.append(text(f"sn{i}", x + 20, y + 68, note, 16, "#374151", w - 40, 40))

    e.append(arrow("lad", 400, 92, [[0, 0], [0, 420]], "#3b82f6"))
    e.append(text("up", 410, 280, "更严", 16, "#1e40af"))

    # Anomaly column
    e.append(text("an_title", 720, 100, "典型异常「仍可能出现」", 18, "#1e40af", 260, 28))
    boxes = [
        ("脏读", "RU"),
        ("不可重复读", "RC 起缓解\nRR 快照缓解"),
        ("幻读", "RR 部分场景\n需当前读+锁"),
    ]
    for j, (name, hint) in enumerate(boxes):
        yy = 150 + j * 95
        e.append(rect(f"an{j}", 700, yy, 200, 70, "#d0bfff", "#6d28d9"))
        e.append(text(f"ant{j}", 720, yy + 12, name + "\n" + hint, 15, "#5b21b6", 160, 50))

    e.append(arrow("d1", 680, 140, [[0, 0], [-180, -20]], "#3b82f6", dashed=True))
    e.append(arrow("d2", 680, 235, [[0, 0], [-235, 0]], "#3b82f6", dashed=True))
    e.append(arrow("d3", 680, 330, [[0, 0], [-280, 80]], "#3b82f6", dashed=True))
    return scene(e)


def read_write_compare():
    e = []
    e.append(text("t0", 300, 20, "读写冲突：武斗 vs 文斗", 24, "#1e40af", 400, 32))
    e.append(rect("row", 380, 80, 440, 56, "#c3fae8", "#0f766e"))
    e.append(text("rowt", 420, 95, "同一行数据：当前版本 + 虚线老版本「Undo」", 16, "#0f766e", 360, 40))

    e.append(rect("bg_l", 40, 160, 520, 320, "#dbe4ff", "#1e40af"))
    e.append(rect("bg_r", 600, 160, 560, 320, "#d3f9d8", "#15803d"))
    e.append(text("lt", 220, 175, "武斗：锁", 20, "#1e40af"))
    e.append(text("rt", 820, 175, "文斗：MVCC", 20, "#15803d"))

    e.append(rect("w1", 80, 220, 160, 60, "#ffc9c9", "#b91c1c"))
    e.append(text("w1t", 100, 238, "写进行中", 17, "#b91c1c"))
    e.append(rect("r1", 300, 220, 160, 60, "#ffd8a8", "#c2410c"))
    e.append(text("r1t", 320, 238, "读等待", 17, "#9a3412"))
    e.append(arrow("a_l", 240, 250, [[0, 0], [60, 0]], "#b91c1c"))
    e.append(text("l_note", 120, 300, "当前读、串行感", 17, "#374151", 200, 24))

    e.append(rect("w2", 640, 220, 180, 60, "#b2f2bb", "#15803d"))
    e.append(text("w2t", 670, 238, "写产生新版本", 17, "#15803d"))
    e.append(rect("r2", 880, 220, 160, 60, "#a5d8ff", "#1e40af"))
    e.append(text("r2t", 900, 238, "读看旧版本", 17, "#1e40af"))
    e.append(arrow("a_r", 820, 250, [[0, 0], [60, 0]], "#15803d"))
    e.append(text("r_note", 700, 300, "快照读、少阻塞", 17, "#374151", 200, 24))

    e.append(
        line_poly(
            "dashv",
            500,
            240,
            [[0, 0], [0, 40], [-80, 80], [-80, 120]],
            "#64748b",
            dashed=True,
        )
    )
    e.append(
        line_poly(
            "dashv2",
            520,
            240,
            [[0, 0], [0, 50], [60, 90], [60, 130]],
            "#64748b",
            dashed=True,
        )
    )
    e.append(text("ver_hint", 400, 400, "老版本", 16, "#64748b"))
    return scene(e)


def snapshot_current_flow():
    e = []
    e.append(text("t0", 280, 20, "快照读 vs 当前读", 24, "#1e40af", 320, 32))
    e.append(rect("in", 480, 60, 200, 56, "#a5d8ff", "#1e40af"))
    e.append(text("int", 520, 75, "SELECT 入口", 18, "#1e40af"))

    e.append(diamond("d", 450, 140, 260, 100))
    e.append(
        text(
            "dt",
            470,
            168,
            "FOR UPDATE /\nLOCK IN SHARE MODE\n或 DML？",
            16,
            "#92400e",
            220,
            50,
        )
    )

    e.append(rect("snap", 120, 280, 280, 120, "#b2f2bb", "#15803d"))
    e.append(text("snapt", 140, 300, "快照读", 20, "#15803d"))
    e.append(text("snapd", 135, 330, "ReadView + 版本链", 17, "#15803d", 250, 50))

    e.append(rect("cur", 720, 280, 400, 120, "#ffc9c9", "#b91c1c"))
    e.append(text("curt", 840, 300, "当前读", 20, "#b91c1c"))
    e.append(text("curd", 740, 330, "读最新 + 可能加锁", 17, "#b91c1c", 360, 50))

    e.append(arrow("y1", 580, 240, [[0, 0], [-200, 80]], "#15803d"))
    e.append(text("yl", 400, 250, "否", 16, "#15803d"))
    e.append(arrow("y2", 710, 240, [[0, 0], [120, 80]], "#b91c1c"))
    e.append(text("yr", 840, 250, "是", 16, "#b91c1c"))

    e.append(rect("side", 720, 440, 400, 100, "#fff3bf", "#a16207"))
    e.append(
        text(
            "sidet",
            735,
            460,
            "当前读侧：INSERT / UPDATE / DELETE\nSELECT … FOR UPDATE 等",
            16,
            "#92400e",
            370,
            50,
        )
    )
    return scene(e)


def version_chain():
    e = []
    e.append(text("t0", 360, 20, "版本链：从新到旧", 24, "#1e40af", 320, 32))
    versions = [
        ("当前版本\ntrx_id 最新", "#b2f2bb", "#15803d"),
        ("旧版本 1\ntrx_id / roll_pointer", "#a5d8ff", "#1e40af"),
        ("旧版本 2", "#d0bfff", "#6d28d9"),
    ]
    x = 680
    for i, (label, fill, stroke) in enumerate(versions):
        e.append(rect(f"v{i}", x, 100 + i * 120, 200, 88, fill, stroke))
        e.append(text(f"vt{i}", x + 20, 120 + i * 120, label, 16, stroke, 160, 60))
        if i < len(versions) - 1:
            e.append(arrow(f"vp{i}", x + 100, 188 + i * 120, [[0, 0], [0, 32]], stroke))
    e.append(arrow("vlast", 780, 100 + (len(versions) - 1) * 120 + 88, [[0, 0], [0, 40]], "#6d28d9"))
    e.append(ellipse("undo", 730, 520, 220, 80, "#c3fae8", "#0f766e"))
    e.append(text("undot", 770, 545, "Undo 存储区", 18, "#0f766e"))

    e.append(rect("iu", 80, 120, 200, 70, "#ffd8a8", "#c2410c"))
    e.append(text("iut", 100, 135, "insert undo\n快照读通常不需要", 15, "#9a3412", 160, 50))
    e.append(rect("uu", 80, 220, 200, 80, "#d0bfff", "#6d28d9"))
    e.append(
        text(
            "uut",
            95,
            235,
            "update undo\n别事务快照可能依赖",
            15,
            "#5b21b6",
            170,
            50,
        )
    )
    e.append(
        text(
            "note",
            80,
            340,
            "图注：两种 undo 可用不同描边色区分\n清理时机不同",
            16,
            "#374151",
            320,
            50,
        )
    )
    return scene(e)


def readview_flow():
    e = []
    e.append(text("t0", 280, 16, "ReadView：版本可见性判断", 22, "#1e40af", 400, 30))
    e.append(rect("rv", 340, 55, 520, 100, "#fff3bf", "#a16207"))
    e.append(
        text(
            "rvt",
            360,
            70,
            "快照字段：m_ids\nmin_trx_id「up_limit」\nmax_trx_id「low_limit」",
            16,
            "#92400e",
            480,
            70,
        )
    )

    e.append(text("q", 480, 175, "对某版本 trx_id", 17, "#1e40af"))
    e.append(diamond("d1", 400, 205, 200, 70))
    e.append(text("d1t", 430, 225, "< min_trx_id ?", 16, "#92400e"))
    e.append(rect("yes1", 120, 210, 120, 52, "#b2f2bb", "#15803d"))
    e.append(text("yes1t", 140, 222, "可见", 17, "#15803d"))
    e.append(arrow("a1", 400, 235, [[0, 0], [-160, 0]], "#15803d"))
    e.append(text("l1", 290, 218, "是", 16, "#15803d"))
    e.append(arrow("a1n", 500, 275, [[0, 0], [0, 25]], "#374151"))
    e.append(text("l1n", 508, 268, "否", 16, "#374151"))

    e.append(diamond("d2", 420, 300, 240, 80))
    e.append(text("d2t", 445, 318, ">= max_trx_id ?", 16, "#92400e"))
    e.append(rect("no2", 120, 310, 120, 52, "#ffc9c9", "#b91c1c"))
    e.append(text("no2t", 135, 322, "不可见", 17, "#b91c1c"))
    e.append(arrow("a2", 420, 340, [[0, 0], [-180, 20]], "#b91c1c"))
    e.append(text("l2", 280, 325, "是", 16, "#b91c1c"))
    e.append(arrow("a2n", 540, 380, [[0, 0], [0, 20]], "#374151"))
    e.append(text("l2n", 548, 372, "否", 16, "#374151"))

    e.append(diamond("d3", 400, 400, 220, 80))
    e.append(text("d3t", 430, 418, "trx_id in m_ids ?", 16, "#92400e"))
    e.append(rect("no3", 120, 415, 120, 52, "#ffc9c9", "#b91c1c"))
    e.append(rect("yes3", 720, 415, 120, 52, "#b2f2bb", "#15803d"))
    e.append(text("no3t", 135, 427, "不可见", 17, "#b91c1c"))
    e.append(text("yes3t", 745, 427, "可见", 17, "#15803d"))
    e.append(arrow("a3a", 400, 438, [[0, 0], [-260, 10]], "#b91c1c"))
    e.append(arrow("a3b", 620, 438, [[0, 0], [100, 0]], "#15803d"))
    e.append(text("l3a", 200, 405, "是", 16, "#b91c1c"))
    e.append(text("l3b", 660, 405, "否", 16, "#15803d"))

    e.append(rect("loop", 360, 520, 480, 70, "#d0bfff", "#6d28d9"))
    e.append(
        text(
            "loopt",
            380,
            538,
            "否则沿 roll_pointer 找下一版本，重复判断「虚线回环」",
            16,
            "#5b21b6",
            440,
            40,
        )
    )
    e.append(arrow("back", 600, 400, [[0, 0], [0, -120]], "#6d28d9", dashed=True, start_arrow=False))
    return scene(e)


def rc_rr_timeline():
    e = []
    e.append(text("t0", 260, 16, "RC vs RR：何时创建 ReadView", 22, "#1e40af", 420, 30))
    e.append(line_poly("axis", 80, 200, [[0, 0], [1000, 0]], "#64748b"))
    e.append(text("t1", 200, 165, "T1 第一次查询", 16, "#1e40af"))
    e.append(text("t2", 480, 165, "T2 他事务提交", 16, "#f59e0b"))
    e.append(text("t3", 780, 165, "T3 第二次查询", 16, "#1e40af"))
    e.append(arrow("m1", 240, 200, [[0, 0], [0, -30]], "#3b82f6"))
    e.append(arrow("m2", 500, 200, [[0, 0], [0, -30]], "#f59e0b"))
    e.append(arrow("m3", 820, 200, [[0, 0], [0, -30]], "#3b82f6"))

    e.append(rect("rc_bg", 60, 240, 1080, 140, "#dbe4ff", "#1e40af"))
    e.append(text("rcl", 80, 250, "RC：每次一致性读重拍 ReadView", 18, "#1e40af"))
    e.append(rect("cam1", 180, 290, 100, 50, "#fff3bf", "#a16207"))
    e.append(text("cam1t", 195, 303, "快照\nT1", 15, "#92400e"))
    e.append(rect("cam3", 760, 290, 100, 50, "#fff3bf", "#a16207"))
    e.append(text("cam3t", 775, 303, "快照\nT3", 15, "#92400e"))
    e.append(text("rc_note", 400, 305, "T3 可能看到 T2 提交后的新数据", 16, "#374151", 340, 24))

    e.append(rect("rr_bg", 60, 400, 1080, 130, "#d3f9d8", "#15803d"))
    e.append(text("rrl", 80, 410, "RR：首次一致性读拍一次，之后共用", 18, "#15803d"))
    e.append(rect("camr", 180, 450, 100, 50, "#b2f2bb", "#15803d"))
    e.append(text("camrt", 195, 463, "仅 T1", 16, "#15803d"))
    e.append(text("rr_note", 340, 460, "T3 仍用同一张快照，与「进门拍一张」一致", 16, "#374151", 520, 28))
    return scene(e)


def phantom_compare():
    e = []
    e.append(text("t0", 240, 16, "RR 与幻读：两次范围查询间别事务插入", 20, "#1e40af", 520, 30))
    e.append(rect("a", 80, 60, 480, 280, "#dbe4ff", "#1e40af"))
    e.append(rect("b", 600, 60, 520, 280, "#ffd8a8", "#c2410c"))
    e.append(text("at", 240, 72, "情况 A：仅快照读", 20, "#1e40af"))
    e.append(text("bt", 800, 72, "情况 B：第二次当前读", 20, "#9a3412"))
    e.append(text("a1", 110, 120, "两次 SELECT 都是快照读", 17, "#374151"))
    e.append(text("a2", 110, 160, "第二次仍看不到新行", 17, "#15803d"))
    e.append(text("a3", 110, 200, "MVCC 快照不变", 16, "#1e40af"))
    e.append(text("b1", 630, 120, "第二次 FOR UPDATE 等当前读", 17, "#374151"))
    e.append(text("b2", 630, 160, "读最新 + 间隙锁 / 临键锁", 17, "#b91c1c"))
    e.append(text("b3", 630, 200, "与纯快照路径不同", 16, "#9a3412"))

    e.append(rect("foot", 120, 380, 960, 80, "#fff3bf", "#a16207"))
    e.append(
        text(
            "foott",
            140,
            400,
            "防幻读 = MVCC + 锁分工，不是单靠 MVCC 包打天下",
            18,
            "#92400e",
            900,
            44,
        )
    )
    return scene(e)


def main():
    BASE.mkdir(parents=True, exist_ok=True)
    files = {
        "5.1-ACID四块拼图.关系图.md": acid_mindmap(),
        "5.1-隔离级别阶梯.对比图.md": isolation_ladder(),
        "5.2-读写冲突两条路.对比图.md": read_write_compare(),
        "5.2-快照读与当前读.流程图.md": snapshot_current_flow(),
        "5.2-版本链.关系图.md": version_chain(),
        "5.2-ReadView判断.流程图.md": readview_flow(),
        "5.2-RC与RR-ReadView时机.时间线图.md": rc_rr_timeline(),
        "5.2-RR与幻读.对比图.md": phantom_compare(),
    }
    for name, payload in files.items():
        (BASE / name).write_text(wrap_md(payload), encoding="utf-8")
    print("generated:", len(files), "files ->", BASE)


if __name__ == "__main__":
    main()
