import os
import re
import sys
import time
from urllib.parse import unquote, urlparse

import pyperclip
import selenium
from selenium import webdriver
from selenium.webdriver import Keys, ActionChains
from selenium.common.exceptions import (
    InvalidSessionIdException,
    NoSuchElementException,
    NoSuchWindowException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from utils.file_utils import (
    read_file_with_footer,
    parse_front_matter,
    download_image,
    list_files,
    read_head,
    write_to_file,
)
from utils.yaml_file_utils import read_common, read_juejin

try:
    from utils.image_upload_helper import send_image_to_clipboard
    CLIPBOARD_IMAGE_AVAILABLE = True
except Exception:
    CLIPBOARD_IMAGE_AVAILABLE = False


TITLE_PLACEHOLDER = "\u8f93\u5165\u6587\u7ae0\u6807\u9898..."
# 部分页面 placeholder 文案可能微调，作兜底匹配
TITLE_PLACEHOLDER_XPATH_FUZZY = '//input[contains(@placeholder, "\u6587\u7ae0\u6807\u9898") or contains(@placeholder, "\u6807\u9898")]'
PUBLISH_TEXT = "\u53d1\u5e03"
PUBLISH_ARTICLE_TEXT = "\u53d1\u5e03\u6587\u7ae0"
TAG_PLACEHOLDER = "\u8bf7\u641c\u7d22\u6dfb\u52a0\u6807\u7b7e"
COLLECTION_PLACEHOLDER = "\u8bf7\u641c\u7d22\u6dfb\u52a0\u4e13\u680f"
TOPIC_PLACEHOLDER = "\u8bf7\u641c\u7d22\u6dfb\u52a0\u8bdd\u9898"
CONFIRM_PUBLISH_TEXT = "\u786e\u5b9a\u5e76\u53d1\u5e03"


# 解析时尝试的图片扩展名（按顺序，找到即用）
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp")


def resolve_obsidian_image_embeds(markdown_content, content_file):
    """
    将 Obsidian 图片语法 ![[xxx]] 转换为标准 Markdown 图片语法，指向 Excalidraw 目录下的图片。
    会尝试 .png / .jpg / .jpeg / .gif / .webp；若都不存在仍会替换为 Excalidraw/xxx.png 并写回，便于后续补图。
    """
    content_file = os.path.abspath(os.path.normpath(content_file))
    content_dir = os.path.dirname(content_file)
    pattern = re.compile(r'!\[\[([^\]]+)\]\]')

    def replace(match):
        raw = match.group(1).strip()

        if "#" in raw:
            raw = raw.split("#", 1)[0].strip()

        alt_text = raw
        if "|" in raw:
            path_part, alt_part = raw.split("|", 1)
            path_part = path_part.strip()
            alt_text = alt_part.strip() or path_part
        else:
            path_part = raw

        if os.path.dirname(path_part):
            rel_dir = os.path.dirname(path_part)
            base_name = os.path.basename(path_part)
        else:
            rel_dir = "Excalidraw"
            base_name = path_part

        # 图片名 = [[]] 内内容 + .png，只有已以已知图片扩展名结尾时才保持原样（避免 splitext 把 "Sync.Map.基础概念" 截成 Sync.Map）
        base_lower = base_name.lower()
        if any(base_lower.endswith(ext) for ext in IMAGE_EXTENSIONS):
            file_name = base_name
        else:
            file_name = base_name + ".png"
        rel_path = os.path.join(rel_dir, file_name)

        image_path = os.path.normpath(os.path.join(content_dir, rel_path))

        if not os.path.exists(image_path):
            # 尝试其他扩展名时，用 [[]] 内的 base_name 加扩展名（不含已有扩展名）
            base_for_other_ext = base_name
            if any(base_lower.endswith(ext) for ext in IMAGE_EXTENSIONS):
                base_for_other_ext = base_name[: -len(next(ext for ext in IMAGE_EXTENSIONS if base_lower.endswith(ext)))]
            for e in IMAGE_EXTENSIONS:
                if e == ".png":
                    continue
                candidate = os.path.normpath(os.path.join(content_dir, rel_dir, base_for_other_ext + e))
                if os.path.exists(candidate):
                    image_path = candidate
                    rel_path = os.path.join(rel_dir, base_for_other_ext + e)
                    break
            if not os.path.exists(image_path):
                print(f"Warning: image not found (will still replace in file): {image_path}")

        # 写回 md 时用正斜杠，便于跨平台
        rel_path_md = rel_path.replace("\\", "/")
        return f"![{alt_text}]({rel_path_md})"

    return pattern.sub(replace, markdown_content)


def build_content_with_placeholders(markdown_content, content_file):
    content_dir = os.path.dirname(os.path.abspath(content_file))
    pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    images = []
    counter = 0

    def replace(match):
        nonlocal counter
        alt_text = match.group(1)
        raw_path = match.group(2).strip()

        if raw_path.startswith("<") and raw_path.endswith(">"):
            raw_path = raw_path[1:-1].strip()

        if " " in raw_path:
            raw_path = raw_path.split(" ")[0]

        if raw_path.startswith("http://") or raw_path.startswith("https://"):
            return match.group(0)

        image_path = unquote(raw_path)
        if not os.path.isabs(image_path):
            image_path = os.path.join(content_dir, image_path)
        image_path = os.path.normpath(image_path)

        if not os.path.exists(image_path):
            print(f"Warning: image not found: {image_path}")
            return match.group(0)

        counter += 1
        placeholder = f"[[[IMAGE_{counter}:{os.path.basename(image_path)}]]]"
        images.append(
            {
                "placeholder": placeholder,
                "path": image_path,
                "alt": alt_text,
            }
        )
        return placeholder

    new_content = pattern.sub(replace, markdown_content)
    return new_content, images


def get_codemirror_instance(driver):
    script = """
    var cmEl = document.querySelector('.CodeMirror');
    if (!cmEl) { return null; }
    return cmEl.CodeMirror || null;
    """
    return driver.execute_script(script)


def focus_codemirror(driver):
    script = """
    var cmEl = document.querySelector('.CodeMirror');
    if (!cmEl || !cmEl.CodeMirror) { return false; }
    cmEl.CodeMirror.focus();
    return true;
    """
    return driver.execute_script(script)


def select_placeholder(driver, placeholder):
    script = """
    var placeholder = arguments[0];
    var cmEl = document.querySelector('.CodeMirror');
    if (!cmEl || !cmEl.CodeMirror) { return -1; }
    var cm = cmEl.CodeMirror;
    var text = cm.getValue();
    var idx = text.indexOf(placeholder);
    if (idx === -1) { return -1; }
    var from = cm.posFromIndex(idx);
    var to = cm.posFromIndex(idx + placeholder.length);
    cm.setSelection(from, to);
    cm.focus();
    return idx;
    """
    return driver.execute_script(script, placeholder)


def remove_placeholder(driver, placeholder):
    script = """
    var placeholder = arguments[0];
    var cmEl = document.querySelector('.CodeMirror');
    if (!cmEl || !cmEl.CodeMirror) { return false; }
    var cm = cmEl.CodeMirror;
    var text = cm.getValue();
    var idx = text.indexOf(placeholder);
    if (idx === -1) { return false; }
    var from = cm.posFromIndex(idx);
    var to = cm.posFromIndex(idx + placeholder.length);
    cm.replaceRange('', from, to);
    // Collapse excessive blank lines to avoid double-blank around inserted images.
    var cleaned = cm.getValue().replace(/\\n{3,}/g, '\\n\\n');
    if (cleaned !== cm.getValue()) {
        cm.setValue(cleaned);
    }
    return true;
    """
    return driver.execute_script(script, placeholder)


def paste_image_from_clipboard(driver, image_path):
    if not CLIPBOARD_IMAGE_AVAILABLE:
        print("Clipboard image upload not available. Missing dependencies.")
        return False

    if not send_image_to_clipboard(image_path):
        return False

    cmd_ctrl = Keys.COMMAND if sys.platform == "darwin" else Keys.CONTROL
    ActionChains(driver).key_down(cmd_ctrl).send_keys("v").key_up(cmd_ctrl).perform()
    time.sleep(3)
    return True


def upload_image_via_file_input(driver, image_path):
    try:
        file_inputs = driver.find_elements(By.XPATH, '//input[@type="file" and @accept="image/*"]')
        if not file_inputs:
            return False
        file_inputs[0].send_keys(image_path)
        time.sleep(3)
        return True
    except Exception:
        return False


def insert_images(driver, images):
    if not images:
        return

    for idx, item in enumerate(images, 1):
        placeholder = item["placeholder"]
        image_path = item["path"]

        print(f"Inserting image {idx}/{len(images)}: {os.path.basename(image_path)}")
        position = select_placeholder(driver, placeholder)
        if position == -1:
            print(f"Placeholder not found in editor: {placeholder}")
            continue

        focus_codemirror(driver)
        if paste_image_from_clipboard(driver, image_path):
            # Remove placeholder in case the editor inserted image on a new line.
            remove_placeholder(driver, placeholder)
            time.sleep(2)
            continue

        if upload_image_via_file_input(driver, image_path):
            remove_placeholder(driver, placeholder)
            time.sleep(2)
            continue

        print(f"Failed to upload image: {image_path}")


def init_driver(common_config):
    driver_type = common_config["driver_type"]

    if driver_type == "chrome":
        service = selenium.webdriver.chrome.service.Service(common_config["service_location"])
        debugger_address = common_config["debugger_address"]
        options = selenium.webdriver.chrome.options.Options()
        options.page_load_strategy = "normal"
        options.add_experimental_option("debuggerAddress", debugger_address)
        driver = webdriver.Chrome(service=service, options=options)
    elif driver_type == "firefox":
        service = selenium.webdriver.firefox.service.Service(
            common_config["service_location"],
            service_args=["--marionette-port", "2828", "--connect-existing"],
        )
        options = selenium.webdriver.firefox.options.Options()
        options.page_load_strategy = "normal"
        driver = webdriver.Firefox(service=service, options=options)
    else:
        raise ValueError(f"Unsupported driver_type: {driver_type}")

    driver.implicitly_wait(10)
    return driver


def _urls_same_page(current: str, expected: str) -> bool:
    """
    是否为同一页面：scheme、host、path 一致（path 去尾 /；忽略 query、fragment）。
    用于判断当前标签是否已是创作者中心，避免重复 driver.get。
    """
    a, b = urlparse((current or "").strip()), urlparse((expected or "").strip())
    if a.scheme.lower() != b.scheme.lower() or a.netloc.lower() != b.netloc.lower():
        return False
    pa = (a.path or "/").rstrip("/").lower()
    pb = (b.path or "/").rstrip("/").lower()
    return pa == pb


def switch_to_creator_tab_if_exists(driver, site: str) -> bool:
    """
    若任一标签的 URL 已与 site 视为同一页，则切换过去并返回 True。
    队列第二篇起可复用上一篇留在后台的创作者中心标签，少开新标签、少一次整页加载。
    """
    handles = list(driver.window_handles)
    if not handles:
        return False
    fallback = handles[-1]
    for h in reversed(handles):
        try:
            driver.switch_to.window(h)
            if _urls_same_page(driver.current_url, site):
                return True
        except Exception:
            continue
    try:
        driver.switch_to.window(fallback)
    except Exception:
        pass
    return False


def open_new_tab_safe(driver):
    """
    Open a new tab robustly across Selenium/Chrome edge cases.
    """
    try:
        # Ensure current context is a live window.
        handles = driver.window_handles
        if handles:
            driver.switch_to.window(handles[-1])
    except Exception:
        pass

    try:
        driver.switch_to.new_window("tab")
        return
    except Exception:
        pass

    before_handles = list(driver.window_handles)
    if not before_handles:
        raise NoSuchWindowException("no window handles available")
    driver.execute_script("window.open('about:blank','_blank');")
    WebDriverWait(driver, 5).until(lambda d: len(d.window_handles) > len(before_handles))
    driver.switch_to.window(driver.window_handles[-1])


def _find_title_input_locator():
    """精确 placeholder + 模糊 placeholder，兼容掘金小幅改版。"""
    return (
        (By.XPATH, f'//input[@placeholder="{TITLE_PLACEHOLDER}"]'),
        (By.XPATH, TITLE_PLACEHOLDER_XPATH_FUZZY),
    )


def _wait_title_on_current_tab(driver, per_tab_wait: WebDriverWait):
    for by, loc in _find_title_input_locator():
        try:
            per_tab_wait.until(EC.presence_of_element_located((by, loc)))
            return True
        except TimeoutException:
            continue
    return False


def find_title_input_element(driver):
    """发布流程里填标题：精确 placeholder 优先，否则模糊匹配。"""
    for by, loc in _find_title_input_locator():
        try:
            return driver.find_element(by, loc)
        except NoSuchElementException:
            continue
    raise NoSuchElementException("未找到文章标题输入框")


def goto_juejin_editor(driver, site, wait, max_retry=2):
    """
    Open creator home and enter editor page robustly.

    第二篇及以后常见问题：点击「写文章」后可能**同标签**进入编辑器，也可能**新开标签**；
    若始终 switch 到最后一个句柄，可能仍停在创作者首页。这里会枚举新开的标签，
    并在当前及所有标签中查找标题输入框。
    """
    per_tab = WebDriverWait(driver, 12)
    for attempt in range(1, max_retry + 1):
        # 已在创作者中心则不再整页跳转，减少「重复打开」感；若无 send-button 再强制刷新
        if not _urls_same_page(driver.current_url, site):
            driver.get(site)
            time.sleep(2)
        else:
            time.sleep(0.3)
        try:
            wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "send-button")))
        except TimeoutException:
            driver.get(site)
            time.sleep(2)
            wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "send-button")))
        btn = driver.find_element(By.CLASS_NAME, "send-button")
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
        except Exception:
            pass
        time.sleep(0.3)
        handles_before = set(driver.window_handles)
        try:
            btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", btn)
        time.sleep(1.5)

        handles_after = driver.window_handles
        new_tabs = [h for h in handles_after if h not in handles_before]

        # 优先：本次点击新开的标签（从后往前，一般是最后一个新开的）
        try_order = list(reversed(new_tabs)) if new_tabs else [handles_after[-1]]
        # 兜底：其余标签也扫一遍（多标签残留时，避免切错）
        for h in handles_after:
            if h not in try_order:
                try_order.append(h)

        seen = set()
        ordered = []
        for h in try_order:
            if h not in seen:
                seen.add(h)
                ordered.append(h)

        for h in ordered:
            try:
                driver.switch_to.window(h)
            except Exception:
                continue
            if _wait_title_on_current_tab(driver, per_tab):
                return

        if attempt < max_retry:
            print(f"Editor not ready, retry entering editor ({attempt}/{max_retry})...")
            continue
        raise TimeoutException(
            "掘金编辑器未就绪：已点击 send-button，但在当前浏览器所有标签中都未找到文章标题输入框。"
        )


