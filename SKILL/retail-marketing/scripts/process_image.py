#!/usr/bin/env python3
"""
零售营销图片处理工具

功能：
  1. 下载远程图片（HTTP/HTTPS URL）
  2. 调整尺寸（缩放 + 居中裁剪）
  3. JPEG 压缩
  4. 输出 base64 字符串（可直接嵌入 HTML src）

用法：
  python process_image.py --input <path|url> --width 750 --output-base64
  python process_image.py --input <path|url> --width 180 --height 180 --quality 80 --output-base64
"""

import argparse
import base64
import io
import os
import sys
import urllib.request
from pathlib import Path


def download_image(url: str, output_dir: str) -> str:
    """下载远程图片，返回本地路径"""
    os.makedirs(output_dir, exist_ok=True)
    ext = os.path.splitext(url.split("?")[0])[1] or ".jpg"
    local_path = os.path.join(output_dir, f"downloaded_{abs(hash(url))}{ext}")

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    with open(local_path, "wb") as f:
        f.write(data)
    print(f"[download] {len(data)} bytes -> {local_path}")
    return local_path


def process_image(
    input_path: str,
    width: int | None,
    height: int | None,
    quality: int = 85,
    output_path: str | None = None,
    output_base64: bool = False,
) -> str | None:
    """
    处理图片：缩放、裁剪、压缩，可选输出文件或 base64。

    裁剪规则：cover 模式 — 等比缩放至覆盖目标区域，居中裁剪超出部分。
    如果只指定 width，则等比缩放，height 自动计算。
    """
    try:
        from PIL import Image, ImageFile
    except ImportError:
        print("ERROR: Pillow is not installed. Run: pip install Pillow", file=sys.stderr)
        sys.exit(1)

    # 容错：允许加载不完整的图片文件
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    img = Image.open(input_path).convert("RGB")
    orig_w, orig_h = img.size
    print(f"[process] original: {orig_w}x{orig_h}", file=sys.stderr)

    if width and height:
        # cover 模式：等比缩放到覆盖目标，居中裁剪
        scale = max(width / orig_w, height / orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)

        left = (new_w - width) // 2
        top = (new_h - height) // 2
        img = img.crop((left, top, left + width, top + height))
        print(f"[process] resize+crop ({scale:.2f}x) -> {width}x{height}", file=sys.stderr)
    elif width:
        # 仅指定宽度，等比缩放
        ratio = width / orig_w
        new_h = int(orig_h * ratio)
        img = img.resize((width, new_h), Image.LANCZOS)
        print(f"[process] resize ({ratio:.2f}x) -> {width}x{new_h}", file=sys.stderr)
    else:
        print("[process] no resize (width not specified)", file=sys.stderr)

    # 压缩输出
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    data = buf.getvalue()
    print(f"[process] JPEG q={quality}: {len(data)} bytes ({len(data)/1024:.1f} KB)", file=sys.stderr)

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(data)
        print(f"[process] saved -> {output_path}", file=sys.stderr)

    if output_base64:
        b64 = base64.b64encode(data).decode("ascii")
        result = f"data:image/jpeg;base64,{b64}"
        print(f"[process] base64 length: {len(result)} chars", file=sys.stderr)
        return result

    return None


def main():
    parser = argparse.ArgumentParser(description="零售营销图片处理工具")
    parser.add_argument("--input", required=True, help="输入图片路径或 URL")
    parser.add_argument("--width", type=int, default=None, help="目标宽度 (px)")
    parser.add_argument("--height", type=int, default=None, help="目标高度 (px)")
    parser.add_argument("--quality", type=int, default=85, help="JPEG 质量 (1-100, 默认 85)")
    parser.add_argument("--output", type=str, default=None, help="输出文件路径")
    parser.add_argument("--output-base64", action="store_true", help="输出 base64 字符串")
    parser.add_argument("--temp-dir", type=str, default=None,
                        help="下载远程图片的临时目录")

    args = parser.parse_args()

    # 判断输入是 URL 还是本地文件
    input_path = args.input
    if input_path.startswith(("http://", "https://")):
        temp_dir = args.temp_dir or os.path.join(os.getcwd(), ".temp-images")
        input_path = download_image(input_path, temp_dir)

    if not os.path.isfile(input_path):
        print(f"ERROR: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    result = process_image(
        input_path=input_path,
        width=args.width,
        height=args.height,
        quality=args.quality,
        output_path=args.output,
        output_base64=args.output_base64,
    )

    if result:
        # 输出 base64 到 stdout（供脚本调用者捕获），stdout 只输出纯数据
        print(result)


if __name__ == "__main__":
    main()
