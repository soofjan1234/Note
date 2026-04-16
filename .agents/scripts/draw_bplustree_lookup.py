import json
import uuid
import os

def create_rect(x, y, w, h, bg, stroke, text):
    fontSize = 18
    lines = text.split('\n')
    text_w = max(len(l.encode('utf-8')) * fontSize * 0.5 for l in lines)
    text_h = len(lines) * fontSize * 1.25
    
    rect_id = str(uuid.uuid4())
    text_id = str(uuid.uuid4())
    
    rect = {
        "id": rect_id, "type": "rectangle",
        "x": x, "y": y, "width": w, "height": h,
        "strokeColor": stroke, "backgroundColor": bg,
        "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
        "roughness": 1, "opacity": 100, "groupIds": [], "roundness": {"type": 3},
        "seed": 1, "version": 1, "isDeleted": False, "boundElements": None, "updated": 1, "link": None, "locked": False
    }
    
    txt = {
        "id": text_id, "type": "text",
        "x": x + (w - text_w)/2, "y": y + (h - text_h)/2,
        "width": text_w, "height": text_h,
        "strokeColor": stroke, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
        "roughness": 1, "opacity": 100, "groupIds": [], "roundness": None,
        "seed": 1, "version": 1, "isDeleted": False, "boundElements": None, "updated": 1, "link": None, "locked": False,
        "text": text, "fontSize": fontSize, "fontFamily": 5, "textAlign": "center", "verticalAlign": "middle",
        "containerId": None, "originalText": text, "autoResize": True, "lineHeight": 1.25
    }
    return [rect, txt], rect_id

def create_diamond(x, y, w, h, bg, stroke, text):
    fontSize = 18
    lines = text.split('\n')
    text_w = max(len(l.encode('utf-8')) * fontSize * 0.5 for l in lines)
    text_h = len(lines) * fontSize * 1.25
    
    dia_id = str(uuid.uuid4())
    text_id = str(uuid.uuid4())
    
    dia = {
        "id": dia_id, "type": "diamond",
        "x": x, "y": y, "width": w, "height": h,
        "strokeColor": stroke, "backgroundColor": bg,
        "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
        "roughness": 1, "opacity": 100, "groupIds": [], "roundness": {"type": 3},
        "seed": 1, "version": 1, "isDeleted": False, "boundElements": None, "updated": 1, "link": None, "locked": False
    }
    
    txt = {
        "id": text_id, "type": "text",
        "x": x + (w - text_w)/2, "y": y + (h - text_h)/2,
        "width": text_w, "height": text_h,
        "strokeColor": stroke, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
        "roughness": 1, "opacity": 100, "groupIds": [], "roundness": None,
        "seed": 1, "version": 1, "isDeleted": False, "boundElements": None, "updated": 1, "link": None, "locked": False,
        "text": text, "fontSize": fontSize, "fontFamily": 5, "textAlign": "center", "verticalAlign": "middle",
        "containerId": None, "originalText": text, "autoResize": True, "lineHeight": 1.25
    }
    return [dia, txt], dia_id

