import os
import re
import sys

def convert_relative_to_absolute(md_file):
    """将markdown文件中的相对路径图片转换为绝对路径"""

    # 获取markdown文件所在目录的绝对路径
    md_dir = os.path.dirname(os.path.abspath(md_file))

    # 读取markdown文件
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 正则匹配markdown图片语法: ![alt](path)
    # 匹配不以http开头的路径（即本地路径）
    pattern = r'!\[([^\]]*)\]\((?!http)([^)]+)\)'

    def replace_path(match):
        alt_text = match.group(1)
        relative_path = match.group(2)

        # URL解码（处理 %20 等编码）
        from urllib.parse import unquote
        decoded_path = unquote(relative_path)

        # 构建绝对路径
        abs_path = os.path.abspath(os.path.join(md_dir, decoded_path))

        # 转换为Windows路径格式（使用反斜杠）
        abs_path = abs_path.replace('/', '\\')

        print(f"转换: {relative_path} -> {abs_path}")

        return f'![{alt_text}]({abs_path})'

    # 替换所有匹配的图片路径
    new_content = re.sub(pattern, replace_path, content)

    # 创建新文件
    base_name = os.path.splitext(md_file)[0]
    new_file = f"{base_name}_absolute.md"

    with open(new_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"\n新文件已创建: {new_file}")
    return new_file

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python convert_image_paths.py <markdown文件路径>")
        sys.exit(1)

    md_file = sys.argv[1]
    if not os.path.exists(md_file):
        print(f"文件不存在: {md_file}")
        sys.exit(1)

    convert_relative_to_absolute(md_file)