def publish_juejin_with_images(driver, content=None, title_override=None, summary_override=None):
    juejin_config = read_juejin()
    common_config = read_common()
    if content:
        common_config["content"] = content

    front_matter = parse_front_matter(common_config["content"])
    auto_publish = common_config["auto_publish"]

    wait = WebDriverWait(driver, 10)
    site = juejin_config["site"]
    # 优先复用已有「创作者中心」标签，避免每篇都新开标签再 get 一次（减少重复打开）
    if switch_to_creator_tab_if_exists(driver, site):
        print("Reusing existing tab: creator home (same URL as configured site).")
    else:
        open_new_tab_safe(driver)
    goto_juejin_editor(driver, site, wait, max_retry=2)

    content_file_path = os.path.abspath(os.path.normpath(common_config["content"]))

    # 读取原始文件，解析 ![[xxx]] 为 ![](Excalidraw/xxx.png) 并写回本地
    try:
        with open(content_file_path, "r", encoding="UTF-8") as f:
            raw_content = f.read()
    except OSError as e:
        print(f"Error reading content file: {content_file_path}\n{e}")
        return

    resolved_content = resolve_obsidian_image_embeds(raw_content, content_file_path)
    if resolved_content != raw_content:
        try:
            write_to_file(resolved_content, content_file_path)
            print(f"Updated local file (replaced ![[...]] with image paths): {content_file_path}")
        except OSError as e:
            print(f"Error writing content file: {content_file_path}\n{e}")

    file_content = read_file_with_footer(content_file_path)
    content_with_placeholders, images = build_content_with_placeholders(
        file_content, content_file_path
    )

    if images:
        print(f"Found {len(images)} local images to upload.")

    cmd_ctrl = Keys.COMMAND if sys.platform == "darwin" else Keys.CONTROL
    pyperclip.copy(content_with_placeholders)
    content_elem = driver.find_element(
        By.XPATH, '//div[@class="CodeMirror-code"]//span[@role="presentation"]'
    )
    content_elem.click()
    ActionChains(driver).key_down(cmd_ctrl).send_keys("v").key_up(cmd_ctrl).perform()
    time.sleep(3)

    title = find_title_input_element(driver)
    title.clear()
    if front_matter and front_matter.get("title"):
        title.send_keys(front_matter["title"])
    elif title_override:
        title.send_keys(title_override)
    else:
        title.send_keys(common_config["title"])
    time.sleep(2)

    insert_images(driver, images)

    publish_button = driver.find_element(By.XPATH, f'//button[contains(text(), "{PUBLISH_TEXT}")]')
    publish_button.click()
    time.sleep(2)

    title_label = driver.find_element(
        By.XPATH, f'//div[contains(@class,"title") and contains(text(), "{PUBLISH_ARTICLE_TEXT}")]'
    )

    category = juejin_config["category"]
    if category:
        try:
            category_btn = driver.find_element(
                By.XPATH,
                f'//div[@class="form-item-content category-list"]//div[contains(text(), "{category}")]',
            )
            category_btn.click()
            time.sleep(2)
        except Exception:
            print(f"Category not found: {category}")

    tag_btn = driver.find_element(
        By.XPATH,
        f'//div[contains(@class,"byte-select__placeholder") and contains(text(), "{TAG_PLACEHOLDER}")]',
    )
    tag_btn.click()
    tags = juejin_config["tags"]
    for tag in tags:
        pyperclip.copy(tag)
        ActionChains(driver).key_down(cmd_ctrl).send_keys("v").key_up(cmd_ctrl).perform()
        try:
            tag_element = driver.find_element(
                By.XPATH,
                f'//li[contains(@class,"byte-select-option") and contains(text(), "{tag}")]',
            )
            tag_element.click()
            time.sleep(2)
        except Exception:
            print(f"Tag not found: {tag}")

    title_label.click()

    if front_matter and front_matter.get("image"):
        try:
            file_input = driver.find_element(By.XPATH, "//input[@type='file']")
            file_input.send_keys(download_image(front_matter["image"]))
            time.sleep(2)
        except Exception:
            print("Cover image upload failed.")

    collections = juejin_config["collections"]
    if collections:
        try:
            collection_button = driver.find_element(
                By.XPATH,
                f'//div[contains(@class,"byte-select__placeholder") and contains(text(), "{COLLECTION_PLACEHOLDER}")]',
            )
            collection_button.click()
            for coll in collections:
                pyperclip.copy(coll)
                ActionChains(driver).key_down(cmd_ctrl).send_keys("v").key_up(cmd_ctrl).perform()
                coll_element = driver.find_element(
                    By.XPATH,
                    f'//li[contains(@class,"byte-select-option") and contains(text(), "{coll}")]',
                )
                coll_element.click()
                time.sleep(2)
            title_label.click()
        except Exception:
            print("Failed to set collection.")

    topic = juejin_config["topic"]
    if topic:
        try:
            topic_btn = driver.find_element(
                By.XPATH,
                f'//div[contains(@class,"byte-select__placeholder") and contains(text(), "{TOPIC_PLACEHOLDER}")]',
            )
            topic_btn.click()
            pyperclip.copy(topic)
            ActionChains(driver).key_down(cmd_ctrl).send_keys("v").key_up(cmd_ctrl).perform()
            topic_element = driver.find_element(
                By.XPATH,
                f'//li[@class="byte-select-option"]//span[contains(text(), "{topic}")]',
            )
            topic_element.click()
            time.sleep(2)
            title_label.click()
        except Exception:
            print("Failed to set topic.")

    if front_matter and front_matter.get("description"):
        summary = front_matter["description"]
    elif summary_override:
        summary = summary_override
    else:
        summary = common_config["summary"]

    if summary:
        try:
            summary_ui = driver.find_element(By.XPATH, '//textarea[@class="byte-input__textarea"]')
            summary_ui.clear()
            summary_ui.send_keys(summary)
            time.sleep(2)
        except Exception:
            print("Failed to set summary.")

    if auto_publish:
        publish_button = driver.find_element(
            By.XPATH, f'//button[contains(text(), "{CONFIRM_PUBLISH_TEXT}")]'
        )
        publish_button.click()
    else:
        print("Ready to publish. Please review and click confirm publish.")


