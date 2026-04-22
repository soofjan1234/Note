import json
from pathlib import Path


ROOT = Path(r"D:\Note\Article\其它\网络\Excalidraw\2")


def _base_elem(elem_type: str, x: float, y: float, w: float, h: float, seed: int):
    return {
        "id": f"el_{seed}",
        "type": elem_type,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "angle": 0,
        "strokeColor": "#374151",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "roundness": {"type": 3} if elem_type == "rectangle" else None,
        "seed": seed,
        "version": 1,
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
    }


def rect(seed: int, x: float, y: float, w: float, h: float, bg: str, stroke: str):
    el = _base_elem("rectangle", x, y, w, h, seed)
    el["backgroundColor"] = bg
    el["strokeColor"] = stroke
    return el


def text(seed: int, x: float, y: float, content: str, size: int = 18, color: str = "#374151"):
    lines = content.split("\n")
    max_len = max(len(i) for i in lines)
    width = max(80, max_len * size * 0.95)
    height = len(lines) * size * 1.25
    el = _base_elem("text", x, y, width, height, seed)
    el.update(
        {
            "strokeColor": color,
            "backgroundColor": "transparent",
            "strokeWidth": 1,
            "roundness": None,
            "text": content,
            "originalText": content,
            "fontSize": size,
            "fontFamily": 5,
            "textAlign": "left",
            "verticalAlign": "top",
            "containerId": None,
            "autoResize": True,
            "lineHeight": 1.25,
        }
    )
    return el


def arrow(seed: int, x1: float, y1: float, x2: float, y2: float, color: str = "#3b82f6"):
    el = _base_elem("arrow", x1, y1, abs(x2 - x1), abs(y2 - y1), seed)
    el.update(
        {
            "strokeColor": color,
            "roundness": {"type": 2},
            "points": [[0, 0], [x2 - x1, y2 - y1]],
            "lastCommittedPoint": None,
            "startBinding": None,
            "endBinding": None,
            "startArrowhead": None,
            "endArrowhead": "arrow",
        }
    )
    return el


def md_wrap(diagram: dict) -> str:
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


def write_diagram(file_name: str, elements: list):
    ROOT.mkdir(parents=True, exist_ok=True)
    diagram = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin",
        "elements": elements,
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    }
    target = ROOT / file_name
    target.write_text(md_wrap(diagram), encoding="utf-8")
    print(f"[OK] {target}")


def diagram_ws_handshake():
    e = []
    s = 100
    e += [text(s, 340, 20, "WebSocket 握手全流程", 28, "#1e40af")]
    s += 1

    # top comparison
    e += [rect(s, 60, 90, 480, 180, "#dbe4ff", "#1e40af")]
    s += 1
    e += [rect(s, 560, 90, 480, 180, "#fff3bf", "#b45309")]
    s += 1
    e += [text(s, 90, 120, "URL 方案层\nws:// / wss://\n入口约定", 20, "#1e40af")]
    s += 1
    e += [text(s, 590, 120, "握手报文层\n首包是 HTTP/1.1 Upgrade\n报文形态", 20, "#92400e")]
    s += 1
    e += [arrow(s, 545, 180, 555, 180, "#f59e0b")]
    s += 1
    e += [text(s, 460, 145, "并不矛盾", 16, "#f59e0b")]
    s += 1

    # timeline
    e += [text(s, 70, 320, "客户端", 18, "#1e40af"), text(s + 1, 940, 320, "服务端", 18, "#15803d")]
    s += 2
    e += [arrow(s, 140, 350, 900, 350, "#3b82f6")]
    s += 1
    e += [text(s, 170, 370, "1) TCP 连接\nwss 先 TLS", 16)]
    s += 1
    e += [text(s, 360, 370, "2) GET + Upgrade", 16)]
    s += 1
    e += [text(s, 550, 370, "3) 101 Switching Protocols\n+ Sec-WebSocket-Accept", 16, "#b45309")]
    s += 1
    e += [text(s, 795, 370, "4) 进入 WS 帧双向通信", 16)]
    s += 1
    e += [rect(s, 60, 450, 980, 120, "#b2f2bb", "#15803d")]
    s += 1
    e += [text(s, 90, 485, "关键点：101 后，同一连接不再是一问一答式 HTTP。", 18, "#166534")]
    return e


