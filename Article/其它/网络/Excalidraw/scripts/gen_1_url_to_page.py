# -*- coding: utf-8 -*-
"""Generate Excalidraw: 图5 从 URL 到页面「六阶段全流程」-> Excalidraw/1/1-从URL到页面-全流程.md"""
import json
import random
from pathlib import Path

OUT_PATH = Path(r"D:\Note\Article\其它\网络\Excalidraw\1\1-从URL到页面-全流程.md")


def rid(n: int = 10) -> str:
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
        "strokeWidth": style == "dashed" and 1 or 2,
        "strokeStyle": style,
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "roundness": {"type": 3} if t == "rectangle" else ({"type": 2} if t == "arrow" else None),
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
    w = max(80, int(max((len(line) for line in lines), default=1) * size * 0.92))
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
    d["strokeWidth"] = 1
    d["roundness"] = None
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


def dashed_segment(x1, y1, x2, y2, color="#111827"):
    d = base_element("arrow", x1, y1, max(1, abs(x2 - x1)), max(1, abs(y2 - y1)), stroke=color, bg="transparent", style="dashed")
    d["strokeWidth"] = 1
    d.update(
        {
            "points": [[0, 0], [x2 - x1, y2 - y1]],
            "lastCommittedPoint": [x2 - x1, y2 - y1],
            "startArrowhead": None,
            "endArrowhead": None,
        }
    )
    return d


def phase_title(x: float, y: float, w: float, label: str, bg: str, stroke: str):
    e = [
        base_element("rectangle", x, y, w, 34, stroke=stroke, bg=bg),
        text_element(x + 10, y + 6, label, 17, stroke),
    ]
    return e


