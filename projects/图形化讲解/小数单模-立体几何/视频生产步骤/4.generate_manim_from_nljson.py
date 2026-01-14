"""Pipeline: NLJSON -> reconstructed HTML -> PNG -> manim script (XFService).

命令行快速使用
    uv run script/generate_manim_from_nljson.py --max 3 --output script\test_outputs_multi --workers 3

输入格式
  - NLJSON（整文件或 NDJSON，每行一个对象），关键字段：
      id: 题目标识
      answer: 含两个 ```json``` 代码块：
          1) analyse / 输出的新的视频脚本 / 视频脚本 ...，内含 displayContent/讲解展示
          2) ops 列表（含 initial_html 与 ops）
  - 题库 JSON/NDJSON：id 对应 input.content 或 content/题目，为题面文本，仅从题库取。

脚本参数
  --source   源 NLJSON，默认平面几何 v2 文件
  --question 题库 JSON（或 NDJSON），默认 data-source-14118.json
  --output   输出根目录，默认 script/manim_outputs
  --only-id  只处理指定 id 列表
  --max      只取前 N 条（按文件顺序）
  --workers  并发进程数，默认 3；设为 1 则串行

输出文件树（每个 id 一个子目录，示例）
  <output>/
  └─<id>/
    ├─html/
    │ └─step_01.html
    ├─png/
    │ └─step_01.png
    ├─reconstruction.json   # narration -> html 文件名映射
    └─<id>_manim.py        # 使用 xf_voiceover.XFService 的 manim 脚本

实现要点
  - 题目只从题库取（id 匹配）；若题库缺失则标记“题目缺失（题库未找到）”。
  - Ops 只在 <svg> 内 insert/update/remove/clear，保留 defs/title/desc。
  - Playwright 渲染只截 svg 元素，已存在 PNG 自动跳过，便于断点续跑。
"""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "Playwright 未安装，请先执行: uv pip install playwright beautifulsoup4 && uv run playwright install chromium"
    ) from exc

# ------- 可配置变量（放在最前，便于手工调整；均可被命令行覆盖） -------
SOURCE_JSON_PATH = Path(
    # r"/mnt/pan8T/temp_yhzou6/数学图形化讲解/files_yhzou/标注数据补充_1225/补充数据_data_1225_一二阶段融合1_matched_1133.jsonl"
    r"/mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解/小数单模-立体几何/4.manim可处理格式_v2/小数单模-立体几何_试标_manim可处理格式_part001_p1v4_p2v4_matched_196.json"
)
# Path(r"D:\github\svg_exp\svg-stage2\平面几何\v5-prompt测试\svg-stage2-2d-gemini-v5_100_matched_98.json")
# Path(r"D:\github\svg_exp\svg-stage2\平面几何\v3.5-平台标注500题-fixed-20251204\svg-stage2-2d-gemini-v3.5_500_matched_489.json")
# Path(r"D:\github\svg_exp\svg-stage2\平面几何\v3.5-平台标注500题-20251204\测试用的目录\test.json")
# Path(r"D:\github\svg_exp\svg-stage2\平面几何\v3.1-平台标注600题-20251203\svg-stage2-2d-gemini-v3.1_600_matched_570.json")
# Path(r"D:\github\svg_exp\svg-stage2\平面几何\v3-平台试标100题\svg_stage2_2d_gemini_100.json")
# Path(r"D:\github\svg_exp\svg-stage2\平面几何\test\test.json")
# Path(r"D:\github\svg_exp\svg-stage2\平面几何\v3.1-平台标注500题重爬（排除v3-20251201数据提供平台）\svg-stage2-2d-gemini-v3.1_500_matched_462.json")
# Path(r"D:\github\svg_exp\svg-stage2\平面几何\v3-平台试标100题\svg_stage2_2d_gemini_100.json")
# SOURCE_JSON_PATH = Path(r"D:\github\svg_exp\svg-stage2\平面几何\v2-这里的50题是让何老师试标的\svg_stage2_2d_gemini_50.json")


