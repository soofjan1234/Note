# -*- coding: utf-8 -*-
"""Generate Obsidian Excalidraw .md for MySQL 日志 series. See ../excalidraw-tip.md."""
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
    tw = w if w is not None else max(80, int(len(content.replace("\n", "")) * size * 0.92))
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


def diagram_6_1_ring_buffer():
    e = []
    e.append(text("t0", 200, 24, "Redo：环形日志与 Write Pos / Checkpoint", 22, "#1e40af", 520, 32))
    # Track outer
    e.append(rect("track", 80, 100, 1040, 100, "#c3fae8", "#0f766e"))
    e.append(text("track_l", 100, 128, "ib_logfile 组：头尾相接循环覆盖", 16, "#0f766e", 320, 44))
    # Segments: checkpoint前 可重用 | 中间待落盘 | write 前
    e.append(rect("seg_done", 100, 118, 280, 64, "#b2f2bb", "#15803d"))
    e.append(text("sd", 140, 132, "Checkpoint 前\n页已落盘·日志可重用", 16, "#15803d", 200, 44))
    e.append(rect("seg_pending", 400, 118, 420, 64, "#ffd8a8", "#c2410c"))
    e.append(text("sp", 480, 132, "未覆盖段：对应脏页可能仍在内存", 16, "#9a3412", 260, 44))
    e.append(rect("seg_new", 840, 118, 260, 64, "#a5d8ff", "#1e40af"))
    e.append(text("sn", 880, 140, "新写入区", 17, "#1e40af", 120, 28))
    # Write pos marker
    e.append(ellipse("wp", 900, 200, 56, 56, "#f59e0b", "#b45309"))
    e.append(text("wpt", 895, 215, "W", 18, "#92400e", 28, 24))
    e.append(text("wpl", 860, 268, "Write Pos\n新日志追加", 16, "#b45309", 120, 40))
    e.append(arrow("a_wp", 928, 118, [[0, 0], [0, 75]], "#f59e0b"))
    # Checkpoint marker
    e.append(ellipse("cp", 360, 200, 56, 56, "#d0bfff", "#6d28d9"))
    e.append(text("cpt", 355, 215, "C", 18, "#5b21b6", 28, 24))
    e.append(text("cpl", 300, 268, "Checkpoint\n推进边界", 16, "#5b21b6", 120, 40))
    e.append(arrow("a_cp", 388, 118, [[0, 0], [0, 75]], "#6d28d9"))
    # Cycle hint
    e.append(line_poly("cyc", 80, 90, [[0, 0], [0, -25], [1040, -25], [1040, 0]], "#64748b", dashed=True))
    e.append(arrow("cyc_a", 1110, 65, [[0, 0], [-30, 0], [-30, 35]], "#64748b"))
    e.append(text("cyc_t", 1120, 50, "循环", 16, "#64748b", 48, 24))
    e.append(rect("foot", 120, 330, 960, 72, "#fff3bf", "#a16207"))
    e.append(
        text(
            "foot_t",
            140,
            348,
            "Write Pos 追上 Checkpoint 时需刷脏、推进检查点，否则阻塞新写入",
            17,
            "#92400e",
            920,
            40,
        )
    )
    return scene(e)