def build_diagram():
    e = []
    e.append(base_element("rectangle", 36, 42, 1128, 718, stroke="#94a3b8", bg="#f8fafc"))

    e.append(text_element(320, 12, "从 URL 到页面：六阶段全流程「时间线概览」", 22, "#1e40af"))

    # column bands: row1
    c1, c2, c3 = 48, 438, 828
    cw = 372
    r1_top, r1_body = 52, 92
    r2_top, r2_body = 412, 452

    # ---- row 1 titles ----
    e += phase_title(c1, r1_top, cw, "1 DNS · URL 解析", "#dbe4ff", "#1e40af")
    e += phase_title(c2, r1_top, cw, "2 TCP 三次握手 + TLS", "#e5dbff", "#6d28d9")
    e += phase_title(c3, r1_top, cw, "3 封装 · 经网关发出", "#ffd8a8", "#c2410c")

    # vertical dashed between cols row1
    e.append(dashed_segment(c1 + cw + 6, 48, c1 + cw + 6, 392))
    e.append(dashed_segment(c2 + cw + 6, 48, c2 + cw + 6, 392))

    # ---- row 2 titles ----
    e += phase_title(c1, r2_top, cw, "4 路由逐跳「LPM」", "#c3fae8", "#0f766e")
    e += phase_title(c2, r2_top, cw, "5 服务端解包与 HTTP 响应", "#b2f2bb", "#166534")
    e += phase_title(c3, r2_top, cw, "6 渲染子资源 + TCP 挥手", "#fff3bf", "#b45309")

    e.append(dashed_segment(c1 + cw + 6, 408, c1 + cw + 6, 748))
    e.append(dashed_segment(c2 + cw + 6, 408, c2 + cw + 6, 748))

    # horizontal dashed between rows
    e.append(dashed_segment(44, 404, 1156, 404))

    # === 1 DNS ===
    e.append(text_element(c1 + 8, r1_body, "https", 16, "#15803d"))
    e.append(text_element(c1 + 52, r1_body, "://www.example.com", 16, "#1e40af"))
    e.append(
        text_element(
            c1 + 8,
            r1_body + 28,
            "浏览器 → 进程/浏览器缓存 → OS 缓存 · hosts\n→ 递归解析器 → 根 → TLD → 权威 → 得到 IP",
            16,
            "#374151",
        )
    )
    e.append(base_element("rectangle", c1 + 8, r1_body + 92, 340, 44, stroke="#1e40af", bg="#a5d8ff"))
    e.append(text_element(c1 + 22, r1_body + 104, "多级未命中才走完整迭代/递归链", 16, "#1e3a8a"))
    e.append(base_element("rectangle", c1 + 8, r1_body + 150, 110, 40, stroke="#166534", bg="#b2f2bb"))
    e.append(text_element(c1 + 38, r1_body + 160, "IP", 18, "#166534"))
    e.append(line_arrow(c1 + 118, r1_body + 170, c1 + 200, r1_body + 170, "#3b82f6"))

    # === 2 TCP + TLS ===
    bx = c2 + 14
    by = r1_body
    for i, lab in enumerate(["SYN", "SYN+ACK", "ACK"]):
        e.append(base_element("rectangle", bx + i * 112, by, 96, 34, stroke="#6d28d9", bg="#d0bfff"))
        e.append(text_element(bx + i * 112 + 18, by + 8, lab, 16, "#5b21b6"))
        if i < 2:
            e.append(line_arrow(bx + i * 112 + 96, by + 17, bx + (i + 1) * 112, by + 17, "#6d28d9"))
    e.append(text_element(bx, by + 44, "客户端 ephemeral 端口 → 服务器 :443", 16, "#374151"))
    e.append(base_element("rectangle", bx, by + 72, 340, 86, stroke="#92400e", bg="#fff3bf"))
    e.append(
        text_element(
            bx + 12,
            by + 82,
            "TLS 叠在已建 TCP 上：证书链校验\n→ 协商密钥 → 之后 HTTP 走密文",
            16,
            "#92400e",
        )
    )
    e.append(text_element(bx, by + 168, "HTTPS：先 TCP，再 TLS，再应用请求", 16, "#1e40af"))

    # === 3 encapsulation + ARP ===
    ox = c3 + 56
    oy = r1_body + 6
    e.append(base_element("rectangle", ox, oy, 210, 200, stroke="#c2410c", bg="#ffe8cc"))
    e.append(base_element("rectangle", ox + 14, oy + 18, 182, 164, stroke="#0f766e", bg="#c3fae8"))
    e.append(base_element("rectangle", ox + 32, oy + 40, 146, 120, stroke="#1e3a8a", bg="#a5d8ff"))
    e.append(base_element("rectangle", ox + 52, oy + 68, 106, 72, stroke="#166534", bg="#b2f2bb"))
    e.append(text_element(ox + 62, oy + 88, "HTTP Request", 16, "#166534"))
    e.append(text_element(ox + 38, oy + 46, "TCP 段·端口·序号", 16, "#1e3a8a"))
    e.append(text_element(ox + 22, oy + 24, "IP 数据报·源目 IP", 16, "#0f766e"))
    e.append(text_element(ox + 8, oy + 6, "以太网帧·目的 MAC=网关", 16, "#9a3412"))
    e.append(text_element(c3 + 8, r1_body + 218, "ARP：问默认网关 MAC → 帧头可填", 16, "#9a3412"))
    e.append(text_element(c3 + 8, r1_body + 244, "目标 IP 已知，下一跳二层地址靠 ARP", 16, "#57534e"))

    # === 4 routing ===
    rx = c1 + 20
    ry = r2_body + 6
    nw, nh, gap = 58, 36, 10
    nodes = [("本机", 0), ("网关", nw + gap), ("R1", 2 * (nw + gap)), ("R2", 3 * (nw + gap)), ("机房", 4 * (nw + gap))]
    for name, nx in nodes:
        e.append(base_element("rectangle", rx + nx, ry, nw, nh, stroke="#0f766e", bg="#c3fae8"))
        e.append(text_element(rx + nx + 6, ry + 8, name, 16, "#0f766e"))
    for i in range(len(nodes) - 1):
        x0 = rx + nodes[i][1] + nw
        x1 = rx + nodes[i + 1][1]
        e.append(line_arrow(x0, ry + nh // 2, x1, ry + nh // 2, "#0f766e"))
    e.append(text_element(rx, ry + 52, "每跳：拆帧看 IP · 查路由表 · 重写 MAC", 16, "#374151"))
    e.append(text_element(rx, ry + 78, "旁注：目的 MAC 变 · 目的 IP 通常不变「无 NAT」", 16, "#57534e"))
    e.append(base_element("rectangle", rx + 200, ry - 36, 88, 28, stroke="#ca8a04", bg="#fff3bf"))
    e.append(text_element(rx + 212, ry - 30, "LPM", 16, "#b45309"))

    # === 5 server === 自上向下：HTTP→…→物理，与 Nginx 并排避免重叠
    sx = c2 + 16
    sy = r2_body + 8
    layer_labels = ["HTTP 请求", "TCP 段", "IP 数据报", "以太网帧", "物理 比特"]
    hbox, vgap = 32, 5
    e.append(text_element(sx + 4, sy - 4, "入站：自下而上解封装「图示自上向下」", 16, "#374151"))
    ly = sy + 18
    for i, lab in enumerate(layer_labels):
        e.append(base_element("rectangle", sx, ly, 178, hbox, stroke="#166534", bg="#dcfce7"))
        e.append(text_element(sx + 8, ly + 6, lab, 16, "#166534"))
        if i < len(layer_labels) - 1:
            e.append(line_arrow(sx + 89, ly + hbox, sx + 89, ly + hbox + vgap, "#64748b"))
        ly += hbox + vgap
    ngx, ngy = sx + 192, sy + 18
    e.append(base_element("rectangle", ngx, ngy, 136, hbox, stroke="#1e40af", bg="#dbeafe"))
    e.append(text_element(ngx + 12, ngy + 6, "Nginx / Tomcat", 16, "#1e40af"))
    e.append(line_arrow(sx + 178, ngy + hbox // 2, ngx, ngy + hbox // 2, "#3b82f6"))
    rb = sy + 18 + (len(layer_labels) - 1) * (hbox + vgap)
    e.append(line_arrow(ngx + 68, ngy + hbox, ngx + 68, ngy + hbox + 36, "#2563eb", "dashed"))
    e.append(line_arrow(ngx + 68, ngy + hbox + 36, sx + 89, rb + hbox + 28, "#2563eb", "dashed"))
    e.append(text_element(sx + 4, rb + hbox + 22, "HTTP Response 回程「封包路径大致镜像」", 16, "#2563eb"))

    # === 6 render ===
    tx = c3 + 10
    ty = r2_body + 8
    e.append(base_element("rectangle", tx, ty, 110, 40, stroke="#b45309", bg="#fff3bf"))
    e.append(text_element(tx + 22, ty + 10, "HTML", 16, "#b45309"))
    e.append(line_arrow(tx + 110, ty + 20, tx + 130, ty + 20, "#b45309"))
    e.append(base_element("rectangle", tx + 130, ty, 150, 40, stroke="#b45309", bg="#fff3bf"))
    e.append(text_element(tx + 148, ty + 10, "DOM / CSSOM", 16, "#b45309"))
    e.append(line_arrow(tx + 280, ty + 20, tx + 300, ty + 20, "#b45309"))
    e.append(base_element("rectangle", tx + 300, ty, 150, 40, stroke="#b45309", bg="#fff3bf"))
    e.append(text_element(tx + 312, ty + 8, "渲染 + 子资源", 16, "#b45309"))
    e.append(base_element("rectangle", tx + 60, ty + 70, 100, 34, stroke="#64748b", bg="#f1f5f9"))
    e.append(text_element(tx + 78, ty + 78, "JS", 16, "#475569"))
    e.append(base_element("rectangle", tx + 180, ty + 70, 100, 34, stroke="#64748b", bg="#f1f5f9"))
    e.append(text_element(tx + 198, ty + 78, "CSS", 16, "#475569"))
    e.append(base_element("rectangle", tx + 300, ty + 70, 100, 34, stroke="#64748b", bg="#f1f5f9"))
    e.append(text_element(tx + 312, ty + 78, "图片等", 16, "#475569"))
    e.append(line_arrow(tx + 160, ty + 40, tx + 110, ty + 70, "#64748b", "dashed"))
    e.append(line_arrow(tx + 205, ty + 40, tx + 230, ty + 70, "#64748b", "dashed"))
    e.append(line_arrow(tx + 375, ty + 40, tx + 350, ty + 70, "#64748b", "dashed"))
    e.append(
        text_element(
            tx,
            ty + 112,
            "Keep-Alive：连接复用；空闲或关闭时 FIN/ACK 四次挥手「简写」",
            16,
            "#57534e",
        )
    )

    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin",
        "elements": e,
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    }


def to_markdown(diagram: dict) -> str:
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
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(to_markdown(build_diagram()), encoding="utf-8", newline="\n")
    print(f"[OK] {OUT_PATH}")


if __name__ == "__main__":
    main()