QUESTION_BANK_PATH = Path(
    r"/mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解/小数单模-立体几何/4.manim可处理格式_v2/小数单模-立体几何_试标_manim可处理格式_part001_p1v4_p2v4_matched_196.json"
)
OUTPUT_ROOT = Path(
    r"/mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解/小数单模-立体几何/5.视频结果_v2/小数单模-立体几何_试标_manim可处理格式_part001_p1v4_p2v4_matched_196"
)
# Path(r"D:\github\svg_exp\svg-stage2\平面几何\v3-平台试标100题\code-test")
# Path(r"D:\github\svg_exp\svg-stage2\平面几何\v3-平台试标100题\code")
# OUTPUT_ROOT = Path(r"D:\github\svg_exp\script\manim_outputs")
DEFAULT_WORKERS = 10
# 可选：包含 / 排除 ID 列表文件（每行一个 id），置None则不生效
INCLUDE_ID_PATH: Path | None = None
# INCLUDE_ID_PATH: Path | None = "/mnt/pan8T/temp_djguo/math_xx_sm_svg/正式生产/数据/小数单模-立体几何/4.manim可处理格式/ids.txt"
EXCLUDE_ID_PATH: Path | None = None
# Path(r"D:\github\svg_exp\svg-stage2\平面几何\v3-平台标注500题-20251201\svg-stage2-2d-gemini-v3_500_matched_377_ids.txt")


@dataclass
class StepHTML:
    narration: str
    html: str


def load_nljson(path: Path) -> List[dict]:
    """Load NLJSON: whole-file JSON or line-delimited JSON."""
    text = path.read_text(encoding="utf-8")
    try:
        obj = json.loads(text)
        return [obj]
    except Exception:
        items: List[dict] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                continue
        if not items:
            raise ValueError("无法解析 NLJSON：既非整体 JSON 也非行分隔 JSON")
        return items