def diagram_6_1_wal_compare():
    e = []
    e.append(text("t0", 320, 20, "WAL：随机写数据页 vs 顺序写 Redo", 22, "#1e40af", 480, 32))
    e.append(rect("left_bg", 60, 70, 480, 300, "#dbe4ff", "#1e40af"))
    e.append(rect("right_bg", 580, 70, 560, 300, "#d3f9d8", "#15803d"))
    e.append(text("lt", 220, 82, "数据页随机落盘", 20, "#1e40af"))
    e.append(text("rt", 820, 82, "Redo 顺序追加", 20, "#15803d"))
    # Scattered pages left
    for i, (px, py) in enumerate([(120, 140), (220, 200), (340, 150), (180, 260), (400, 240)]):
        e.append(rect(f"p{i}", px, py, 72, 48, "#a5d8ff", "#1e40af"))
        e.append(text(f"pt{i}", px + 8, py + 12, "页", 16, "#1e40af", 56, 28))
    e.append(line_poly("zig1", 150, 180, [[0, 0], [80, 60], [160, -20], [240, 40]], "#3b82f6", dashed=True))
    e.append(text("lio", 200, 320, "随机 I/O · 寻道成本高", 17, "#1e40af", 220, 28))
    # Right: one long redo bar
    e.append(rect("redo_bar", 640, 180, 480, 56, "#c3fae8", "#0f766e"))
    e.append(text("rbt", 780, 195, "ib_logfile 顺序写", 17, "#0f766e", 200, 28))
    e.append(arrow("r_arr", 1120, 208, [[0, 0], [40, 0]], "#15803d"))
    e.append(text("seq", 1165, 192, "追加", 16, "#15803d", 48, 24))
    e.append(text("sio", 720, 280, "顺序 I/O · 吞吐通常更好", 17, "#15803d", 260, 28))
    e.append(rect("mid", 200, 400, 800, 64, "#fff3bf", "#a16207"))
    e.append(text("midt", 240, 418, "先写 Redo「WAL」，数据页由后台异步刷盘", 18, "#92400e", 720, 36))
    return scene(e)


def diagram_6_1_redo_flush_path():
    e = []
    e.append(text("t0", 280, 20, "Redo：从脏页变更到 ib_logfile", 22, "#1e40af", 440, 32))
    e.append(rect("bp", 80, 100, 200, 80, "#a5d8ff", "#1e40af"))
    e.append(text("bpt", 100, 120, "Buffer Pool\n脏页", 17, "#1e40af", 160, 44))
    e.append(text("note1", 300, 115, "变更产生 Redo 记录", 16, "#374151", 160, 24))
    e.append(arrow("a1", 280, 135, [[0, 0], [60, 0]], "#3b82f6"))
    e.append(rect("rlb", 360, 100, 220, 80, "#d0bfff", "#6d28d9"))
    e.append(text("rlbt", 380, 120, "Redo Log Buffer\n内存", 17, "#5b21b6", 180, 44))
    e.append(arrow("a2", 580, 135, [[0, 0], [70, 0]], "#3b82f6"))
    e.append(rect("ibf", 670, 100, 240, 80, "#c3fae8", "#0f766e"))
    e.append(text("ibft", 700, 120, "ib_logfile\n磁盘日志文件", 17, "#0f766e", 180, 44))
    e.append(rect("side", 80, 220, 520, 140, "#fff3bf", "#a16207"))
    e.append(text("st", 100, 232, "innodb_flush_log_at_trx_commit", 17, "#92400e", 360, 28))
    e.append(
        text(
            "s1",
            100,
            262,
            "1：提交 fsync · 持久性最强「生产常见默认」\n2：提交写 OS 缓存 · 每秒 fsync · 掉电有风险\n0：后台约每秒刷 · 最快 · 崩溃丢日志风险最大",
            16,
            "#92400e",
            480,
            72,
        )
    )
    e.append(text("foot", 620, 240, "Log Buffer 过半、Checkpoint 等也会触发刷盘", 16, "#374151", 300, 44))
    return scene(e)


