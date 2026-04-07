"""
图片上传辅助工具
通过剪贴板实现图片自动上传
"""
import os
import time
from PIL import Image
import io
import win32clipboard
from selenium.webdriver import Keys, ActionChains


def send_image_to_clipboard(image_path):
    """将图片发送到剪贴板"""
    try:
        # 打开图片
        image = Image.open(image_path)

        # 转换为RGB模式（如果需要）
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # 创建一个字节流来保存图片
        output = io.BytesIO()
        image.save(output, 'BMP')
        data = output.getvalue()[14:]  # BMP文件头是14字节
        output.close()

        # 将图片数据发送到剪贴板
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()

        return True
    except Exception as e:
        print(f"复制图片到剪贴板失败: {e}")
        return False


def upload_image_via_clipboard(driver, image_path):
    """
    通过剪贴板上传图片到编辑器

    Args:
        driver: Selenium WebDriver实例
        image_path: 图片文件路径
    """
    try:
        print(f"正在上传: {os.path.basename(image_path)}")

        # 1. 将图片复制到剪贴板
        if not send_image_to_clipboard(image_path):
            return False

        # 2. 重新获取编辑器元素并点击确保焦点
        from selenium.webdriver.common.by import By
        try:
            # 尝试多种方式找到编辑器
            editor = None
            try:
                editor = driver.find_element(By.CSS_SELECTOR, '.CodeMirror-code')
            except:
                try:
                    editor = driver.find_element(By.CSS_SELECTOR, '.CodeMirror-scroll')
                except:
                    editor = driver.find_element(By.CSS_SELECTOR, '.CodeMirror')

            editor.click()
            time.sleep(0.5)
        except Exception as e:
            print(f"警告: 无法定位编辑器，尝试直接粘贴: {e}")

        # 3. 粘贴图片 (Ctrl+V)
        cmd_ctrl = Keys.COMMAND if os.name == 'darwin' else Keys.CONTROL
        action_chains = ActionChains(driver)
        action_chains.key_down(cmd_ctrl).send_keys('v').key_up(cmd_ctrl).perform()

        # 4. 等待上传完成
        time.sleep(3)

        print(f"✓ 已上传: {os.path.basename(image_path)}")
        return True

    except Exception as e:
        print(f"✗ 上传失败 {os.path.basename(image_path)}: {e}")
        return False


if __name__ == "__main__":
    # 测试
    test_image = r"D:\Note\.autoPublish\article\image.png"
    if os.path.exists(test_image):
        send_image_to_clipboard(test_image)
        print("图片已复制到剪贴板")
    else:
        print("测试图片不存在")
