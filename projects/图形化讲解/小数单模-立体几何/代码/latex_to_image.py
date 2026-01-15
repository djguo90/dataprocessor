import re
import shutil
import subprocess
import tempfile
import textwrap
import unicodedata
from pathlib import Path


def _escape_text_outside_math(s: str) -> str:
    """
    只在非 $...$ 区域转义最容易炸 TeX 的字符（尤其 %）。
    数学区保持原样（避免破坏 \\frac{...}{...} 这种语法）。
    """
    if s.count("$") % 2 != 0:
        raise ValueError("LaTeX字符串中公式的$符号未配对！")

    parts = s.split("$")

    # 非数学段：转义常见危险字符
    for i in range(0, len(parts), 2):
        seg = parts[i]
        seg = re.sub(r'(?<!\\)%', r'\%', seg)
        seg = re.sub(r'(?<!\\)&', r'\&', seg)
        seg = re.sub(r'(?<!\\)#', r'\#', seg)
        seg = re.sub(r'(?<!\\)_', r'\_', seg)
        parts[i] = seg

    # 数学段：只转义 %（避免注释吞掉后续内容）
    for i in range(1, len(parts), 2):
        parts[i] = re.sub(r'(?<!\\)%', r'\%', parts[i])

    return "$".join(parts)


def _eaw_width(ch: str) -> int:
    """粗略字符宽度：中日韩宽字符算2，其它算1"""
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def _wrap_text_eaw(text: str, max_cols: int) -> str:
    """
    按“列宽”自动换行：
      - 宽字符(W/F)按2列
      - 其它按1列
    保留原有换行；对每一行做二次折行。
    """
    if max_cols <= 10:
        max_cols = 10

    out_lines = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n")
        if not line:
            out_lines.append("")
            continue

        buf = []
        cols = 0
        for ch in line:
            w = _eaw_width(ch)
            if cols + w > max_cols and buf:
                out_lines.append("".join(buf).rstrip())
                buf = []
                cols = 0
            buf.append(ch)
            cols += w
        if buf:
            out_lines.append("".join(buf).rstrip())
    return "\n".join(out_lines)


def _render_plain_text_fallback(text: str, output_path: Path, dpi: int, figsize, fontsize: int) -> bool:
    """
    退化路径：不用 LaTeX，直接把字符串当普通文本画到图片上。
    - 尽量使用 Ubuntu 常见中文字体（Noto CJK / 文泉驿），没有则用默认字体（可能变方块）
    """
    try:
        import matplotlib as mpl
        mpl.use("Agg")  # 保险：无界面环境
        import matplotlib.pyplot as plt
        from matplotlib import font_manager

        s = textwrap.dedent(text).strip()
        # 退化模式下把常见 LaTeX 换行 \\ 转为实际换行
        s = s.replace(r"\\", "\n")

        # 根据图宽估一个每行最大“列数”
        # 经验估算：字符像素宽 ~ 0.6*fontsize*(dpi/72)
        width_px = float(figsize[0]) * float(dpi)
        char_px = max(1.0, 0.6 * float(fontsize) * (float(dpi) / 72.0))
        max_cols = int(width_px / char_px)

        s = _wrap_text_eaw(s, max_cols=max_cols)

        # 尝试选一个可用中文字体
        candidates = [
            "Noto Sans CJK SC",
            "Noto Serif CJK SC",
            "WenQuanYi Zen Hei",
            "WenQuanYi Micro Hei",
            "DejaVu Sans",
        ]
        fp = None
        for name in candidates:
            try:
                prop = font_manager.FontProperties(family=name)
                font_manager.findfont(prop, fallback_to_default=False)
                fp = prop
                break
            except Exception:
                continue

        mpl.rcParams.update({
            "font.family": "sans-serif",
            "axes.unicode_minus": False,
        })

        fig, ax = plt.subplots(figsize=figsize)
        ax.axis("off")

        # 左上角对齐更像“正文排版”
        ax.text(
            0.02, 0.98,
            s,
            fontsize=fontsize,
            ha="left",
            va="top",
            transform=ax.transAxes,
            linespacing=1.3,
            fontproperties=fp,
        )

        fig.savefig(output_path, dpi=dpi, bbox_inches="tight", pad_inches=0.15, facecolor="white")
        plt.close(fig)
        return True
    except Exception as e:
        print(f"退化渲染失败：{e}")
        return False