def create_arrow(start_x, start_y, points, stroke="#3b82f6", text=None):
    arr_id = str(uuid.uuid4())
    arr = {
        "id": arr_id, "type": "arrow",
        "x": start_x, "y": start_y, "width": abs(points[-1][0]), "height": abs(points[-1][1]),
        "strokeColor": stroke, "backgroundColor": "transparent", "fillStyle": "solid",
        "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1, "opacity": 100,
        "groupIds": [], "roundness": {"type": 2}, "seed": 1, "version": 1, "isDeleted": False,
        "boundElements": None, "updated": 1, "link": None, "locked": False,
        "points": points, "lastCommittedPoint": None, "startBinding": None, "endBinding": None,
        "startArrowhead": None, "endArrowhead": "arrow"
    }
    els = [arr]
    
    if text:
        fontSize = 16
        lines = text.split('\n')
        text_w = max(len(l.encode('utf-8')) * fontSize * 0.5 for l in lines)
        text_h = len(lines) * fontSize * 1.25
        
        mx = start_x + points[len(points)//2][0]
        my = start_y + points[len(points)//2][1]
        
        txt_id = str(uuid.uuid4())
        txt = {
            "id": txt_id, "type": "text",
            "x": mx - text_w/2, "y": my - text_h/2 - 10,
            "width": text_w, "height": text_h,
            "strokeColor": stroke, "backgroundColor": "transparent", "fillStyle": "solid",
            "strokeWidth": 1, "strokeStyle": "solid", "roughness": 1, "opacity": 100,
            "groupIds": [], "roundness": None, "seed": 1, "version": 1, "isDeleted": False,
            "boundElements": None, "updated": 1, "link": None, "locked": False,
            "text": text, "fontSize": fontSize, "fontFamily": 5, "textAlign": "center", "verticalAlign": "middle",
            "containerId": None, "originalText": text, "autoResize": True, "lineHeight": 1.25
        }
        els.append(txt)
    return els

elements = []

startX = 400
startY = 50

# Title
els, _ = create_rect(280, 20, 0, 0, "transparent", "#1e40af", "B+树导航：自内存全局Hash到页内二分寻址")
for e in els:
    if e['type'] == 'rectangle':
        continue
    e['fontSize'] = 24
    elements.append(e)

# Step 1: Input node
w, h = 240, 60
currY = 100
els, id_start = create_rect(startX, currY, w, h, "#a5d8ff", "#1e40af", "路径解析获得节点：\n(space_id, page_no)")
elements.extend(els)

# Step 2: Global Hash
currY += 100
els, id_hash = create_rect(startX, currY, w, h, "#d0bfff", "#5f3dc4", "1. 从全局 Hash 表定位页\n(Buffer Pool 自适应哈希)")
elements.extend(els)
elements.extend(create_arrow(startX + w/2, currY - 100 + h, [[0,0], [0, 40]], stroke="#3b82f6"))

# Step 3: Diamond (In Buffer Pool?)
currY += 120
els, id_cond = create_diamond(startX-20, currY, w+40, h+30, "#fff3bf", "#f08c00", "命中 Hash 表？\n(页在内存中)")
elements.extend(els)
elements.extend(create_arrow(startX + w/2, currY - 120 + h, [[0,0], [0, 60]], stroke="#3b82f6"))

# Split paths
# YES PATH (Left)
yesX = startX - 220
yesY = currY + 120
els, id_yes = create_rect(yesX, yesY, 200, 60, "#b2f2bb", "#2b8a3e", "获取内存物理指针\n(宏观导航完毕)")
elements.extend(els)
elements.extend(create_arrow(startX-20, currY + (h+30)/2, [[0,0], [-100, 0], [-100, yesY - (currY + (h+30)/2)]], stroke="#2b8a3e", text="是 (命中内存缓存)"))

# NO PATH (Right)
noX = startX + 260
noY = currY + 100
els, id_no1 = create_rect(noX, noY, 220, 60, "#ffc9c9", "#c92a2a", "2. 缺页兜底：触发磁盘 I/O\n强制加载 16KB 对应页")
elements.extend(els)
elements.extend(create_arrow(startX-20 + w+40, currY + (h+30)/2, [[0,0], [140, 0], [140, noY - (currY + (h+30)/2)]], stroke="#c92a2a", text="否 (缺页中断)"))

noY2 = noY + 90
els, id_no2 = create_rect(noX, noY2, 220, 60, "#ffd8a8", "#e8590c", "放入 LRU 链表预热\n并将其地址登记到 Hash")
elements.extend(els)
elements.extend(create_arrow(noX + 110, noY + 60, [[0,0], [0, 30]], stroke="#c92a2a"))

# Merge Node: 16KB in memory
currY += 280
w2 = 280
els, id_mem = create_rect(startX - 20, currY, w2, 70, "#c3fae8", "#0ca678", "中观结束点：已准备好目标\n16KB 页实体 (驻在内存中)")
elements.extend(els)
# yes path merging
elements.extend(create_arrow(yesX + 100, yesY + 60, [[0,0], [0, 100], [startX - yesX + 40, 100]], stroke="#2b8a3e"))
# no path merging
elements.extend(create_arrow(noX + 110, noY2 + 60, [[0,0], [0, 70], [-(noX - startX + 40), 70]], stroke="#e8590c"))


# Step 4: Access Page Directory
currY += 120
els, id_dir = create_rect(startX - 20, currY, w2, h, "#dbe4ff", "#3b82f6", "3. 微观加速：读取该页页尾\nPage Directory (页目录槽)")
elements.extend(els)
elements.extend(create_arrow(startX - 20 + w2/2, currY - 120 + 70, [[0,0], [0, 50]], stroke="#3b82f6"))

# Step 5: Binary Search
currY += 110
els, id_bin = create_rect(startX - 20, currY, w2, 70, "#eebefa", "#a61e4d", "拿着目标主键，对目录槽分组\n进行『二分查找法』")
elements.extend(els)
elements.extend(create_arrow(startX - 20 + w2/2, currY - 110 + h, [[0,0], [0, 50]], stroke="#3b82f6"))

# Step 6: Target located
currY += 120
els, id_done = create_rect(startX - 20, currY, w2, 60, "#b2f2bb", "#2b8a3e", "微观定位！瞬间锁定目标数据行")
elements.extend(els)
elements.extend(create_arrow(startX - 20 + w2/2, currY - 120 + 70, [[0,0], [0, 50]], stroke="#2b8a3e"))

out = {
  "type": "excalidraw",
  "version": 2,
  "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin",
  "elements": elements,
  "appState": { "gridSize": None, "viewBackgroundColor": "#ffffff" },
  "files": {}
}

md_content = """---
excalidraw-plugin: parsed
tags: [excalidraw]
---
==⚠  Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠== You can decompress Drawing data with the command palette: 'Decompress current Excalidraw file'. For more info check in plugin settings under 'Saving'

# Excalidraw Data

## Text Elements
%%
## Drawing
```json
""" + json.dumps(out, indent=2) + """
```
%%
"""

os.makedirs('/Users/Zhuanz/projects/OtherWS/Note/Article/MySQL/Excalidraw', exist_ok=True)
with open('/Users/Zhuanz/projects/OtherWS/Note/Article/MySQL/Excalidraw/3.1-InnoDB.页面查找流程图.md', 'w') as f:
    f.write(md_content)

