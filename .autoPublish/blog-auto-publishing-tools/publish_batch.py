import os
import traceback

import selenium
from selenium import webdriver

from publisher.alicloud_publisher import alicloud_publisher
from publisher.cnblogs_publisher import cnblogs_publisher
from publisher.csdn_publisher import csdn_publisher
from publisher.cto51_publisher import cto51_publisher
from publisher.infoq_publisher import infoq_publisher
from publisher.jianshu_publisher import jianshu_publisher
from publisher.juejin_publisher import juejin_publisher
from publisher.mpweixin_publisher import mpweixin_publisher
from publisher.oschina_publisher import oschina_publisher
from publisher.segmentfault_publisher import segmentfault_publisher
from publisher.toutiao_publisher import toutiao_publisher
from publisher.txcloud_publisher import txcloud_publisher
from publisher.zhihu_publisher import zhihu_publisher
from utils.yaml_file_utils import read_common, set_common_override, clear_common_override


all_sites = [
    "csdn",
    "jianshu",
    "juejin",
    "segmentfault",
    "oschina",
    "cnblogs",
    "zhihu",
    "cto51",
    "infoq",
    "txcloud",
    "alicloud",
    "toutiao",
    "mpweixin",
]


def build_driver(common_config):
    driver_type = common_config["driver_type"]
    if driver_type == "chrome":
        service = selenium.webdriver.chrome.service.Service(common_config["service_location"])
        options = selenium.webdriver.chrome.options.Options()
        options.page_load_strategy = "normal"
        options.add_experimental_option("debuggerAddress", common_config["debugger_address"])
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
        raise ValueError(f"不支持的 driver_type: {driver_type}")

    driver.implicitly_wait(10)
    return driver


def publish_to_platform(platform, driver, content=None):
    try:
        globals()[platform + "_publisher"](driver, content)
    except Exception:
        print(platform, "got error")
        traceback.print_exc()


def publish_to_all_enabled_platforms(driver, content, common_config):
    for platform in all_sites:
        if platform in common_config["enable"] and common_config["enable"][platform]:
            publish_to_platform(platform, driver, content)


def normalize_queue_item(item, fallback):
    if isinstance(item, str):
        return {
            "content": item,
            "title": fallback.get("title", ""),
            "summary": fallback.get("summary", ""),
        }
    if isinstance(item, dict):
        return {
            "content": item.get("content", ""),
            "title": item.get("title", fallback.get("title", "")),
            "summary": item.get("summary", fallback.get("summary", "")),
        }
    return {"content": "", "title": fallback.get("title", ""), "summary": fallback.get("summary", "")}


if __name__ == "__main__":
    common_config = read_common()
    publish_queue = common_config.get("publish_queue", [])
    if not publish_queue:
        print("common.yaml 里没有 publish_queue，示例：")
        print("publish_queue:")
        print("  - content: d:/Note/Article/Go/内存管理/内存分配.md")
        print("    title: Go 内存管理（1）：内存分配")
        print("    summary: 你的摘要...")
        raise SystemExit(1)

    driver = build_driver(common_config)
    try:
        total = len(publish_queue)
        for idx, raw_item in enumerate(publish_queue, start=1):
            item = normalize_queue_item(raw_item, common_config)
            content = item["content"]
            if not content:
                print(f"[{idx}/{total}] 跳过：content 为空")
                continue
            if not os.path.exists(content):
                print(f"[{idx}/{total}] 跳过：文件不存在 -> {content}")
                continue

            print(f"\n[{idx}/{total}] 准备发布：{content}")
            set_common_override(
                {
                    "title": item["title"],
                    "content": content,
                    "summary": item["summary"],
                }
            )
            publish_to_all_enabled_platforms(driver, content, common_config)

            if idx < total:
                cmd = input("按 Enter 发布下一篇，输入 q 退出：").strip().lower()
                if cmd == "q":
                    print("用户主动停止批量发布。")
                    break
    finally:
        clear_common_override()
        driver.quit()
