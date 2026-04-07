import json
import os
import uuid

class ExcalidrawGenerator:
    def __init__(self, title):
        self.title = title
        self.elements = []
        self.appState = {"gridSize": None, "viewBackgroundColor": "#ffffff"}
        self.files = {}

    def _create_id(self):
        return str(uuid.uuid4())

    def add_rect(self, x, y, width, height, label="", stroke_color="#1e1e1e", bg_color="transparent", opacity=100, stroke_width=2, stroke_style="solid", roundness=3):
        rect_id = self._create_id()
        rect = {
            "id": rect_id, "type": "rectangle", "x": x, "y": y, "width": width, "height": height, "angle": 0,
            "strokeColor": stroke_color, "backgroundColor": bg_color, "fillStyle": "solid", "strokeWidth": stroke_width,
            "strokeStyle": stroke_style, "roughness": 1, "opacity": opacity, "groupIds": [], "roundness": {"type": roundness} if roundness else None,
            "seed": 123456, "version": 1, "isDeleted": False, "boundElements": None, "updated": 1, "link": None, "locked": False
        }
        self.elements.append(rect)
        if label:
            self.add_text(x + width/2, y + height/2, label, font_size=16, color=stroke_color, align="center")
        return rect_id

    def add_circle(self, x, y, radius, label="", stroke_color="#1e1e1e", bg_color="transparent", stroke_style="solid"):
        circ_id = self._create_id()
        circ = {
            "id": circ_id, "type": "ellipse", "x": x-radius, "y": y-radius, "width": radius*2, "height": radius*2, "angle": 0,
            "strokeColor": stroke_color, "backgroundColor": bg_color, "fillStyle": "solid", "strokeWidth": 2,
            "strokeStyle": stroke_style, "roughness": 1, "opacity": 100, "groupIds": [], "roundness": {"type": 2},
            "seed": 123456, "version": 1, "isDeleted": False, "boundElements": None, "updated": 1, "link": None, "locked": False
        }
        self.elements.append(circ)
        if label:
            self.add_text(x, y, label, font_size=14, color=stroke_color, align="center")
        return circ_id

    def add_text(self, x, y, text, font_size=16, color="#374151", align="center"):
        lines = text.split('\n')
        max_line_len = max(len(line) for line in lines)
        estimated_width = max_line_len * font_size * 0.95
        estimated_height = len(lines) * font_size * 1.25
        text_id = self._create_id()
        real_x = x - estimated_width / 2 if align == "center" else x
        real_y = y - estimated_height / 2 if align == "center" else y
        text_el = {
            "id": text_id, "type": "text", "x": real_x, "y": real_y, "width": estimated_width, "height": estimated_height, "angle": 0,
            "strokeColor": color, "backgroundColor": "transparent", "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
            "roughness": 1, "opacity": 100, "groupIds": [], "roundness": None, "seed": 123456, "version": 1, "isDeleted": False,
            "boundElements": None, "updated": 1, "link": None, "locked": False, "text": text, "fontSize": font_size,
            "fontFamily": 5, "textAlign": align, "verticalAlign": "middle", "containerId": None, "originalText": text,
            "autoResize": True, "lineHeight": 1.25
        }
        self.elements.append(text_el)
        return text_id

    def add_arrow(self, start_x, start_y, end_x, end_y, stroke_color="#3b82f6", stroke_style="solid", points=None):
        arrow_id = self._create_id()
        if points is None: points = [[0, 0], [end_x - start_x, end_y - start_y]]
        arrow = {
            "id": arrow_id, "type": "arrow", "x": start_x, "y": start_y, "width": abs(end_x - start_x), "height": abs(end_y - start_y),
            "angle": 0, "strokeColor": stroke_color, "backgroundColor": "transparent", "fillStyle": "solid", "strokeWidth": 2,
            "strokeStyle": stroke_style, "roughness": 1, "opacity": 100, "groupIds": [], "roundness": {"type": 2}, "seed": 123456,
            "version": 1, "isDeleted": False, "boundElements": None, "updated": 1, "link": None, "locked": False, "points": points,
            "lastCommittedPoint": None, "startBinding": None, "endBinding": None, "startArrowhead": None, "endArrowhead": "arrow"
        }
        self.elements.append(arrow)
        return arrow_id

    def save(self, path):
        data = {"type": "excalidraw", "version": 2, "source": "https://github.com/obsidian-excalidraw-plugin", "elements": self.elements, "appState": self.appState, "files": {}}
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write('---\nexcalidraw-plugin: parsed\ntags: [excalidraw]\n---\n')
            f.write('==⚠ Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠==\n\n# Excalidraw Data\n\n## Text Elements\n%%\n## Drawing\n```json\n')
            f.write(json.dumps(data, indent=2, ensure_ascii=False))
            f.write('\n```\n%%')