def load_id_set(path: Path | None) -> set[str]:
    """读取包含/排除 ID 的文件，每行一个 id，空行忽略。路径为空或不存在则返回空集合。"""
    if not path:
        return set()
    p = Path(path)
    if not p.exists():
        return set()
    return {
        line.strip()
        for line in p.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


# --------- 文本后处理辅助（迁移自脚本后处理工具的核心片段） ---------
def fix_geometry_symbols(s: str) -> str:
    """
    将 Unicode 几何符号转为 LaTeX 命令。
    智能区分 Text 模式和 Math 模式：
    - Math ($...$): ∠ -> \angle
    - Text: ∠ -> $\angle$
    """
    if not s:
        return s

    # 拆分数学块和文本块
    math_pattern = re.compile(r"(\$.*?\$|\\\(.+?\\\)|\\\[.+?\\\])", flags=re.S)

    parts = []
    last = 0
    for m in math_pattern.finditer(s):
        # 1. 处理前面的文本块
        if m.start() > last:
            txt = s[last : m.start()]
            # 文本模式：加 $ 包裹
            txt = txt.replace("∠", r"$\angle$")
            txt = txt.replace("°", r"$^{\circ}$")
            txt = txt.replace("△", r"$\triangle$")
            txt = txt.replace("⊥", r"$\perp$")
            parts.append(txt)

        # 2. 处理数学块内部
        math_content = m.group(0)
        # 数学模式：直接替换，无需 $
        math_content = math_content.replace("∠", r"\angle ")  # 加个空格防止粘连
        math_content = math_content.replace("°", r"^{\circ}")
        math_content = math_content.replace("△", r"\triangle ")
        math_content = math_content.replace("⊥", r"\perp ")
        parts.append(math_content)

        last = m.end()

    # 3. 处理剩余文本
    if last < len(s):
        tail = s[last:]
        tail = tail.replace("∠", r"$\angle$")
        tail = tail.replace("°", r"$^{\circ}$")
        tail = tail.replace("△", r"$\triangle$")
        tail = tail.replace("⊥", r"$\perp$")
        parts.append(tail)

    return "".join(parts)


def fix_latex_underscore(s: str) -> str:
    """仅在“非数学片段”里转义下划线，保留数学模式中的下标。

    思路：
      - 先按数学块拆分：$...$、\\(...\\)、\\[...\\]、\\begin{...}...\\end{...}
      - 数学块原样保留（允许下标 `_`）。
      - 其它文本块把裸 `_` 转为 `\\_`，已写成 `\\_` 不动。
    """
    if not s:
        return s

    math_pattern = re.compile(
        r"(\$.*?\$|\\\(.+?\\\)|\\\[.+?\\\]|\\begin\{.*?\}.*?\\end\{.*?\})",
        flags=re.S,
    )

    parts = []
    last = 0
    for m in math_pattern.finditer(s):
        # 处理前面的文本块
        if m.start() > last:
            txt = s[last : m.start()]
            txt = re.sub(r"(?<!\\)_", r"\\_", txt)
            parts.append(txt)
        # 数学块原样保留
        parts.append(m.group(0))
        last = m.end()
    # 收尾文本块
    if last < len(s):
        tail = s[last:]
        tail = re.sub(r"(?<!\\)_", r"\\_", tail)
        parts.append(tail)

    return "".join(parts)


def fix_div_symbol(s: str) -> str:
    """将 \\div 替换为 \\divisionsymbol，避免兼容问题。"""
    return s.replace(r"\div", r"\divisionsymbol")


def wrap_chinese_in_math_mode(s: str) -> str:
    """将数学模式内的中文用 \\text{} 包裹，防止渲染丢失。
    例如: "$边长 \times 4$" -> "$\\text{边长} \times 4$"
    """
    if not s:
        return s

    # 匹配数学块: $...$ 或 \(...\) 或 \[...\]
    # 注意：这里简化处理，假设没有嵌套的 $
    math_pattern = re.compile(
        r"(\$.*?\$|\\\(.+?\\\)|\\\[.+?\\\])",
        flags=re.S,
    )

    # 匹配中文: 只要包含至少一个汉字，且前面没有 \text{
    # 使用 negative lookbehind (?<!...) 避免双重包裹
    chinese_pattern = re.compile(r"(?<!\\text\{)([\u4e00-\u9fa5]+)")

    parts = []
    last = 0
    for m in math_pattern.finditer(s):
        # 1. 添加前面的非数学文本（不做 wrap 处理）
        if m.start() > last:
            parts.append(s[last : m.start()])

        # 2. 处理数学块内部
        math_content = m.group(0)
        # 在数学块内查找中文并 wrap
        math_content_fixed = chinese_pattern.sub(r"\\text{\1}", math_content)
        parts.append(math_content_fixed)

        last = m.end()

    # 3. 添加剩余文本
    if last < len(s):
        parts.append(s[last:])

    return "".join(parts)

def has_svg_visual_elements(html: str) -> bool:
    """
    检测HTML中的SVG标签内是否包含指定的可视化元素（排除<defs>标签内的元素）
    
    核心规则：
    - 仅检测<defs>外部的SVG可视化元素
    - <defs>内的模板/定义类元素（如marker里的path）不纳入检测
    - 无SVG标签 或 SVG内仅<defs>内有可视化元素 → 返回False
    - SVG内<defs>外存在指定可视化元素 → 返回True
    
    参数:
        html: 待检测的HTML字符串
    
    返回:
        True: SVG内<defs>外存在指定可视化元素
        False: 无SVG标签，或仅<defs>内有可视化元素，或无任何指定可视化元素
    """
    # 定义需要检测的SVG可视化元素列表
    svg_visual_tags = [
        # 基础图形（核心）
        'circle', 'rect', 'path', 'line', 'ellipse', 'polygon', 'polyline',
        # 文本/图像
        'image', 'text', 'tspan', 'textPath',
        # 装饰/样式（扩展）
        'marker', 'pattern', 'linearGradient', 'radialGradient', 'filter',
        'clipPath', 'mask', 'use', 'symbol'
    ]
    
    # 1. 解析HTML
    soup = BeautifulSoup(html, 'html.parser')
    
    # 2. 找到所有SVG标签
    svg_tags = soup.find_all('svg')
    if not svg_tags:
        return False  # 无SVG标签，直接返回False
    
    # 3. 遍历每个SVG标签，检测<defs>外部的可视化元素
    for svg in svg_tags:
        # 定义筛选规则：标签在目标列表中，且所有祖先标签不含<defs>
        def is_outside_defs(elem):
            # 检查元素本身是否是目标标签
            if elem.name not in svg_visual_tags:
                return False
            # 检查元素的所有祖先是否包含<defs>
            for parent in elem.parents:
                if parent.name == 'defs':
                    return False
            return True
        
        # 查找SVG内符合条件的元素（<defs>外的目标元素）
        visual_elems_outside_defs = svg.find_all(is_outside_defs)
        if visual_elems_outside_defs:
            return True
    
    # 4. 无<defs>外的可视化元素（仅<defs>内有/完全无）
    return False




def post_process_tex(text: str) -> str:
    """对要放入 Tex 的字符串做安全处理。"""
    if not text:
        return text
    # 1. 几何符号替换 (Unicode -> LaTeX)
    text = fix_geometry_symbols(text)
    # 2. 先处理数学模式内的中文包裹
    text = wrap_chinese_in_math_mode(text)
    # 3. 处理下划线（注意：fix_latex_underscore 内部也会识别数学块，互不干扰）
    text = fix_latex_underscore(text)
    # 4. 其他符号替换
    text = fix_div_symbol(text)
    return text

def post_process_display(input_str: str) -> str:
    """
    检查字符串中是否存在非结尾位置的「⋯」「⋯⋯」「...」「......」，
    若存在则将所有这些符号统一替换为「······」
    
    参数：
        input_str: 输入的原始字符串
    
    返回：
        处理后的字符串（符合条件则替换，否则返回原字符串）
    """
    def mod_replace(ellipsis_patterns: str, input_str: str) -> str:
        # 构建非结尾位置的匹配正则（负向断言(?!$)表示后面不是字符串结尾）
        non_end_ellipsis_re = re.compile(f'({ellipsis_patterns})(?!$)')
        
        # 检查是否存在非结尾位置的目标省略号
        if non_end_ellipsis_re.search(input_str):
            # 构建全局替换的正则
            replace_ellipsis_re = re.compile(ellipsis_patterns)
            # 将所有目标省略号替换为「······」
            input_str = replace_ellipsis_re.sub('······', input_str)
        return input_str

        

    new_input_str = mod_replace(ellipsis_patterns=r'⋯⋯|⋯', input_str=input_str)
    new_input_str = mod_replace(ellipsis_patterns=r'\.{6}|\.{3}', input_str=new_input_str)
    if input_str != new_input_str:
        print(f"修复前：{input_str}")
        print(f"修复后：{new_input_str}")
        print("=" * 50)
    return input_str



def parse_answer_blocks(answer: str) -> tuple[dict, list]:
    """Extract two ```json blocks from answer string.

    为兼容 LaTeX 里的单反斜杠（\\pi, \\times, \\circ 等），在 json.loads 前
    先将“非 JSON 合法转义”的反斜杠加一层转义，避免 Invalid \\escape。
    """

    def _safe_load(block: str):
        # 只对非法转义加一层反斜杠。
        # 修改：将 bfnrtu 从白名单移除，防止 latex 命令（如 \times, \frac）被解析为控制字符。
        # 只保留 \" \\ / (json 结构相关)
        fixed = re.sub(r"(?<!\\)\\(?![\\\"/])", r"\\\\", block)
        return json.loads(fixed)

    blocks = re.findall(r"```json\n(.*?)\n```", answer, flags=re.S)
    if len(blocks) < 2:
        raise ValueError("answer 中未找到两个 json 代码块")
    first = json.loads(blocks[0])
    second = json.loads(blocks[1])
    return first, second


def build_display_map(first_block: dict) -> Dict[str, str]:
    """map narration -> display text (第一项，上屏文案). 兼容多种包裹结构/中英文键。"""

    def find_display_content(block: dict):
        for key in ("displayContent", "讲解展示"):
            if isinstance(block, dict) and key in block:
                return block.get(key)
        return None

    candidates = [
        first_block.get("analyse", {}),
        first_block.get("输出的新的视频脚本", {}),
        first_block.get("视频脚本", {}),
        first_block,  # 兜底：可能 displayContent 就在顶层
    ]

    display = None
    for cand in candidates:
        display = find_display_content(cand)
        if display:
            break
    if display is None:
        return {}

    result: Dict[str, str] = {}
    for narration, arr in display.items():
        if isinstance(arr, list) and arr:
            result[narration] = arr[0] or ""
    return result


def extract_full_narration(first_block: dict) -> str:
    """提取阶段一的整段讲解文本（可能字段名不同）。"""

    def pick(block: dict):
        for key in ("讲解", "explainContent", "讲解全文", "讲解内容", "讲解文本"):
            if isinstance(block, dict) and key in block and isinstance(block[key], str):
                return block[key]
        return ""

    # 优先 analyse/输出的新的视频脚本/视频脚本 下的讲解
    candidates = [
        pick(first_block),
        pick(first_block.get("analyse", {})),
        pick(first_block.get("输出的新的视频脚本", {})),
        pick(first_block.get("视频脚本", {})),
    ]
    for txt in candidates:
        if txt:
            return txt
    return ""


def split_sentences(text: str) -> List[str]:
    """按中文/英文句号、问号、感叹号、分号切分，保留原标点。"""
    if not text:
        return []
    parts = re.findall(r"[^。！？!?；;]+[。！？!?；;]?", text)
    return [p.strip() for p in parts if p.strip()]


def find_voiceonly_segments(
    full_narration: str, existing_narrations: List[str], display_keys: List[str]
) -> List[str]:
    """找出未出现在展示键/ops叙述里的讲解片段，供纯语音播放。"""
    if not full_narration:
        return []
    existing_pool = existing_narrations + display_keys
    voice_only: List[str] = []
    for sent in split_sentences(full_narration):
        if any(sent in x or x in sent for x in existing_pool):
            continue
        voice_only.append(sent)
    return voice_only


def merge_narration_sequence(full_narration: str, narrations: List[str]):
    """
    按阶段一讲解句序交织 step / voice-only，支持“句子中嵌入 narration”的场景：
      - 若句子包含当前 narration 子串：先把前缀作为 voice（若有），再输出 step，再把后缀继续匹配后续 narration（可重复）。
      - 若句子与未来的 narration 近似但不包含当前 narration，则跳过等待后续匹配，避免重复。
      - 剩余未匹配的 narration 追加末尾。
    """
    sentences = split_sentences(full_narration)
    merged = []
    step_i = 0

    def similar(a: str, b: str) -> bool:
        return a == b or a in b or b in a

    for sent in sentences:
        cursor = sent
        while cursor and step_i < len(narrations):
            cur_narr = narrations[step_i]
            pos = cursor.find(cur_narr)
            if pos == -1:
                # 若后续 narration 与整句相似，则跳过等待后面匹配；否则整句作为 voice
                if any(similar(cursor, n) for n in narrations[step_i:]):
                    cursor = ""  # 延后匹配，不生成 voice
                    break
                merged.append(("voice", cursor))
                cursor = ""
                break
            # 前缀 voice
            prefix = cursor[:pos].strip()
            if prefix:
                merged.append(("voice", prefix))
            # 当前 step
            merged.append(("step", step_i))
            step_i += 1
            cursor = cursor[pos + len(cur_narr) :].strip()
        if cursor:
            # 句尾剩余未匹配部分
            merged.append(("voice", cursor))

    while step_i < len(narrations):
        merged.append(("step", step_i))
        step_i += 1
    return merged


def apply_ops_to_html_backup(current_html: str, ops: list) -> str:
    """Apply ops to current html, returning new html."""
    soup = BeautifulSoup(current_html, "html.parser")
    svg = soup.find("svg")
    if svg is None:
        raise ValueError("HTML 缺少 <svg>")

    def parse_fragment(fragment: str):
        frag_soup = BeautifulSoup(fragment, "html.parser")
        return [x for x in frag_soup.contents if getattr(x, "name", None)]

    for op in ops:
        action = op.get("action")
        element_id = op.get("element_id")
        frag_html = op.get("html", "")

        if action == "insert":
            for el in parse_fragment(frag_html):
                svg.append(el)
        elif action == "update":
            target = svg.find(id=element_id)
            if target:
                fragments = parse_fragment(frag_html)
                if fragments:
                    target.replace_with(fragments[0])
            else:
                for el in parse_fragment(frag_html):
                    svg.append(el)
        elif action == "remove":
            target = svg.find(id=element_id)
            if target:
                target.decompose()
        elif action == "clear":
            for child in list(svg.children):
                if getattr(child, "name", None) is None:
                    continue
                if child.name in {"defs", "title", "desc"}:
                    continue
                child.decompose()
        else:
            raise ValueError(f"未知 action: {action}")

    return str(soup)


def apply_ops_to_html(current_html: str, ops: list) -> str:
    for op in ops:
        # print(op["html"].strip().replace("\\n", "\n"))
        current_html = current_html.replace("    <!-- 步骤代码放这里 -->", op["html"].strip()+"\n"+"    <!-- 步骤代码放这里 -->")
    return current_html.replace("\\\n", "\n")


def reconstruct_html_steps(ops_list: list) -> List[StepHTML]:
    if not ops_list:
        return []
    initial = ops_list[0].get("initial_html")
    # if has_svg_visual_elements(initial):
    #     raise ValueError("initial_html 不是空白画布")


    if not initial:
        raise ValueError("缺少 initial_html")

    results: List[StepHTML] = []
    current_html = initial
    for step in ops_list:
        # 先应用 ops 再记录画面，避免“讲解对应上一帧”导致初始画面重复的问题。
        if step.get("ops"):
            current_html = apply_ops_to_html(current_html, step["ops"])
        # print(current_html)
        narration = step.get("narration", "") or ""
        results.append(StepHTML(narration=narration, html=current_html))
    return results


def render_htmls_to_png(html_dir: Path, png_dir: Path) -> List[Path]:
    html_dir.mkdir(parents=True, exist_ok=True)
    png_dir.mkdir(parents=True, exist_ok=True)
    html_files = sorted(html_dir.glob("step_*.html"))
    png_paths: List[Path] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        for html_file in html_files:
            html_abs = html_file.resolve()
            png_path = png_dir / (html_file.stem + ".png")
            if png_path.exists():
                png_paths.append(png_path)
                continue
            page.goto(html_abs.as_uri())
            page.wait_for_timeout(200)
            try:
                svg = page.locator("svg")
                svg.wait_for(timeout=1000)
                svg.screenshot(path=str(png_path))
            except Exception:
                # 兜底：如果未找到 svg，则截整页，避免阻断流水线
                page.screenshot(path=str(png_path), full_page=True)
            png_paths.append(png_path)
        browser.close()
    return png_paths


def sanitize_class_name(id_str: str) -> str:
    clean = re.sub(r"\W+", "_", id_str)
    if not clean or clean[0].isdigit():
        clean = f"Scene_{clean}"
    return clean


def generate_manim_py(
    id_str: str,
    question: str,
    timeline: List[str],  # The master list of narrations from displayContent
    display_map: Dict[str, str],
    narration_to_png: Dict[str, Path],
    out_path: Path,
):
    class_name = sanitize_class_name(id_str)

    def _escape(text: str) -> str:
        return (
            text.replace('"', '\\"')
            .replace("\\n", "\\\\")
            .replace("\n", "\\\\")
            .replace("\r", "\\\\")
            .replace("<b>", "$\\textbf{")
            .replace("</b>", "}$")
        )

    q_safe = post_process_tex(_escape(question))
    lines = []
    lines.append("from pathlib import Path")
    lines.append("from manim import *")
    lines.append("from manim_voiceover import VoiceoverScene")
    lines.append("from xf_voiceover import XFService")
    lines.append("")
    lines.append(f"class {class_name}(VoiceoverScene):")
    lines.append("    def construct(self):")
    lines.append("        self.set_speech_service(XFService())")
    lines.append("        self.camera.background_color = WHITE")
    lines.append("        Text.set_default(font='SimHei', color=BLACK)")
    lines.append(
        "        Tex.set_default(color=BLACK, font_size=22, tex_template=TexTemplateLibrary.ctex)"
    )
    lines.append("        animation_font_size = 20")
    lines.append(
        "        animation_area = Rectangle(width=5.0, height=6.0, fill_opacity=0, color=WHITE)"
    )
    lines.append("        animation_area.z_index = -100")          # 强制最底层")
    lines.append("        animation_area.to_edge(LEFT, buff=0.5)")
    lines.append(
        "        text_area = Rectangle(width=6.0, height=6.0, fill_opacity=0, color=WHITE)"
    )
    lines.append("        text_area.to_edge(RIGHT, buff=0.2)")
    lines.append("        self.add(animation_area, text_area)")

    # ✅ 固定文本锚点：text_area 左上角同一位置（给一点内边距）
    lines.append("        text_anchor = text_area.get_corner(UL) + RIGHT*0.35 + DOWN*0.35")

    lines.append(f'        problem = Tex(r"{q_safe}")')
    lines.append("        problem.to_edge(UP, buff=0.5)")
    lines.append("        self.play(Write(problem))")
    lines.append("        self.wait(2)")
    lines.append("        current_img = None")
    lines.append("        text_items = VGroup()")

    for idx, narration in enumerate(timeline, start=1):
        n_safe = post_process_tex(_escape(narration))
        png_path = narration_to_png.get(narration)
        disp = display_map.get(narration, "")
        disp_safe = post_process_display(post_process_tex(_escape(disp)))

        if png_path:
            lines.append(f"        # Step {idx}")
            lines.append(f'        with self.voiceover(text="{n_safe}") as tracker:')

            lines.append(f"            new_img = ImageMobject(r'{png_path}').scale(1.3)")
            lines.append("            new_img.move_to(animation_area.get_center() + RIGHT*0.3)")
            lines.append("            if current_img is None:")
            lines.append("                self.play(FadeIn(new_img))")
            lines.append("            else:")
            lines.append("                self.play(FadeOut(current_img), FadeIn(new_img))")
            lines.append("            current_img = new_img")

            if disp:
                # ✅ 每一步都清空 text_items
                lines.append("            if len(text_items) > 0:")
                lines.append("                self.play(FadeOut(text_items))")
                lines.append("                text_items = VGroup()")
                lines.append(
                    f'            text_line = Tex(r"{disp_safe}", color=BLACK, font_size=animation_font_size, tex_template=TexTemplateLibrary.ctex, tex_environment="flushleft")'
                )
                # ✅ 每一步都从同一个锚点开始放
                lines.append("            text_line.move_to(text_anchor, aligned_edge=UL)")
                lines.append("            self.play(Write(text_line), run_time=tracker.duration * 0.4)")
                lines.append("            text_items.add(text_line)")

            lines.append("            self.wait(1e-3)")

        else:
            lines.append(f"        # Voice-only {idx}")
            lines.append(f'        with self.voiceover(text="{n_safe}") as tracker:')

            if disp:
                # ✅ 每一步都清空 text_items
                lines.append("            if len(text_items) > 0:")
                lines.append("                self.play(FadeOut(text_items))")
                lines.append("                text_items = VGroup()")
                lines.append(
                    f'            text_line = Tex(r"{disp_safe}", color=BLACK, font_size=animation_font_size, tex_template=TexTemplateLibrary.ctex, tex_environment="flushleft")'
                )
                # ✅ 每一步都从同一个锚点开始放
                lines.append("            text_line.move_to(text_anchor, aligned_edge=UL)")
                lines.append("            self.play(Write(text_line), run_time=tracker.duration * 0.4)")
                lines.append("            text_items.add(text_line)")

            lines.append("            self.wait(1e-3)")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def process_one(item: dict, question_map: Dict[str, str], out_root: Path):
    id_str = item.get("id") or item.get("query_md5") or "sample"
    # print(f"[child-start] {id_str}", flush=True)
    answer = item.get("answer")
    if not answer:
        print(f"[skip] {id_str} 缺少 answer")
        return
    first_block, ops_block = parse_answer_blocks(answer)
    display_map = build_display_map(first_block)

    # Master timeline: Keys of displayContent (preserving order)
    # If displayContent is not found or empty, fallback to ops narrations?
    # No, strict v3.1 requires displayContent.
    if not display_map:
        # Fallback: use narrations from ops as timeline if display_map is empty
        # (though this shouldn't happen if prompt is followed)
        print(f"[warn] {id_str} display_map empty, falling back to ops narrations")
        timeline = [op.get("narration", "") for op in ops_block]
    else:
        timeline = list(display_map.keys())

    steps = reconstruct_html_steps(ops_block)

    base_dir = out_root / id_str
    html_dir = base_dir / "html"
    png_dir = base_dir / "png"
    base_dir.mkdir(parents=True, exist_ok=True)

    recon_map = {}
    narration_to_png = {}  # map narration -> png path (may be absent for voice-only steps)

    # Render HTMLs and build mapping
    html_dir.mkdir(parents=True, exist_ok=True)
    current_html_content = ""

    for idx, step in enumerate(steps, start=1):
        # Only generate PNG if HTML content actually changed from previous step?
        # Or trust that ops=[] produces same HTML.
        # To implement "No visual change" logic properly:
        # We check if the step has non-empty ops in ops_block.
        # But steps is already reconstructed.
        # Let's look at the raw ops_block[idx-1]

        raw_op_block = ops_block[idx - 1] if idx - 1 < len(ops_block) else {}
        raw_ops = raw_op_block.get("ops", [])
        is_initial = raw_op_block.get("initial_html") is not None

        # If ops is empty and not initial, it's a voice-only step (visually).
        # But reconstruct_html_steps generates html for it (same as previous).
        # We only want to register it in narration_to_png if it's a VISUAL step.

        has_visual_change = bool(raw_ops) or is_initial

        if has_visual_change:
            html_file = html_dir / f"step_{idx:02d}.html"
            html_file.write_text(step.html, encoding="utf-8")
            recon_map[step.narration] = html_file.name

            # We will verify PNG existence later, but here we map it logically
            png_path = png_dir / (html_file.stem + ".png")
            narration_to_png[step.narration] = png_path
        else:
            # No visual change -> Do NOT map this narration to a PNG.
            # generate_manim_py will see None and generate Voice-only.
            pass

        (base_dir / "reconstruction.json").write_text(
            json.dumps(recon_map, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # Render only the generated HTMLs
        render_htmls_to_png(html_dir, png_dir)

    # 题目必须来自题库，找不到则标记缺失
    question_text = question_map.get(id_str, "题目缺失（题库未找到）")

    manim_path = base_dir / f"{id_str}_manim.py"
    print(f"[start] {id_str}", flush=True)
    generate_manim_py(
        id_str,
        question_text,
        timeline,
        display_map,
        narration_to_png,
        manim_path,
    )
    # print(f"[child-done] {id_str} -> {manim_path}", flush=True)


def load_question_bank(path: Path) -> Dict[str, str]:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except Exception:
        # 尝试行分隔 JSON
        mapping = {}
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            qid = str(obj.get("id"))
            content = (
                obj.get("input", {}).get("content")
                or obj.get("question")
                or obj.get("input", {}).get("题目")
                or obj.get("content")
                or obj.get("题目")
            )
            if qid and content:
                mapping[qid] = content
        return mapping

    if isinstance(data, list):
        return {
            str(x.get("id")): (
                x.get("input", {}).get("content")
                or x.get("content")
                or x.get("题目", "")
            )
            for x in data
            if isinstance(x, dict)
        }
    if isinstance(data, dict):
        return {
            str(k): (v.get("input", {}).get("content") or v.get("content", ""))
            for k, v in data.items()
            if isinstance(v, dict)
        }
    return {}


def is_output_complete(id_str: str, out_root: Path) -> bool:
    """判定指定 id 的输出目录是否“齐全”，齐全则可跳过重跑。"""
    base_dir = out_root / id_str
    if not base_dir.is_dir():
        return False
    manim_py = base_dir / f"{id_str}_manim.py"
    recon = base_dir / "reconstruction.json"
    png_dir = base_dir / "png"
    html_dir = base_dir / "html"
    if not (
        manim_py.exists() and recon.exists() and png_dir.is_dir() and html_dir.is_dir()
    ):
        return False
    if not any(png_dir.glob("*.png")):
        return False
    if not any(html_dir.glob("*.html")):
        return False
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE_JSON_PATH)
    parser.add_argument("--question", type=Path, default=QUESTION_BANK_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--only-id", nargs="*", help="只处理指定 id 列表")
    parser.add_argument(
        "--include-file",
        type=Path,
        default=INCLUDE_ID_PATH,
        help="包含 id 列表文件（每行一个 id），为空则忽略",
    )
    parser.add_argument(
        "--exclude-file",
        type=Path,
        default=EXCLUDE_ID_PATH,
        help="排除 id 列表文件（每行一个 id），为空则忽略",
    )
    parser.add_argument("--max", type=int, default=None, help="最多处理多少条")
    parser.add_argument(
        "--workers", type=int, default=DEFAULT_WORKERS, help="并发进程数，设为 1 则串行"
    )
    args = parser.parse_args()

    items = load_nljson(args.source)
    question_map = load_question_bank(args.question)

    include_ids = load_id_set(args.include_file)
    exclude_ids = load_id_set(args.exclude_file)

    if args.include_file:
        print(f"[filter] include file={args.include_file} -> {len(include_ids)} ids")
    if args.exclude_file:
        print(f"[filter] exclude file={args.exclude_file} -> {len(exclude_ids)} ids")

    selected = []
    for obj in items:
        obj_id = obj.get("id")
        if include_ids and obj_id not in include_ids:
            continue
        if exclude_ids and obj_id in exclude_ids:
            continue
        if args.only_id and obj_id not in args.only_id:
            continue
        selected.append(obj)
    print(
        f"[filter] source={args.source.name} total={len(items)} "
        f"after filters={len(selected)}"
    )
    if args.max is not None:
        selected = selected[: args.max]

    out_root: Path = args.output
    out_root.mkdir(parents=True, exist_ok=True)

    if args.workers and args.workers > 1:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {}
            for obj in selected:
                obj_id = obj.get("id")
                manim_py = args.output / str(obj_id) / f"{obj_id}_manim.py"
                if manim_py.exists():
                    print(f"[skip] {obj_id} 已存在 *_manim.py，跳过生成")
                    continue
                if obj_id and is_output_complete(obj_id, out_root):
                    print(f"[skip] {obj_id} 已存在且文件齐全")
                    continue
                # print(f"[queue] {obj_id}", flush=True)
                futures[pool.submit(process_one, obj, question_map, out_root)] = obj_id
            for fut in as_completed(futures):
                obj_id = futures[fut]
                try:
                    fut.result()
                    print(f"[main-done] {obj_id}", flush=True)
                except Exception as exc:
                    print(f"[error] {obj_id}: {exc}")
    else:
        for obj in selected:
            obj_id = obj.get("id")
            manim_py = args.output / str(obj_id) / f"{obj_id}_manim.py"
            if manim_py.exists():
                print(f"[skip] {obj_id} 已存在 *_manim.py，跳过生成")
                continue
            if obj_id and is_output_complete(obj_id, out_root):
                print(f"[skip] {obj_id} 已存在且文件齐全")
                continue
            # print(f"[queue] {obj_id}", flush=True)
            try:
                process_one(obj, question_map, out_root)
                print(f"[main-done] {obj_id}", flush=True)
            except Exception as exc:
                print(f"[error] {obj.get('id')}: {exc}")


if __name__ == "__main__":
    main()