def diagram_mqtt_vs_mq():
    e = []
    s = 300
    e += [text(s, 300, 20, "MQTT vs 消息队列", 28, "#1e40af")]
    s += 1
    e += [rect(s, 60, 80, 470, 520, "#dbe4ff", "#1e40af")]
    s += 1
    e += [rect(s, 560, 80, 470, 520, "#e5dbff", "#6d28d9")]
    s += 1
    e += [text(s, 90, 110, "MQTT（设备入口）", 22, "#1e40af")]
    s += 1
    e += [text(s, 590, 110, "消息队列（后端处理）", 22, "#6d28d9")]
    s += 1
    e += [text(s, 90, 170, "位置：网络边缘\n侧重点：连接管理、弱网\n典型：IoT 设备、车联网\n语义：Topic、QoS、LWT\n优势：头小、低功耗", 18)]
    s += 1
    e += [text(s, 590, 170, "位置：数据中心内部\n侧重点：持久化、削峰、回放\n典型：微服务异步任务\n语义：队列、分区、消费组\n优势：吞吐与可靠处理", 18)]
    s += 1
    e += [rect(s, 60, 620, 970, 130, "#c3fae8", "#0f766e")]
    s += 1
    e += [text(s, 95, 655, "组合链路：设备 -> MQTT Broker -> MQ/流平台 -> 微服务", 22, "#0f766e")]
    return e


def diagram_ssh_auth():
    e = []
    s = 500
    e += [text(s, 290, 20, "SSH 场景与密钥认证", 28, "#1e40af")]
    s += 1
    e += [rect(s, 60, 80, 470, 240, "#dbe4ff", "#1e40af")]
    s += 1
    e += [text(s, 90, 110, "常用场景", 22, "#1e40af")]
    s += 1
    e += [text(s, 90, 160, "1) Xshell/PuTTY 远程运维\n2) scp 传发布包与配置\n3) Git over SSH\n4) CI/CD 自动部署", 18)]
    s += 1

    e += [rect(s, 560, 80, 470, 560, "#fff3bf", "#b45309")]
    s += 1
    e += [text(s, 590, 110, "公钥认证流程", 22, "#92400e")]
    s += 1
    e += [text(s, 590, 160, "1) 客户端生成密钥对\n2) 公钥放 authorized_keys\n3) 服务端发送 challenge\n4) 客户端私钥签名\n5) 服务端公钥验签通过", 18)]
    s += 1

    e += [rect(s, 60, 360, 470, 280, "#ffc9c9", "#b91c1c")]
    s += 1
    e += [text(s, 90, 390, "口令认证 vs 密钥认证", 22, "#b91c1c")]
    s += 1
    e += [text(s, 90, 440, "口令：直接交密码，易被爆破/撞库。\n密钥：私钥不上传，只做签名。\n建议：私钥加 passphrase；禁 root 直登。", 18)]
    return e


def diagram_mqtt_bike():
    e = []
    s = 700
    e += [text(s, 170, 20, "MQTT 在共享单车弱网开锁中的优势", 26, "#1e40af")]
    s += 1
    section_y = [80, 250, 420, 590]
    titles = ["1) 心跳与重连", "2) QoS 2 Exactly Once", "3) LWT 失联感知", "4) 流量成本"]
    bodies = [
        "HTTP：超时后用户卡顿。\nMQTT：断线后快速重连，\n刚恢复就能接住开锁指令。",
        "PUBLISH -> PUBREC -> PUBREL -> PUBCOMP\n弱网下也避免漏开或重复执行。",
        "车辆异常掉线时，Broker 自动发布\ncars/status/{id}=offline，\n后端立即标灰，不必高频轮询。",
        "HTTP 每次带较重首部；\nMQTT 固定头最小 2 字节。\n百万车分钟级上报，省流量显著。",
    ]
    colors = [("#dbe4ff", "#1e40af"), ("#fff3bf", "#b45309"), ("#ffd8a8", "#c2410c"), ("#b2f2bb", "#15803d")]

    for i in range(4):
        bg, stroke = colors[i]
        y = section_y[i]
        e += [rect(s, 60, y, 980, 140, bg, stroke)]
        s += 1
        e += [text(s, 90, y + 18, titles[i], 22, stroke)]
        s += 1
        e += [text(s, 90, y + 58, bodies[i], 18, "#374151")]
        s += 1
    return e


def main():
    write_diagram("2.3-WebSocket握手全流程.md", diagram_ws_handshake())
    write_diagram("2.3-MQTT与消息队列区别.md", diagram_mqtt_vs_mq())
    write_diagram("2.3-SSH场景与密钥认证.md", diagram_ssh_auth())
    write_diagram("2.3-MQTT共享单车弱网开锁机制.md", diagram_mqtt_bike())


if __name__ == "__main__":
    main()