def latex_to_image(latex_str, output_path, dpi=100, figsize=(8, 4), fontsize=16) -> bool:
    """
    首选：XeLaTeX 渲染中文+公式为 PNG。
    如果 xelatex 编译失败：自动退化为“普通文本渲染”（不解析 LaTeX）。

    依赖（Ubuntu，推荐装齐）：
      sudo apt-get update
      sudo apt-get install -y texlive-xetex texlive-lang-chinese texlive-latex-extra poppler-utils fonts-noto-cjk
    """
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # ---- 首选：XeLaTeX ----
    try:
        if shutil.which("xelatex") is None:
            raise RuntimeError("未找到 xelatex")
        if shutil.which("pdftocairo") is None:
            raise RuntimeError("未找到 pdftocairo")

        s = latex_str.strip()
        s = _escape_text_outside_math(s)

        # 用 figsize 的宽度推一个“文本盒宽度”（cm），minipage 会自动换行
        text_width_cm = max(6.0, float(figsize[0]) * 2.54 * 0.92)
        baseline = max(1, int(fontsize * 1.3))

        tex = rf"""
\documentclass[border=2pt]{{standalone}}
\usepackage{{ctex}}
\usepackage{{amsmath,amssymb}}
\IfFontExistsTF{{Noto Sans CJK SC}}{{\setCJKmainfont{{Noto Sans CJK SC}}}}{{}}
\setlength{{\parindent}}{{0pt}}
\begin{{document}}
\fontsize{{{fontsize}}}{{{baseline}}}\selectfont
\begin{{minipage}}{{{text_width_cm:.2f}cm}}
{s}
\end{{minipage}}
\end{{document}}
""".strip() + "\n"

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "figure.tex").write_text(tex, encoding="utf-8")

            # 1) XeLaTeX -> PDF
            cmd = ["xelatex", "-interaction=nonstopmode", "-halt-on-error", "figure.tex"]
            r = subprocess.run(cmd, cwd=td, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if r.returncode != 0:
                raise RuntimeError("xelatex 编译失败：\n" + r.stdout)

            pdf_file = td / "figure.pdf"

            # 2) PDF -> PNG
            out_base = td / "out"
            cmd2 = ["pdftocairo", "-png", "-singlefile", "-r", str(dpi), str(pdf_file), str(out_base)]
            r2 = subprocess.run(cmd2, cwd=td, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if r2.returncode != 0:
                raise RuntimeError("pdftocairo 转换失败：\n" + r2.stdout)

            png_file = td / "out.png"

            # 跨设备移动：shutil.move（避免 EXDEV）
            if out_path.exists():
                out_path.unlink()
            shutil.move(str(png_file), str(out_path))

        return True

    except Exception as e:
        # ---- 失败则退化：普通文本画图 ----
        print(f"XeLaTeX 渲染失败，开始退化为普通文本渲染：{e}")
        return _render_plain_text_fallback(latex_str, out_path, dpi=dpi, figsize=figsize, fontsize=fontsize)


if __name__ == "__main__":
    test_latex = r"""
    大数定律：设独立同分布的随机变量序列$X_1,X_2,\dots,X_n$的数学期望为$\mu$，
    则对于任意正数$\epsilon$，有$\lim_{n\to\infty}P\left(\left|\frac{1}{n}\sum_{i=1}^n X_i - \mu\right| < \epsilon\right) = 1$。
    """

    ok = latex_to_image(test_latex, "chinese_formula.png", figsize=(8, 3), fontsize=16)
    print("渲染完成！" if ok else "渲染失败！")
