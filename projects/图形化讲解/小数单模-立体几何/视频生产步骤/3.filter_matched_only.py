"""筛选 NLJSON 中“展示键数 = narration 数且文本匹配”的记录，输出新 JSON。

匹配标准：
  - 展示键（displayContent/讲解展示 的键）数量 == 第二段 narration 数量
  - 逐条规范化后完全相等（去空白和中英文标点）

输出文件名：
  <原文件名不含扩展>_matched_<count>.json
  存放在与源文件同目录。

用法示例：
  uv run script/SVG多图形态代码提取和渲染脚本/filter_matched_only.py ^
    --source D:\github\svg_exp\svg-stage2\平面几何\v3-平台标注500题-20251201\svg-stage2-2d-gemini-v3_500.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import List


def load_items(path: Path) -> List[dict]:
    text = path.read_text(encoding="utf-8")
    try:
        obj = json.loads(text)
        return [obj] if isinstance(obj, dict) else obj
    except Exception:
        return [json.loads(line) for line in text.splitlines() if line.strip()]


def parse_blocks(answer: str):
    blocks = re.findall(r"```json\n(.*?)\n```", answer, flags=re.S)
    if len(blocks) < 2:
        return None, None

    def fix(b: str):
        try:
            b = re.sub(r"(?<!\\)\\(?![\\\"/bfnrtu])", r"\\\\", b)
            return json.loads(b)
        except Exception:
            return None

    first = fix(blocks[0])
    second = fix(blocks[1])
    if first is None or second is None:
        return None, None
    return first, second


def find_disp(first):
    if not isinstance(first, dict):
        return None
    for c in [
        first.get("analyse", {}),
        first.get("输出的新的视频脚本", {}),
        first.get("视频脚本", {}),
        first,
    ]:
        if isinstance(c, dict):
            for k in ("displayContent", "讲解展示"):
                if k in c and isinstance(c[k], dict):
                    return c[k]
    return None


def narrs(second):
    if isinstance(second, list):
        steps = second
    elif isinstance(second, dict) and "ops" in second:
        steps = second["ops"]
    else:
        steps = []
    # print([str(s.get("narration", "")) for s in steps if isinstance(s, dict)])
    # print("*" * 50)
    # print(second)
    return [str(s.get("narration", "")) for s in steps if isinstance(s, dict)]


def norm(s: str) -> str:
    return re.sub(r"[\s，。、《》“”\"',.?!！？；;：:、·\t\r\n]+", "", s)


def is_match(keys: List[str], ns: List[str]) -> bool:
    if len(keys) != len(ns):
        print(keys)
        print("-------------------------")
        print(ns)
        print("+++++++++++++++++++++++++++++++++++++++++")
        return False
    return all(norm(n) == norm(k) for n, k in zip(ns, keys))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()

    items = load_items(args.source)
    matched = []
    bad_ids = []

    for it in items:
        first, second = parse_blocks(it.get("answer", ""))
        if first is None:
            continue
        disp = find_disp(first) or {}
        # print(disp)
        # print("*" * 100)
        keys = list(disp.keys())
        if not keys:
            # print(1)
            bad_ids.append(it.get("id") or it.get("query_md5") or "unknown")
            continue
        ns = narrs(second)
        if not ns:
            # print(1)
            bad_ids.append(it.get("id") or it.get("query_md5") or "unknown")
            continue
        if is_match(keys, ns):
            matched.append(it)
        else:
            # print(1)
            bad_ids.append(it.get("id") or it.get("query_md5") or "unknown")

    out_name = f"{args.source.stem}_matched_{len(matched)}{args.source.suffix}"
    out_path = args.source.parent / out_name
    # 输出为 NDJSON，一行一个对象，符合源文件格式习惯
    with out_path.open("w", encoding="utf-8") as f:
        for it in matched:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    bad_path = args.source.parent / f"{args.source.stem}_bad_ids.txt"
    bad_path.write_text("\n".join(bad_ids), encoding="utf-8")

    print(
        f"筛选完成，保留 {len(matched)} 条，输出: {out_path}；未匹配/长度不等 ID 共 {len(bad_ids)} 条，列表: {bad_path}"
    )


if __name__ == "__main__":
    main()
