import json
import sys
import os
import re
import pyperclip

from selenium.webdriver import Keys, ActionChains
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import wait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.relative_locator import locate_with
from selenium.webdriver.support.wait import WebDriverWait

from publisher.common_handler import wait_login
from utils.file_utils import read_file_with_footer, parse_front_matter, download_image, read_file_all_content
from utils.yaml_file_utils import read_jianshu, read_common, read_juejin
import time


def extract_image_paths(markdown_content, content_file):
    """从markdown内容中提取所有图片路径"""
    # 获取markdown文件所在目录
    content_dir = os.path.dirname(os.path.abspath(content_file))

    # 正则匹配markdown图片语法: ![alt](path)
    pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    matches = re.findall(pattern, markdown_content)

    image_paths = []
    for alt_text, img_path in matches:
        # 跳过http开头的网络图片
        if img_path.startswith('http'):
            continue

        # 处理URL编码的路径
        from urllib.parse import unquote
        img_path = unquote(img_path)

        # 如果是相对路径，转换为绝对路径
        if not os.path.isabs(img_path):
            img_path = os.path.join(content_dir, img_path)

        # 规范化路径
        img_path = os.path.normpath(img_path)

        if os.path.exists(img_path):
            image_paths.append((alt_text, img_path))
        else:
            print(f"警告: 图片文件不存在: {img_path}")

    return image_paths


def upload_images_to_editor(driver, image_paths):
    """上传图片到掘金编辑器"""
    if not image_paths:
        print("没有需要上传的本地图片")
        return

    print(f"\n开始上传 {len(image_paths)} 张图片...")

    # 找到编辑器区域
    try:
        editor = driver.find_element(By.XPATH, '//div[@class="CodeMirror-code"]')
    except:
        print("无法找到编辑器元素")
        return

    for idx, (alt_text, img_path) in enumerate(image_paths, 1):
        try:
            print(f"上传第 {idx}/{len(image_paths)} 张图片: {os.path.basename(img_path)}")

            # 在编辑器中查找图片占位符并定位
            # 方法1: 使用文件上传输入框（如果存在）
            try:
                # 掘金编辑器支持通过隐藏的input元素上传图片
                file_inputs = driver.find_elements(By.XPATH, '//input[@type="file" and @accept="image/*"]')
                if file_inputs:
                    file_input = file_inputs[0]
                    file_input.send_keys(img_path)
                    time.sleep(3)  # 等待上传完成
                    continue
            except:
                pass

            # 方法2: 模拟拖拽上传（备用方案）
            # 这需要JavaScript注入
            js_drop_file = """
            var target = arguments[0];
            var offsetX = arguments[1];
            var offsetY = arguments[2];
            var filePath = arguments[3];
            var fileName = arguments[4];

            // 创建一个DataTransfer对象
            var dataTransfer = new DataTransfer();
            // 注意：由于浏览器安全限制，无法直接从文件路径创建File对象
            // 这个方法在实际中可能不工作
            """

            print(f"  提示: 图片 {os.path.basename(img_path)} 可能需要手动上传")

        except Exception as e:
            print(f"上传图片失败 {img_path}: {e}")

    print("\n图片上传处理完成")