def choose_content(common_config):
    content_dir = common_config["content_dir"]
    file_list = list_files(content_dir, ".md")
    if not file_list:
        print("No markdown files found in content_dir.")
        return None

    print("Select an article to publish (enter index):")
    for index, file_name in enumerate(file_list):
        print(f"{index}: {os.path.basename(file_name)}")
    last_published = read_head("last_published.txt")
    if last_published:
        print(f"Last published: {last_published.strip()}")

    choice = input("Choice: ").strip()
    if not choice.isdigit():
        print("Invalid input.")
        return None
    choice_index = int(choice)
    if 0 <= choice_index < len(file_list):
        return file_list[choice_index]
    print("Invalid selection.")
    return None


def save_last_published_file_name(filename):
    write_to_file(filename, "last_published.txt")


def normalize_queue_item(item):
    if isinstance(item, str):
        return {"content": item, "title": "", "summary": ""}
    if isinstance(item, dict):
        return {
            "content": item.get("content", ""),
            "title": item.get("title", ""),
            "summary": item.get("summary", ""),
        }
    return {"content": "", "title": "", "summary": ""}


def main():
    common_config = read_common()
    driver = init_driver(common_config)
    try:
        queue = common_config.get("publish_queue", [])
        if queue:
            total = len(queue)
            for idx, raw_item in enumerate(queue, start=1):
                item = normalize_queue_item(raw_item)
                content = item["content"]
                if not content:
                    print(f"[{idx}/{total}] skipped: empty content")
                    continue
                if not os.path.exists(content):
                    print(f"[{idx}/{total}] skipped: file not found -> {content}")
                    continue

                print(f"\n[{idx}/{total}] publishing: {content}")
                try:
                    publish_juejin_with_images(
                        driver,
                        content,
                        title_override=item["title"],
                        summary_override=item["summary"],
                    )
                except (InvalidSessionIdException, NoSuchWindowException, WebDriverException) as e:
                    # Chrome debug session may be closed/restarted between articles.
                    err_msg = str(e).lower()
                    if (
                        "invalid session id" in err_msg
                        or "not connected to devtools" in err_msg
                        or "no such window" in err_msg
                        or "web view not found" in err_msg
                    ):
                        print("Browser window/session disconnected. Reconnecting to Chrome debug session and retrying...")
                        try:
                            driver.quit()
                        except Exception:
                            pass
                        driver = init_driver(common_config)
                        publish_juejin_with_images(
                            driver,
                            content,
                            title_override=item["title"],
                            summary_override=item["summary"],
                        )
                    else:
                        raise
                save_last_published_file_name(os.path.basename(content))

                if idx < total:
                    next_cmd = input("Press Enter to publish next, or input q to quit: ").strip().lower()
                    if next_cmd == "q":
                        print("Stopped by user.")
                        break
        else:
            content = common_config.get("content")
            if not content:
                content = choose_content(common_config)
            if not content:
                print("No article selected. Exiting.")
                return
            publish_juejin_with_images(driver, content)
            save_last_published_file_name(os.path.basename(content))
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