def diagram_6_1_lsn_recovery():
    e = []
    e.append(text("t0", 260, 20, "LSN：日志推进、检查点与页恢复", 22, "#1e40af", 500, 32))
    e.append(ellipse("n1", 120, 120, 200, 90, "#a5d8ff", "#1e40af"))
    e.append(text("n1t", 150, 145, "日志 LSN\n推进", 17, "#1e40af", 140, 44))
    e.append(ellipse("n2", 480, 120, 220, 90, "#b2f2bb", "#15803d"))
    e.append(text("n2t", 510, 145, "Checkpoint LSN", 17, "#15803d", 160, 44))
    e.append(ellipse("n3", 800, 120, 220, 90, "#c3fae8", "#0f766e"))
    e.append(text("n3t", 820, 145, "FIL_PAGE_LSN\n页头", 17, "#0f766e", 180, 44))
    e.append(arrow("e12", 320, 160, [[0, 0], [150, 0]], "#3b82f6"))
    e.append(text("e12l", 350, 130, "之前可覆盖", 15, "#3b82f6", 100, 22))
    e.append(arrow("e23", 700, 160, [[0, 0], [90, 0]], "#3b82f6"))
    e.append(rect("flow", 200, 280, 760, 100, "#dbe4ff", "#1e40af"))
    e.append(
        text(
            "ft",
            220,
            300,
            "崩溃恢复：从 Checkpoint 往后扫 Redo；若 页 LSN < 日志应对 LSN → 对该页 Redo 重做",
            17,
            "#1e40af",
            720,
            60,
        )
    )
    e.append(rect("warn", 200, 410, 760, 70, "#fff3bf", "#a16207"))
    e.append(
        text(
            "wt",
            220,
            425,
            "页若物理损坏，单靠 Redo 无法修复，需 Doublewrite / 备份等手段",
            16,
            "#92400e",
            700,
            44,
        )
    )
    return scene(e)


def diagram_6_2_undo_compare():
    e = []
    e.append(text("t0", 220, 20, "Insert Undo 与 Update、Delete Undo", 22, "#1e40af", 560, 32))
    e.append(rect("L", 60, 70, 500, 320, "#dbe4ff", "#1e40af"))
    e.append(rect("R", 600, 70, 520, 320, "#ffd8a8", "#c2410c"))
    e.append(text("lt", 220, 82, "Insert Undo", 20, "#1e40af"))
    e.append(text("rt", 800, 82, "Update / Delete Undo", 20, "#9a3412"))
    e.append(text("l1", 90, 130, "体积小", 17, "#374151"))
    e.append(text("l2", 90, 165, "定位新行，回滚删行", 17, "#1e40af"))
    e.append(text("l3", 90, 210, "事务提交后常可快速回收", 17, "#15803d", 400, 28))
    e.append(text("r1", 630, 130, "带 before image", 17, "#374151"))
    e.append(text("r2", 630, 165, "支撑 MVCC 旧版本链", 17, "#9a3412"))
    e.append(text("r3", 630, 210, "提交后仍可能长期保留，等 Purge", 17, "#b45309", 440, 28))
    e.append(rect("foot", 140, 420, 900, 60, "#fff3bf", "#a16207"))
    e.append(text("ft", 180, 435, "Redo 管提交后恢复；Undo 管未提交回滚与一致性读历史", 17, "#92400e", 820, 36))
    return scene(e)