def gen_diagram1():
    gen = ExcalidrawGenerator("GC周期总览")
    gen.add_text(600, 50, "Go GC 周期总览", font_size=28, color="#1e40af")
    
    # Timeline
    gen.add_arrow(50, 450, 1150, 450, stroke_color="#374151")

    # Background partitions
    gen.add_rect(150, 150, 180, 450, "STW 层", bg_color="#ffc9c9", opacity=20, stroke_color="#991b1b")
    gen.add_rect(330, 150, 450, 450, "并发层", bg_color="#d3f9d8", opacity=20, stroke_color="#15803d")
    gen.add_rect(780, 150, 180, 450, "STW 层", bg_color="#ffc9c9", opacity=20, stroke_color="#991b1b")
    gen.add_rect(960, 150, 190, 450, "并发层", bg_color="#d3f9d8", opacity=20, stroke_color="#15803d")

    # Triggers
    gen.add_circle(100, 200, 40, "堆阈值", bg_color="#fff3bf")
    gen.add_circle(100, 300, 40, "定时器", bg_color="#fff3bf")
    gen.add_circle(100, 400, 40, "程序员\n手动", bg_color="#fff3bf")
    gen.add_arrow(140, 300, 175, 300)

    # Phases
    gen.add_rect(175, 300, 150, 100, "1. 准备 (STW)\n[相机图标]\n拍照定格 (找根)", bg_color="#ffffff")
    gen.add_rect(450, 300, 200, 100, "2. 标记 (并发)\n[雪球/扫雷图标]\n按图索骥 (找活对象)\n(Worker/Assist)", bg_color="#ffffff")
    gen.add_rect(800, 300, 150, 100, "3. 收尾 (STW)\n[结账单图标]\n清算尾账\n(wbBufFlush)", bg_color="#ffffff")
    gen.add_rect(1000, 300, 140, 100, "4. 清扫 (并发)\n[扫帚图标]\n抹零回库\n(Lazy Sweep)", bg_color="#ffffff")

    gen.add_text(600, 630, "为什么要停世界？拍照需静止，结算需断流。", font_size=18, color="#1e40af")
    gen.add_text(1070, 430, "清扫细则：\n- bgsweep 慢慢扫\n- 懒惰清扫(按需)\n- 整块空闲则 freeSpan", font_size=14)

    gen.save("d:/Note/Article/Go/内存管理/Excalidraw/GC周期总览.时间线.md")

def gen_diagram2():
    gen = ExcalidrawGenerator("并发协作与管制")
    gen.add_text(600, 50, "并发标记协作与 Assist (协助) 机制", font_size=28, color="#1e40af")
    
    gen.add_rect(100, 200, 200, 100, "Worker (后台工人)\n[#a5d8ff]\n25% CPU 专职扫描", bg_color="#a5d8ff", stroke_color="#1e40af")
    gen.add_text(450, 250, "Mutator (业务方)\n[不同色快]\n正在改指针/分内存", color="#15803d")
    gen.add_rect(400, 200, 40, 40, "", bg_color="#ffd8a8")
    gen.add_rect(450, 200, 40, 40, "", bg_color="#b2f2bb")
    
    gen.add_rect(300, 450, 400, 120, "Assist (协助机制)\n[限速杆 / ETC拦截器]\n逾期额度，强制劳役\n(强制去扫堆)", bg_color="#ffc9c9", stroke_color="#991b1b")
    gen.add_arrow(500, 300, 500, 450, stroke_color="#991b1b")

    gen.add_text(600, 620, "天平结构：分配速度 vs 扫描速度", font_size=20)
    gen.save("d:/Note/Article/Go/内存管理/Excalidraw/协作与Assist机制.关系图.md")

