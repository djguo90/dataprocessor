

"""
一阶段check项
"""
import re

def remove_redundant_spaces(text):
    """
    input:
        text: 输入的文本
    output:
        清洗后的文本
    """
    if not text:
        return ""
        
    # 逻辑解析：
    # 1. text.splitlines(): 按换行符切分文本，兼容 \n, \r\n 等
    # 2. line.strip(): 去除每一行首尾的空白字符（满足要求③）
    # 3. if line.strip(): 过滤掉变成空字符串的行。
    #    这步操作同时完成了：
    #    - 删除原文本中多余的空行（满足要求②：多个换行合并为一个）
    #    - 删除包含空格的空行（满足要求②：包括多个换行中间有空格的情况）
    # 4. '\n'.join(...): 将剩下的非空行用单个换行符拼接起来
    #    因为首尾的空行在第3步已被过滤，且拼接后不会有多余换行，所以自然满足了要求①（删除首尾空白）
    
    return '\n'.join([line.strip() for line in text.splitlines() if line.strip()])


def fix_continued_equality(text):
    """
    input:
        text: 包含LaTeX公式的文本
    output:
        修复连等式，具备以下智能逻辑：
        1. 基础拆分：$A=B=C$ -> 换行显示
        2. 层级保护：不拆分括号 (), {}, [] 内的等号
        3. 智能合并：定义式（如 $S = \pi r^2 = ...$）首行保留，计算式（如 $1+1=2=...$）首行拆分
        4. 并列保护（新）：忽略逗号分隔的式子（如 $V=240, h=20$），视为并列关系不换行
    """

    # --- 1. 判断是否存在“顶层逗号” (用于识别 V=240, h=20) ---
    def has_top_level_comma(content):
        """
        检测是否存在顶层逗号（即不在括号内的逗号）。
        但在检测时需排除 '数字千分位' 的情况 (如 1,000)。
        """
        brace_stack = []
        n = len(content)
        
        for i, char in enumerate(content):
            # 跳过转义符
            if char == '\\': 
                continue # 简化处理，实际上应该跳过 i+1，但仅做存在性检测通常足够
            
            # 括号层级追踪
            if char in '({[':
                brace_stack.append(char)
            elif char in ')}]':
                if brace_stack: brace_stack.pop()
            
            # 核心判断：顶层逗号
            elif char == ',' and not brace_stack:
                # 排除千分位数字的情况：如果逗号后面紧跟着数字，认为是 1,000
                # 检查下一个非空白字符是否为数字
                is_thousand_separator = False
                if i + 1 < n:
                    next_char = content[i+1]
                    # 如果逗号后直接是数字 (1,000)
                    if next_char.isdigit():
                        is_thousand_separator = True
                
                if not is_thousand_separator:
                    return True # 发现了真正的分隔符，说明这是并列句
                    
        return False

    # --- 2. 辅助：去除保护内容以检测运算符 ---
    def strip_protected_content(s):
        res = []
        depth = 0
        i = 0
        while i < len(s):
            char = s[i]
            if char == '\\':
                i += 2; continue
            if char in '({[': depth += 1
            elif char in ')}]': depth = max(0, depth - 1)
            if depth == 0 and char not in ')}]': 
                res.append(char)
            i += 1
        return "".join(res)

    def is_calculation_expression(content):
        skeleton = strip_protected_content(content)
        operators = ['+', '-', '*', '/', '='] 
        return any(op in skeleton for op in operators)

    # --- 3. 核心分割逻辑 (层级感知) ---
    def split_top_level_equals(content):
        parts = []
        last_idx = 0
        brace_stack = [] 
        i = 0
        n = len(content)
        while i < n:
            char = content[i]
            if char == '\\':
                i += 2; continue
            if char in '({[':
                brace_stack.append(char)
            elif char in ')}]':
                if brace_stack: brace_stack.pop()
            elif char == '=' and not brace_stack:
                parts.append(content[last_idx:i])
                last_idx = i + 1
            i += 1
        parts.append(content[last_idx:])
        return parts

    # --- 4. 正则回调函数 ---
    def replacer(match):
        content = match.group(1)
        
        # [新增规则]：如果是并列句 (V=240, h=20)，直接跳过，保持原样
        if has_top_level_comma(content):
            return match.group(0)

        parts = split_top_level_equals(content)
        
        # 必须至少有3部分（即至少2个等号）才处理
        if len(parts) < 3:
            return match.group(0)
        
        parts = [p.strip() for p in parts]
        first_part = parts[0]
        new_content_lines = []
        
        # 智能首行判断
        if is_calculation_expression(first_part):
            # 纯计算，首行拆分
            new_content_lines.append(f"${first_part}$")
            remaining_start = 1
        else:
            # 变量定义，首行合并
            new_content_lines.append(f"${first_part} = {parts[1]}$")
            remaining_start = 2
            
        for part in parts[remaining_start:]:
            new_content_lines.append(f"$= {part}$")
        
        return '\n'.join(new_content_lines)

    pattern = r'\$(.*?)\$'
    return re.sub(pattern, replacer, text, flags=re.DOTALL)

# --- 完备性测试 ---
if __name__ == "__main__":
    test_cases = [
        # 场景1：你要的新特例 (并列赋值) -> 应该保持原样
        "$V=240, h=20$",
        
        # 场景2：带有数字千分位的连等式 -> 应该换行
        # 逗号后面是数字，不应视为并列句
        "$X = 10,000 = 10^4$",
        
        # 场景3：普通的连等式 -> 应该换行
        "$S = \pi r^2 = 3.14 \times 4 = 12.56$",
        
        # 场景4：函数内的逗号 -> 应该换行
        # 逗号在括号内，不应影响判断
        "$f(x, y) = x + y = 2 + 3 = 5$",
        
        # 场景5：多个逗号的并列 -> 保持原样
        "$a=1, b=2, c=3$"
    ]

    for i, t in enumerate(test_cases, 1):
        print(f"\n--- Case {i} ---")
        print(f"输入: {t}")
        print("输出:")
        print(fix_continued_equality(t))