def diagram_6_2_purge_history():
    e = []
    e.append(text("t0", 200, 20, "History List 与 Purge：从头扫、从尾挂", 22, "#1e40af", 560, 32))
    e.append(rect("chain_bg", 80, 90, 1000, 120, "#c3fae8", "#0f766e"))
    e.append(text("hl", 420, 100, "History List「Undo 待清理链」", 18, "#0f766e", 320, 28))
    e.append(rect("n1", 120, 140, 100, 56, "#a5d8ff", "#1e40af"))
    e.append(text("n1t", 135, 155, "头·最老", 16, "#1e40af", 70, 28))
    e.append(text("dots", 240, 158, "···", 20, "#374151"))
    e.append(rect("n2", 320, 140, 100, 56, "#d0bfff", "#6d28d9"))
    e.append(text("n2t", 345, 158, "结点", 16, "#5b21b6", 50, 24))
    e.append(text("dots2", 440, 158, "···", 20, "#374151"))
    e.append(rect("n3", 520, 140, 100, 56, "#b2f2bb", "#15803d"))
    e.append(text("n3t", 545, 158, "尾", 16, "#15803d", 50, 24))
    e.append(arrow("c1", 220, 165, [[0, 0], [90, 0]], "#0f766e"))
    e.append(arrow("c2", 420, 165, [[0, 0], [90, 0]], "#0f766e"))
    e.append(arrow("commit", 700, 140, [[0, 0], [-80, 0]], "#f59e0b"))
    e.append(text("cmt", 710, 115, "COMMIT 挂到链表尾部", 16, "#b45309", 200, 24))
    e.append(rect("purge", 100, 260, 180, 72, "#ffd8a8", "#c2410c"))
    e.append(text("pgt", 120, 280, "Purge 线程\n从头向尾扫", 16, "#9a3412", 140, 44))
    e.append(arrow("p1", 280, 296, [[0, 0], [40, 0]], "#c2410c"))
    e.append(diamond("d1", 360, 260, 200, 80))
    e.append(text("dt", 400, 285, "ReadView\n仍需要？", 16, "#92400e", 120, 40))
    e.append(rect("yes", 600, 240, 200, 56, "#ffc9c9", "#b91c1c"))
    e.append(text("yt", 630, 255, "暂停·不可删", 16, "#b91c1c", 140, 28))
    e.append(rect("no", 600, 310, 200, 56, "#b2f2bb", "#15803d"))
    e.append(text("nt", 615, 325, "回收 Undo 页", 16, "#15803d", 170, 28))
    e.append(arrow("to_y", 460, 280, [[0, 0], [130, -20]], "#92400e"))
    e.append(arrow("to_n", 460, 320, [[0, 0], [130, 20]], "#92400e"))
    e.append(rect("row", 80, 400, 480, 80, "#eebefa", "#86198f"))
    e.append(
        text(
            "rowt",
            100,
            415,
            "另一职责：Delete Mark 行 → Purge 真正从 B+ 树摘掉",
            17,
            "#701a75",
            440,
            50,
        )
    )
    return scene(e)


def diagram_6_3_binlog_format():
    e = []
    e.append(text("t0", 280, 20, "binlog_format 三种模式", 22, "#1e40af", 400, 32))
    w = 320
    e.append(rect("c1", 60, 80, w, 260, "#dbe4ff", "#1e40af"))
    e.append(rect("c2", 420, 80, w, 260, "#d3f9d8", "#15803d"))
    e.append(rect("c3", 780, 80, w, 260, "#ffd8a8", "#c2410c"))
    e.append(text("t1", 140, 95, "STATEMENT", 19, "#1e40af"))
    e.append(text("t2", 500, 95, "ROW", 19, "#15803d"))
    e.append(text("t3", 860, 95, "MIXED", 19, "#9a3412"))
    e.append(text("b1", 90, 140, "记录原始 SQL 文本", 17, "#374151"))
    e.append(text("b1n", 90, 185, "省空间", 16, "#15803d"))
    e.append(text("b1r", 90, 220, "NOW「」等可能导致主从不一致", 16, "#b91c1c", 260, 40))
    e.append(text("b2", 450, 140, "行级变更前后镜像", 17, "#374151"))
    e.append(text("b2n", 450, 195, "重放结果稳", 16, "#15803d"))
    e.append(text("b2r", 450, 230, "体积往往更大", 16, "#b45309"))
    e.append(text("b3", 810, 140, "Server 择优切换", 17, "#374151"))
    e.append(text("b3n", 810, 200, "能语句则省，有风险则 ROW", 16, "#9a3412", 260, 40))
    e.append(text("b3r", 810, 260, "折中方案", 16, "#92400e"))
    e.append(rect("foot", 200, 370, 760, 56, "#fff3bf", "#a16207"))
    e.append(text("ft", 240, 385, "生产常见：ROW；以业务与版本文档为准", 17, "#92400e", 680, 32))
    return scene(e)


