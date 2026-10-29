#!/usr/bin/env python3
"""Standalone PaddleOCR for nexus agent — powered by RapidOCR + ONNX Runtime.

A self-contained OCR executable that extracts text from images without
requiring PaddlePaddle. Uses PP-OCRv6 models via ONNX Runtime.

Usage examples:
  paddle-ocr.exe --image screenshot.png
  paddle-ocr.exe --image photo.jpg --lang en --output text
  paddle-ocr.exe --image doc.png --output json --show-boxes
  echo C:\\path\\to\\img.png | paddle-ocr.exe --stdin
"""
import argparse
import json
import os
import sys
import traceback

__version__ = "1.0.0"
__engine__ = "RapidOCR + ONNX Runtime"
__model__ = "PP-OCRv6"

BANNER = f"""paddle-ocr v{__version__} ({__engine__})
Model: {__model__} | Built-in: Chinese, English, Japanese, Korean, etc.

Usage:
  paddle-ocr.exe --image <path> [options]
  paddle-ocr.exe --image screenshot.png
  paddle-ocr.exe --image photo.jpg --lang en --output text
  paddle-ocr.exe --image doc.png --output json --show-boxes

Options:
  --image PATH       Path to image file (png/jpg/gif/bmp/tiff/webp)
  --lang LANG        Language code (default: ch)
                       ch    - Chinese (simplified + traditional)
                       en    - English
                       japan - Japanese
                       korean - Korean
                       fr    - French
                       de    - German
  --output FORMAT    Output format: json (default) or text
  --show-boxes       Include per-line confidence in JSON output
  --stdin            Read image path from stdin (for pipe integration)
  --version          Show version info
  -h, --help         Show this help message

JSON output format:
  {{"text": "extracted text", "confidence": 0.95, "count": 25}}

Exit codes:
  0  Success (text found or empty image)
  1  Error (file not found, OCR failed, etc.)
"""


def main():
    if len(sys.argv) == 1:
        print(BANNER)
        sys.exit(0)

    parser = argparse.ArgumentParser(
        description="PaddleOCR Standalone — extract text from images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  paddle-ocr.exe --image screenshot.png\n"
               "  paddle-ocr.exe --image photo.jpg --lang en --output text\n"
               "  paddle-ocr.exe --image doc.png --output json --show-boxes\n",
    )
    parser.add_argument("--image", help="Path to image file")
    parser.add_argument("--lang", default="ch",
                        help="Language: ch (Chinese), en (English), japan (Japanese) (default: ch)")
    parser.add_argument("--output", default="json", choices=["json", "text"],
                        help="Output format (default: json)")
    parser.add_argument("--show-boxes", action="store_true",
                        help="Include per-line confidence in JSON output")
    parser.add_argument("--stdin", action="store_true",
                        help="Read image path from stdin")
    parser.add_argument("--version", action="version", version=f"paddle-ocr v{__version__} ({__engine__})")
    args = parser.parse_args()

    # Read image path from stdin if --stdin is set
    if args.stdin:
        args.image = sys.stdin.read().strip()
    elif args.image is None:
        parser.print_help()
        sys.exit(1)

    if not os.path.isfile(args.image):
        print(json.dumps({"error": f"File not found: {args.image}"}))
        sys.exit(1)

    try:
        import logging
        logging.disable(logging.INFO)

        from rapidocr import RapidOCR

        engine = RapidOCR()
        result = engine(args.image)

        if result is None or result.txts is None or len(result.txts) == 0:
            if args.output == "json":
                print(json.dumps({"text": "", "confidence": 0, "boxes": []}))
            else:
                print("")
            sys.exit(0)

        texts = list(result.txts)
        scores = [float(s) for s in result.scores] if result.scores is not None else []
        full_text = "\n".join(texts)
        avg_conf = round(sum(scores) / len(scores), 4) if scores else 0

        if args.output == "json":
            out = {"text": full_text, "confidence": avg_conf, "count": len(texts)}
            if args.show_boxes and result.boxes is not None:
                out["boxes"] = [
                    {"text": t, "confidence": round(float(s), 4)}
                    for t, s in zip(texts, scores)
                ]
            print(json.dumps(out, ensure_ascii=False))
        else:
            print(full_text)

    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