def juejin_publisher_enhanced(driver, content=None):
    """增强版掘金发布器，支持自动上传图片"""
    juejin_config = read_juejin()
    common_config = read_common()
    if content:
        common_config['content'] = content

    # 提取markdown文档的front matter内容：
    front_matter = parse_front_matter(common_config['content'])

    auto_publish = common_config['auto_publish']

    # 打开新标签页并切换到新标签页
    driver.switch_to.new_window('tab')

    # 浏览器实例现在可以被重用，进行你的自动化操作
    driver.get(juejin_config['site'])
    time.sleep(2)  # 等待2秒

    # 设置等待
    wait = WebDriverWait(driver, 5)

    # 写文章按钮
    wait_login(driver, By.CLASS_NAME, 'send-button')
    write_btn = driver.find_element(By.CLASS_NAME, 'send-button')
    write_btn.click()
    time.sleep(2)  # 等待3秒

    # 切换到新的tab
    driver.switch_to.window(driver.window_handles[-1])
    # 等待新标签页完成加载内容
    wait.until(EC.presence_of_element_located((By.XPATH, '//input[@placeholder="输入文章标题..."]')))

    # 提取图片路径
    markdown_content = read_file_all_content(common_config['content'])
    image_paths = extract_image_paths(markdown_content, common_config['content'])

    print(f"\n发现 {len(image_paths)} 张本地图片")
    for alt, path in image_paths:
        print(f"  - {os.path.basename(path)}")

    # 文章内容（先不粘贴图片路径的markdown）
    file_content = read_file_with_footer(common_config['content'])

    # 移除本地图片的markdown语法，只保留占位符
    temp_content = file_content
    for alt_text, img_path in image_paths:
        # 创建占位符
        placeholder = f"\n\n[图片占位: {os.path.basename(img_path)}]\n\n"
        # 匹配各种可能的图片引用格式
        patterns = [
            re.escape(f'![{alt_text}]({os.path.basename(img_path)})'),
            re.escape(f'![{alt_text}]({img_path})'),
        ]
        for pattern in patterns:
            temp_content = re.sub(pattern, placeholder, temp_content)

    # 掘金比较特殊，不能用元素赋值的方法，所以我们使用拷贝的方法
    cmd_ctrl = Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL
    # 将要粘贴的文本内容复制到剪贴板
    pyperclip.copy(temp_content)
    content_elem = driver.find_element(By.XPATH, '//div[@class="CodeMirror-code"]//span[@role="presentation"]')
    content_elem.click()
    # 模拟实际的粘贴操作
    action_chains = webdriver.ActionChains(driver)
    action_chains.key_down(cmd_ctrl).send_keys('v').key_up(cmd_ctrl).perform()
    time.sleep(3)

    # 文章标题
    title = driver.find_element(By.XPATH, '//input[@placeholder="输入文章标题..."]')
    title.clear()
    if 'title' in front_matter and front_matter['title']:
        title.send_keys(front_matter['title'])
    else:
        title.send_keys(common_config['title'])
    time.sleep(2)

    # 尝试上传图片
    print("\n准备上传图片...")
    print("提示: 由于浏览器安全限制，可能需要手动上传图片")
    print("请在编辑器中手动上传以下图片：")
    for idx, (alt, path) in enumerate(image_paths, 1):
        print(f"{idx}. {os.path.basename(path)} -> {path}")

    # 等待用户手动上传图片
    if image_paths:
        print("\n请手动将上述图片拖拽到编辑器对应位置...")
        print("完成后请按回车继续...")
        input()

    # 发布按钮
    publish_button = driver.find_element(By.XPATH, '//button[contains(text(), "发布")]')
    publish_button.click()
    time.sleep(2)

    # 发布文章 title
    title_label = driver.find_element(By.XPATH, '//div[contains(@class,"title") and contains(text(), "发布文章")]')

    # 分类
    category = juejin_config['category']
    if category:
        try:
            category_btn = driver.find_element(By.XPATH, f'//div[@class="form-item-content category-list"]//div[contains(text(), "{category}")]')
            category_btn.click()
            time.sleep(2)
        except:
            print(f"未找到分类: {category}")

    # 添加标签
    tag_btn = driver.find_element(By.XPATH, '//div[contains(@class,"byte-select__placeholder") and contains(text(), "请搜索添加标签")]')
    tag_btn.click()
    tags = juejin_config['tags']
    for tag in tags:
        # 使用复制粘贴的方式
        pyperclip.copy(tag)
        action_chains = webdriver.ActionChains(driver)
        action_chains.key_down(cmd_ctrl).send_keys('v').key_up(cmd_ctrl).perform()
        try:
            tag_element = driver.find_element(By.XPATH, f'//li[contains(@class,"byte-select-option") and contains(text(), "{tag}")]')
            tag_element.click()
            time.sleep(2)
        except Exception as e:
            print(f'没有找到标签：{tag}')

    title_label.click()

    # 文章封面
    if 'image' in front_matter and front_matter['image']:
        try:
            file_input = driver.find_element(By.XPATH, "//input[@type='file']")
            file_input.send_keys(download_image(front_matter['image']))
            time.sleep(2)
        except:
            print("封面图片上传失败")

    # 收录至专栏
    collections = juejin_config['collections']
    if collections:
        try:
            collection_button = driver.find_element(By.XPATH, '//div[contains(@class,"byte-select__placeholder") and contains(text(), "请搜索添加专栏，同一篇文章最多添加三个专栏")]')
            collection_button.click()
            for coll in collections:
                pyperclip.copy(coll)
                action_chains = webdriver.ActionChains(driver)
                action_chains.key_down(cmd_ctrl).send_keys('v').key_up(cmd_ctrl).perform()
                coll_element = driver.find_element(By.XPATH, f'//li[contains(@class,"byte-select-option") and contains(text(), "{coll}")]')
                coll_element.click()
                time.sleep(2)
            title_label.click()
        except:
            print(f"专栏添加失败")

    # 创作话题
    topic = juejin_config['topic']
    if topic:
        try:
            topic_btn = driver.find_element(By.XPATH, '//div[contains(@class,"byte-select__placeholder") and contains(text(), "请搜索添加话题，最多添加1个话题")]')
            topic_btn.click()
            pyperclip.copy(topic)
            action_chains = webdriver.ActionChains(driver)
            action_chains.key_down(cmd_ctrl).send_keys('v').key_up(cmd_ctrl).perform()
            topic_element = driver.find_element(By.XPATH, f'//li[@class="byte-select-option"]//span[contains(text(), "{topic}")]')
            topic_element.click()
            time.sleep(2)
            title_label.click()
        except:
            print("话题添加失败")

    # 编辑摘要
    if 'description' in front_matter and front_matter['description']:
        summary = front_matter['description']
    else:
        summary = common_config['summary']
    if summary:
        try:
            summary_ui = driver.find_element(By.XPATH, '//textarea[@class="byte-input__textarea"]')
            summary_ui.clear()
            summary_ui.send_keys(summary)
            time.sleep(2)
        except:
            print("摘要填写失败")

    # 最终发布
    if auto_publish:
        publish_button = driver.find_element(By.XPATH, '//button[contains(text(), "确定并发布")]')
        publish_button.click()
    else:
        print("\n准备就绪！请检查并手动点击'确定并发布'按钮")