def diagram_6_3_layer_roles():
    e = []
    e.append(text("t0", 240, 20, "层级：Server 的 Binlog 与 InnoDB 的 Redo「」Undo", 21, "#1e40af", 520, 32))
    e.append(rect("srv", 120, 80, 960, 160, "#dbe4ff", "#1e40af"))
    e.append(text("srvt", 520, 95, "MySQL Server 层", 20, "#1e40af"))
    e.append(rect("bin", 360, 130, 480, 90, "#fff3bf", "#a16207"))
    e.append(
        text(
            "bint",
            380,
            145,
            "Binlog\n复制 · PITR · 审计",
            17,
            "#92400e",
            440,
            60,
        )
    )
    e.append(rect("eng", 120, 280, 960, 200, "#d3f9d8", "#15803d"))
    e.append(text("engt", 520, 295, "InnoDB 存储引擎", 20, "#15803d"))
    e.append(rect("redo", 200, 340, 280, 110, "#c3fae8", "#0f766e"))
    e.append(text("redot", 230, 365, "Redo Log\n崩溃恢复·WAL", 17, "#0f766e", 220, 50))
    e.append(rect("undo", 520, 340, 280, 110, "#d0bfff", "#6d28d9"))
    e.append(text("undot", 545, 365, "Undo Log\n回滚·MVCC", 17, "#5b21b6", 230, 50))
    e.append(arrow("2pc1", 640, 175, [[0, 0], [0, 155]], "#6d28d9", dashed=True))
    e.append(arrow("2pc2", 480, 175, [[0, 0], [0, 155]], "#6d28d9", dashed=True))
    e.append(text("tpcl", 660, 220, "2PC 提交时对齐", 16, "#6d28d9", 140, 24))
    return scene(e)


def diagram_6_3_redo_binlog_compare():
    e = []
    e.append(text("t0", 300, 16, "Redo Log vs Binlog 对照", 22, "#1e40af", 400, 32))
    e.append(rect("h1", 80, 60, 480, 48, "#c3fae8", "#0f766e"))
    e.append(rect("h2", 580, 60, 480, 48, "#fff3bf", "#a16207"))
    e.append(text("h1t", 240, 72, "Redo Log「InnoDB」", 18, "#0f766e"))
    e.append(text("h2t", 740, 72, "Binlog「Server」", 18, "#92400e"))
    rows = [
        ("层级", "引擎内部", "Server 层·与引擎解耦"),
        ("用途", "单实例崩溃恢复", "复制·备份恢复·审计"),
        ("内容形态", "物理页修改", "逻辑或行级事件"),
        ("写入方式", "固定文件循环覆盖", "一般追加·可轮转"),
        ("与提交", "WAL + 2PC 与 Binlog 对齐", "2PC 后再视为对外一致"),
    ]
    y0 = 130
    for i, (dim, a, b) in enumerate(rows):
        y = y0 + i * 70
        e.append(rect(f"r{i}a", 80, y, 200, 56, "#dbe4ff", "#1e40af"))
        e.append(text(f"rd{i}", 120, y + 16, dim, 16, "#1e40af", 120, 28))
        e.append(rect(f"r{i}b", 300, y, 260, 56, "#a5d8ff", "#1e40af"))
        e.append(text(f"ra{i}", 320, y + 16, a, 16, "#374151", 220, 40))
        e.append(rect(f"r{i}c", 580, y, 480, 56, "#ffd8a8", "#c2410c"))
        e.append(text(f"rb{i}", 600, y + 16, b, 16, "#9a3412", 440, 40))
    e.append(rect("foot", 120, 520, 900, 56, "#fff3bf", "#a16207"))
    e.append(
        text(
            "ft",
            160,
            535,
            "两者都需持久化时依赖 2PC，避免 Redo 与 Binlog 单边落地",
            17,
            "#92400e",
            820,
            32,
        )
    )
    return scene(e)


