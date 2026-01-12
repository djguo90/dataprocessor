"""Batch render manim videos from generated *_manim.py files.

输入
  - INPUT_ROOT 下的目录结构（来自 generate_manim_from_nljson.py）：
      <id>/html/step_01.html
      <id>/png/step_01.png
      <id>/<id>_manim.py
  - 需已安装 manim、xelatex、xf_voiceover 依赖。

输出文件树示例
  <OUTPUT_ROOT>/
  ├─rendered_ids.txt       # 全量排序 id 记录，便于断点续渲
  └─<id>/
    ├─<id>.mp4             # 生成视频
    └─Tex/...              # manim 中间文件

用法
  python script/render_manim_batch.py

配置（修改下方全局变量）
  INPUT_ROOT   : 根目录，包含若干 <id>/<id>_manim.py
  OUTPUT_ROOT  : 输出根目录，manim --media_dir 指向这里的 <id> 子目录
  RANGES       : 二维数组，形如 [[1, None], [10, 20]]
                 - 第一维从 1 开始，按排序后的 id 序号截取
                 - 末端为 None 表示到最后一个
  MANIM_OPTS   : 追加给 manim 的参数，默认 ['-pql']（低清快）

行为
  - 每次运行前清空 log/ 目录，为失败任务提供重试机会。
  - 读取已成功的 rendered_ids.txt，跳过已成功渲染的 id。
  - 按 id 排序后依据 RANGES 选取要渲染的未成功 id。
  - 对每个 id：
      1) 解析 *_manim.py 中的首个 class 名。
      2) 运行: manim <opts> <pyfile> <ClassName> -o <id>.mp4 --media_dir <OUTPUT_ROOT>/<id>
      3) 渲染成功：ID 添加到 rendered_ids.txt
      4) 渲染失败：在 log/ 目录创建 {id}.log 文件，记录详细错误信息
  - tqdm 进度条显示进度。

备注
  - 不指定 manim 可执行路径，使用环境中的 `manim`。
  - 失败重试机制：每次运行都会重新尝试之前失败的渲染任务。
  - rendered_ids.txt 只包含成功渲染的 ID，便于断点续渲。
  - log/ 目录中的 .log 文件包含详细的错误信息，用于问题诊断。
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from tqdm import tqdm

# -------- 全局配置 --------
INPUT_ROOT = Path(r"/mnt/pan8T/temp_djguo/math_xx_sm_svg/正式生产/数据/小数单模-立体几何/5.视频结果/小数单模-立体几何_试标_视频前处理_part001_pv2_matched_195")
# Path(r"D:\github\svg_exp\script\test_outputs_multi")
OUTPUT_ROOT = Path(
    r"/mnt/pan8T/temp_djguo/math_xx_sm_svg/正式生产/数据/小数单模-立体几何/5.视频结果/小数单模-立体几何_试标_视频结果_part001_pv2_matched_195"
)
# RANGES: [[start, end], ...] 1-based inclusive; end None -> to last
RANGES: List[Tuple[int, int | None]] = [(1, None)]
# manim 渲染附加参数（可改 '-pqh' 或 '-pqm'）
MANIM_OPTS = ["-ql"]
# 渲染记录文件
RENDER_LOG = OUTPUT_ROOT / "rendered_ids.txt"
# 错误日志目录
LOG_DIR = OUTPUT_ROOT / "log"
# 如果系统 PATH 未包含 xelatex，可在此添加 LaTeX bin 目录前缀（留空则不改）
TEX_BIN = r"/usr/bin/xelatex"
# 进程池并行度（同时渲染的场景数），建议不要超过逻辑核数
POOL_SIZE = 10
# 仓库根目录（用于补充 PYTHONPATH，让 xf_voiceover 可被找到）
ROOT_DIR = Path(__file__).resolve().parents[2]


def find_manim_py(id_dir: Path) -> Path | None:
    files = list(id_dir.glob("*_manim.py"))
    if not files:
        return None
    if len(files) > 1:
        # 取最长匹配 id 的那个
        files.sort(key=lambda p: len(p.name), reverse=True)
    return files[0]


def extract_class_name(py_path: Path) -> str:
    text = py_path.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"class\s+(\w+)\s*\(", text)
    if not m:
        raise ValueError(f"未找到 class 定义: {py_path}")
    return m.group(1)


def load_sorted_ids(root: Path) -> List[str]:
    ids = [p.name for p in root.iterdir() if p.is_dir()]
    ids.sort()
    return ids


def select_ids(ids: List[str], ranges: List[Tuple[int, int | None]]) -> List[str]:
    selected: List[str] = []
    n = len(ids)
    for start, end in ranges:
        s = max(1, start)
        e = n if end is None else min(n, end)
        if s > e:
            continue
        selected.extend(ids[s - 1 : e])
    # 保持原排序且去重
    seen = set()
    ordered = []
    for i in ids:
        if i in selected and i not in seen:
            ordered.append(i)
            seen.add(i)
    return ordered


def load_successful_ids() -> set[str]:
    """读取已成功渲染的ID列表"""
    if not RENDER_LOG.exists():
        return set()
    return (
        set(RENDER_LOG.read_text(encoding="utf-8").strip().split("\n"))
        if RENDER_LOG.stat().st_size > 0
        else set()
    )


def mp4_exists(id_str: str) -> bool:
    """
    检查最终 mp4 是否已存在。
    结构示例：<OUTPUT_ROOT>/<id>/videos/<scene>_manim/480p15/<id>.mp4
    只要任一分辨率目录下同名 mp4 存在，即视为已完成。
    """
    videos_root = OUTPUT_ROOT / id_str / "videos"
    if not videos_root.exists():
        return False
    for mp4 in videos_root.rglob(f"{id_str}.mp4"):
        if mp4.is_file():
            return True
    return False


def clear_log_directory() -> None:
    """清空之前的失败日志目录"""
    if LOG_DIR.exists():
        shutil.rmtree(LOG_DIR)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def write_error_log(
    id_str: str, py_file: Path, cls: str, return_code: int, error_msg: str = ""
) -> None:
    """写入渲染失败的错误日志"""
    log_file = LOG_DIR / f"{id_str}.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_content = f"""渲染失败记录 - {timestamp}