def gen_diagram3():
    gen = ExcalidrawGenerator("三色核心原理")
    gen.add_text(600, 50, "三色标记原理 (状态与位图映射)", font_size=40, color="#1e40af")
    
    # Pools
    gen.add_rect(100, 120, 1000, 550, "[背景图] 对象池", bg_color="#f8f9fa", stroke_style="dotted")

    # Status Definitions
    def add_node(x, y, label, bg, stroke_style="solid", desc="", mb=False):
        gen.add_rect(x, y, 160, 100, label, bg_color=bg, stroke_style=stroke_style)
        if mb:
            gen.add_rect(x + 130, y, 30, 20, "1", bg_color="#fff3bf", stroke_width=1)
        gen.add_text(x + 80, y + 130, desc, font_size=14)

    add_node(150, 200, "白: 颜色白色\n(生死未卜)", "#ffffff", stroke_style="dashed", desc="位图0, 不在队列\n(末尾仍白即垃圾)")
    add_node(450, 200, "灰: 颜色灰色\n正在排队", "#808080", mb=True, desc="位图已标 1\n正在工作队列中")
    add_node(750, 200, "黑: 颜色黑色\n确定存活", "#212529", stroke_style="solid", mb=True, desc="位图已标 1\n地址已出队列")

    # Transfer belt
    gen.add_rect(300, 450, 500, 80, "gcWork (传送带)\n[ 展示灰色小方块被 Worker 检查 ]", bg_color="#a5d8ff", stroke_color="#1e40af")
    gen.add_arrow(530, 300, 530, 450)
    gen.add_text(850, 550, "黄色小勾: markBits = 1", font_size=16)

    gen.save("d:/Note/Article/Go/内存管理/Excalidraw/三色标记原理.关系图.md")

def gen_diagram4():
    gen = ExcalidrawGenerator("写屏障拦截")
    gen.add_text(600, 50, "混合写屏障拦截逻辑 (防漏标三部曲)", font_size=28, color="#1e40af")

    # 1. Start
    gen.add_text(200, 150, "1. 初始状态", font_size=20)
    gen.add_rect(50, 200, 80, 50, "黑 A", bg_color="#212529", stroke_color="#000000")
    gen.add_rect(250, 200, 80, 50, "灰 B", bg_color="#808080")
    gen.add_rect(150, 350, 80, 50, "白 C", stroke_style="dashed")
    gen.add_arrow(290, 250, 220, 350)
    gen.add_text(290, 300, "B -> C", font_size=14)

    # 2. Consequences
    gen.add_text(550, 150, "2. 致命后果 (如果无屏障)", font_size=20, color="#991b1b")
    gen.add_arrow(650, 250, 580, 350, stroke_style="dashed", stroke_color="#991b1b") # B-C nil
    gen.add_text(650, 280, "nil", color="#991b1b")
    gen.add_arrow(430, 250, 520, 350, stroke_color="#f59e0b") # A-C link
    gen.add_text(550, 420, "后果：C 仅由黑 A 指向\n但 A 不重扫, C 会被误杀!", color="#991b1b")

    # 3. Intervention
    gen.add_text(950, 150, "3. 写屏障干预", font_size=20)
    gen.add_rect(800, 250, 300, 150, "拦截写操作!\n[自动喷漆枪]\n强行将 C 喷灰 (标红/标灰)\n送入 gcWork 队列", bg_color="#ffd8a8", stroke_color="#b45309")
    gen.add_arrow(700, 325, 800, 325)

    gen.add_text(600, 620, "宁上错杀多活一轮 (浮动垃圾)，绝不漏标导致崩溃。", font_size=18, color="#1e40af")
    gen.save("d:/Note/Article/Go/内存管理/Excalidraw/写屏障拦截.对比图.md")

if __name__ == "__main__":
    gen_diagram1()
    gen_diagram2()
    gen_diagram3()
    gen_diagram4()
    print("Generation Completed successfully.")