def diagram_6_4_update_2pc_flow():
    e = []
    e.append(text("t0", 160, 16, "UPDATE 到提交：内存·日志·2PC 主路径", 21, "#1e40af", 640, 32))
    labels = [
        "Buffer Pool\n改脏页",
        "写 Undo",
        "Redo\nLog Buffer",
        "Prepare\nRedo 刷盘",
        "写 Binlog\n刷盘",
        "Redo\ncommit",
    ]
    xs = [40, 230, 420, 610, 800, 990]
    bw = 120
    for i, label in enumerate(labels):
        x = xs[i]
        if i < 3:
            fill, stroke = "#a5d8ff", "#1e40af"
        elif i < 5:
            fill, stroke = "#d0bfff", "#6d28d9"
        else:
            fill, stroke = "#b2f2bb", "#15803d"
        e.append(rect(f"s{i}", x, 100, bw, 92, fill, stroke))
        e.append(text(f"st{i}", x + 6, 118, label, 16, stroke, 108, 60))
        if i < len(labels) - 1:
            e.append(arrow(f"arr{i}", x + bw, 142, [[0, 0], [xs[i + 1] - x - bw, 0]], "#3b82f6"))
    e.append(text("wal", 200, 220, "此阶段 .ibd 数据文件仍可旧态，符合 WAL", 16, "#374151", 360, 28))
    e.append(rect("foot", 120, 270, 880, 56, "#fff3bf", "#a16207"))
    e.append(
        text(
            "ft",
            160,
            285,
            "组提交可合并多事务的 fsync；sync_binlog 等影响 Binlog 刷盘策略",
            16,
            "#92400e",
            800,
            32,
        )
    )
    return scene(e)


def diagram_6_4_crash_recovery():
    e = []
    e.append(text("t0", 200, 20, "崩溃恢复：Redo 见 prepare 时如何裁决", 22, "#1e40af", 520, 32))
    e.append(rect("in", 120, 90, 280, 72, "#a5d8ff", "#1e40af"))
    e.append(text("int", 150, 108, "Redo 中某事务处于 prepare", 17, "#1e40af", 220, 40))
    e.append(arrow("a0", 400, 120, [[0, 0], [80, 0]], "#3b82f6"))
    e.append(diamond("d", 500, 85, 220, 90))
    e.append(text("dt", 540, 115, "Binlog 有\n完整对应记录？", 16, "#92400e", 140, 44))
    e.append(rect("yes", 780, 70, 200, 64, "#b2f2bb", "#15803d"))
    e.append(text("yt", 800, 88, "是 → 引擎补成 commit", 16, "#15803d", 160, 36))
    e.append(rect("no", 780, 150, 200, 64, "#ffc9c9", "#b91c1c"))
    e.append(text("nt", 810, 168, "否 → 回滚", 16, "#b91c1c", 140, 28))
    e.append(arrow("ay", 720, 115, [[0, 0], [50, -25]], "#15803d"))
    e.append(arrow("an", 720, 145, [[0, 0], [50, 25]], "#b91c1c"))
    e.append(rect("foot", 140, 280, 880, 80, "#fff3bf", "#a16207"))
    e.append(
        text(
            "ft",
            170,
            295,
            "防止 InnoDB 与 Binlog 对同一事务「一边已持久、一边没有」的单边落地",
            17,
            "#92400e",
            820,
            48,
        )
    )
    return scene(e)


def main():
    BASE.mkdir(parents=True, exist_ok=True)
    files = {
        "6.1-环形日志与双指针.示意图.md": diagram_6_1_ring_buffer(),
        "6.1-WAL随机写与顺序写Redo.对比图.md": diagram_6_1_wal_compare(),
        "6.1-Redo内存到磁盘与刷盘策略.流程图.md": diagram_6_1_redo_flush_path(),
        "6.1-LSN与崩溃恢复.关系图.md": diagram_6_1_lsn_recovery(),
        "6.2-Insert与Update-Delete-Undo.对比图.md": diagram_6_2_undo_compare(),
        "6.2-History-List与Purge.流程图.md": diagram_6_2_purge_history(),
        "6.3-binlog_format三模式.对比图.md": diagram_6_3_binlog_format(),
        "6.3-层级与三种日志分工.层级图.md": diagram_6_3_layer_roles(),
        "6.3-Redo与Binlog对照.对比图.md": diagram_6_3_redo_binlog_compare(),
        "6.4-UPDATE执行到提交与2PC.流程图.md": diagram_6_4_update_2pc_flow(),
        "6.4-崩溃恢复prepare裁决.流程图.md": diagram_6_4_crash_recovery(),
    }
    for name, payload in files.items():
        (BASE / name).write_text(wrap_md(payload), encoding="utf-8")
    print("generated:", len(files), "files ->", BASE)


if __name__ == "__main__":
    main()