ID: {id_str}
Python文件: {py_file}
类名: {cls}
返回码: {return_code}
命令: manim {" ".join(MANIM_OPTS)} {py_file} {cls} -o {id_str}.mp4 --media_dir {OUTPUT_ROOT / id_str}

错误信息:
{error_msg}
"""
    log_file.write_text(log_content, encoding="utf-8")


def write_log(processed: List[str]) -> None:
    """写入成功渲染的ID列表"""
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    RENDER_LOG.write_text("\n".join(processed), encoding="utf-8")


def render_one(id_str: str, py_file: Path, cls: str) -> Tuple[bool, str]:
    """渲染单个场景，返回(成功状态, 错误信息)"""
    out_dir = OUTPUT_ROOT / id_str
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "manim",
        *MANIM_OPTS,
        str(py_file),
        cls,
        "-o",
        f"{id_str}.mp4",
        "--media_dir",
        str(out_dir),
    ]
    env = os.environ.copy()
    if TEX_BIN:
        env["PATH"] = TEX_BIN + os.pathsep + env.get("PATH", "")
    env["PYTHONUTF8"] = "1"
    env["LC_ALL"] = "C.UTF-8"
    env["PYTHONPATH"] = str(ROOT_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    try:
        print(f"[start] {id_str} -> {py_file.name} ({cls})", flush=True)
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,  # 捕获输出以记录到日志
            text=True,            # 以文本形式返回
            timeout=600,  # 10分钟超时
        )
        if result.returncode == 0:
            print(f"[ok]    {id_str}", flush=True)
            return True, ""
        else:
            error_msg = result.stderr or result.stdout or "未知错误"
            print(f"[fail]  {id_str} rc={result.returncode}", flush=True)
            print(error_msg)  # 也打印到控制台便于观察
            return False, error_msg
    except subprocess.TimeoutExpired:
        print(f"[timeout] {id_str} 超过600s", flush=True)
        return False, "渲染超时（10分钟）"
    except Exception as e:
        print(f"[error] {id_str} exec exception: {e}", flush=True)
        return False, f"执行异常: {str(e)}"


def main():
    # 1. 清空之前的失败日志目录
    clear_log_directory()

    # 2. 读取已成功渲染的ID
    successful_ids = load_successful_ids()
    print(f"跳过已成功渲染的 {len(successful_ids)} 个ID")

    # 3. 加载所有ID并排除已成功的
    all_ids = load_sorted_ids(INPUT_ROOT)
    pending_ids = [id for id in all_ids if id not in successful_ids]

    # 4. 根据RANGES选择要渲染的ID
    target_ids = select_ids(pending_ids, RANGES)
    if not target_ids:
        print("没有可渲染的 id")
        return

    print(f"准备渲染 {len(target_ids)} 个ID")

    # 5. 开始批量渲染
    successful_rendered: List[str] = []
    failed_count = 0

    with ProcessPoolExecutor(max_workers=POOL_SIZE) as pool:
        # 准备所有渲染任务
        futures = {}
        for id_str in target_ids:
            # 1) 成功 mp4 已存在则跳过
            if mp4_exists(id_str):
                print(f"[skip] {id_str} 已存在 mp4，跳过渲染")
                successful_ids.add(id_str)
                continue

            py_file = find_manim_py(INPUT_ROOT / id_str)
            if py_file is None:
                print(f"[warn] {id_str} 缺少 *_manim.py，已记入 log")
                write_error_log(
                    id_str, Path("N/A"), "N/A", 1, "缺少 *_manim.py，无法渲染"
                )
                failed_count += 1
                continue

            try:
                cls_name = extract_class_name(py_file)
            except Exception as e:
                print(f"[warn] {id_str} 解析 class 失败，已记入 log: {e}")
                write_error_log(id_str, py_file, "N/A", 1, f"解析 class 失败: {e}")
                failed_count += 1
                continue

            future = pool.submit(render_one, id_str, py_file, cls_name)
            futures[future] = (id_str, py_file, cls_name)

        # 处理渲染结果
        for fut in tqdm(
            futures.keys(), total=len(futures), desc="Rendering", unit="scene"
        ):
            id_str, py_file, cls_name = futures[fut]
            success, error_msg = fut.result()

            if success:
                # 渲染成功，记录到成功列表
                successful_rendered.append(id_str)
                # 更新完整成功列表（包含之前成功的）
                all_successful = successful_ids.union(successful_rendered)
                write_log(sorted(all_successful))
            else:
                # 渲染失败，记录错误日志
                failed_count += 1
                write_error_log(id_str, py_file, cls_name, 1, error_msg)
                print(f"[fail] {id_str} - 错误: {error_msg[:100]}...")

    print(f"\n渲染完成！成功: {len(successful_rendered)}, 失败: {failed_count}")
    print(f"成功ID已保存到: {RENDER_LOG}")
    print(f"失败日志保存在: {LOG_DIR}")


if __name__ == "__main__":
    main()
