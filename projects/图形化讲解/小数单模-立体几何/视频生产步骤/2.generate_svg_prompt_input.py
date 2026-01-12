#!/usr/bin/env python3
# coding: utf-8
"""
生成SVG Prompt输入数据脚本
根据几何题目数据和prompt模板生成SVG prompt输入文件

主要功能：
1. 支持多种数据源格式，基于ID进行合并去重
2. 从数据源中提取题目内容（content、question或query字段）
3. 加载prompt模板文件
4. 将prompt模板和题目内容拼接，生成完整的查询文本
5. 支持根据ID文件筛选特定数据
6. 支持按行数范围提取数据
7. 输出NLJSON格式文件，每行一个JSON对象

支持的数据源格式：
1. 简单格式 (simple)：[{id, question}]
2. 内容字段格式 (simple_content)：[{id, content}]
3. 嵌套格式 (nested)：{category: [{content, id}]}
4. 错误格式 (items_array)：{name, items: [{id, content}]}
5. 无后缀NLJSON格式 (transcript)：每行一个JSON对象，包含tranScript.scienceStruct结构
   {
     "topic_id": "str",
     "analysis": "str",
     "tranScript": {
       "scienceStruct": {
         "content": "题目内容",
         "standardAnalyse": "分析内容",
         ...
       },
       ...
     },
     ...
   }
6. NLJSON格式 (nljson)：每行一个JSON对象，包含query字段，从"题目如下："后提取题目内容
   {
     "id": "str",
     "query": "prompt模板\n# 题目如下：题目内容",
     "param": {"temperature": 0.7}
   }
7. Input嵌套格式 (input_nested)：每行一个JSON对象，包含id和input字段
   {
     "id": "str",
     "input": {
       "content": "题目内容文本",
       "analyse": {
         "explainContent": "详细解析说明文本",
         "displayContent": {
           "知识点1": "解释1",
           "知识点2": "解释2"
         }
       }
     }
   }

输出文件格式（NLJSON）：
每行一个JSON对象，格式为：
{
  "id": "题目ID",
  "query": "prompt模板\n题目内容",
  "param": {"temperature": 0.7}
}
"""

import json
import os
import sys
from datetime import datetime
from multiprocessing import Process

# ============================================================================
# 配置参数（全部大写，放在最前面）
# ============================================================================

# 文件路径配置
PROMPT_PATH = (
    r"/data/temp_yhzou6/数学图形化讲解/SVG-单模-交接文件/prompts_for_svg/平面几何/prompt-SVG-mutiple-imgs-2D-v5.md"
    # r"D:\github\svg_exp\题目拒识\2D-除钟面外\prompt.md"
    # r"D:\github\svg_exp\prompts_for_svg\平面几何\prompt-SVG-mutiple-imgs-2D-v3.5.md"
)
SAVE_DIR = r"/data/temp_yhzou6/数学图形化讲解/files_yhzou/data/crawl_data/data_part5"
# r"D:\github\svg_exp\svg-stage2\平面几何\v5-prompt测试"
# r"D:\github\svg_exp\svg-stage2\平面几何\v3.5-平台标注500题-20251204"

# 输入数据集 - 支持多个数据源，格式为列表
# 如果有多个数据源，数据会基于ID进行合并去重
DATA_PATHS = [
    r"/data/temp_yhzou6/数学图形化讲解/SVG-单模-交接文件/svg-stage2/平面几何/data-source-14118.json"
    # 第二批平面几何tiku
    # r"D:\github\svg_exp\tiku\2D-except-clock\2D-图形几何-第二批\data\script_with_ht_and_preset_3_filted_2D_32559",
    # r"D:\github\svg_exp\tiku\2D-except-clock\2D-图形几何-第二批\data\script_with_ht_and_preset_328_filted_2D_32860",
    # r"D:\github\svg_exp\tiku\2D-except-clock\2D-图形几何-第二批\data\script_with_ht_and_preset_391_filted_2D_32514",
    # r"D:\github\svg_exp\tiku\2D-except-clock\2D-图形几何-第二批\data\script_with_ht_and_preset_450_filted_2D_32542"
    # 使用指定的数据源 - 新的input嵌套格式数据
    # r"D:\github\svg_exp\svg-stage2\平面几何\data-source-14118.json"
    # r"D:\github\svg_exp\svg_exp\model_sft_data\v3.0\train_test_set\2d_svg_train_1_None_2d_train_set_137183_prompt_updated_with_titles\2d_test_set_300_弧线凹面_边标记_fixed_gemini_300_prompt_updated_filted_2D_121644.json"
    # r"D:\github\svg_exp\svg_exp\model_sft_data\v2.0\train_test_set\2d_svg_train_1_None_2d_train_set_32571_fixed_弧线凹面_边标记错误_32571.cleaned_with_titles\2d_svg_train_1_None_2d_train_set_32571_fixed_弧线凹面_边标记错误_32571.cleaned_32569_filted_2D_26553.json"
    # r"D:\github\svg_exp\tiku\2D-except-clock\10w\script_with_ht_and_preset_28_filted_2D_37368",
    # r"D:\github\svg_exp\tiku\2D-except-clock\10w\script_with_ht_and_preset_31_filted_2D_37249",
    # r"D:\github\svg_exp\tiku\2D-except-clock\10w\script_with_ht_and_preset_34_filted_2D_37311"
    # r"D:\github\svg_exp\tiku\classified_questions\geometric_transformation_questions.json",  # 简单格式
    # r"D:\github\svg_exp\tiku\sampled_150000_lines_export_all_Doubao-Seed-1.6-no_format\2d_geometry_28074_questions.json",  # 嵌套格式
    # # 可以添加更多数据源路径
    # r"D:\github\svg_exp\tiku\sampled_5w_分题型数据\classified_questions\coordinate_transform.json",
    # r"D:\github\svg_exp\tiku\sampled_5w_分题型数据\classified_questions\geometric_relations.json",
    # r"D:\github\svg_exp\tiku\sampled_5w_分题型数据\classified_questions\number_line_applications.json",
    # r"D:\github\svg_exp\tiku\sampled_5w_分题型数据\classified_questions\perimeter_area_2d.json",
    # r"D:\github\svg_exp\tiku\sampled_5w_分题型数据\classified_questions\triangle_angles.json",
    # r"D:\github\svg_exp\tiku\graphical_explanation_data_tiku_rule_geometry\filtered_2d_geometry_questions.json",
    # r"D:\github\svg_exp\path\to\transcript_data.jsonl",  # transcript格式（无后缀NLJSON）
    # r"D:\github\svg_exp\tiku\sampled_5w_分题型数据\classified_questions\triangle_angles.json"
    # r"D:\github\svg_exp\tiku\sampled_5w_分题型数据\三角形角度的计算\三角形角度的计算.json"
]

# 输出文件名（基础名称，不含扩展名和数量）
OUTPUT_FILE_NAME = "svg-stage2-2d-prompt-input-v5-baseline"

# ID文件路径（可选，如果指定则只处理这些ID的数据）
# 如果不需要ID筛选，设置为空字符串""
# IDS_FILE_PATH = r"D:\github\svg_exp\script\ids_with_edge_marks_32571.txt"
# IDS_FILE_PATH = r"D:\github\svg_exp\svg_exp\model_sft_data\v1.0\train_test_set\2d_test_set_300_ids.txt"  # 设置为空字符串表示不使用ID筛选功能

# 使用之前从exported_svg_selection_18518.json中提取的ID
# IDS_FILE_PATH = r"D:\github\svg_exp\svg_exp\svg-筛选数据\svg-2D-除钟面外\exported_svg_selection_18518_with_id\exported_svg_selection_18518_ids.txt"
# r"D:\github\svg_exp\svg-stage2\平面几何\v2-这里的50题是让何老师试标的\svg_stage2_2d_gemini_50_ids.txt"
# r"D:\github\svg_exp\svg_exp\model_sft_data\v1.0\train_test_set\2d_train_set_32571_ids.txt"

# 已处理过的ID文件路径，用于排除重复题目（可选）
# 如果不需要去除已处理ID，保持为空字符串
# r"D:\github\svg_exp\svg-stage2\平面几何\v3-平台试标100题\svg_stage2_2d_gemini_100_ids.txt"
# 支持多个包含/排除ID文件（列表形式，留空列表即不启用）

IDS_FILE_PATHS: list[str] = []

EXCLUDE_IDS_FILE_PATHS: list[str] = [
    "/data/temp_yhzou6/数学图形化讲解/SVG-单模-交接文件/svg-stage2/平面几何/v3.5-平台标注500题-fixed-20251204/svg-stage2-2d-gemini-v3.5_500_matched_489_non_other_category_ids_464.txt",
    "/data/temp_yhzou6/数学图形化讲解/SVG-单模-交接文件/svg-stage2/平面几何/v5-分包1+2一2000题/svg-stage2-2d-gemini-v5-分包-1_1000_merged_2_2000_matched_1891_non_other_category_ids_1802.txt",
    "/data/temp_yhzou6/数学图形化讲解/SVG-单模-交接文件/svg-stage2/平面几何/v5-平台标注-1000-分包-1/svg-stage2-2d-prompt-input-v5-分包-1_1000_ids.txt",
    "/data/temp_yhzou6/数学图形化讲解/SVG-单模-交接文件/svg-stage2/平面几何/v5-平台标注-1000-分包-2/svg-stage2-2d-prompt-input-v5-分包-2_1000_ids.txt",
    "/data/temp_yhzou6/数学图形化讲解/SVG-单模-交接文件/svg-stage2/平面几何/v5-平台标注-1000-分包-3/svg-stage2-2d-prompt-input-v5-分包-3_1000_ids.txt"
]
# [
#     r"D:\github\svg_exp\svg-stage2\平面几何\v5-平台标注-1000-分包-2\svg-stage2-2d-prompt-input-v5-分包-2_1000_ids.txt",
#     r"D:\github\svg_exp\svg-stage2\平面几何\v5-平台标注-1000-分包-1\svg-stage2-2d-prompt-input-v5-分包-1_1000_ids.txt",
#     r"D:\github\svg_exp\svg-stage2\平面几何\v3.1-平台标注500题重爬（排除v3-20251201数据提供平台）\svg-stage2-2d-gemini-v3.1_500_matched_462_ids.txt",
#     r"D:\github\svg_exp\svg-stage2\平面几何\v3-平台标注500题-20251201\svg-stage2-2d-gemini-v3_500_matched_377_ids.txt",
#     r"D:\github\svg_exp\svg-stage2\平面几何\v3.1-平台标注600题-20251203\svg-stage2-2d-prompt-input-v3.1_600_ids.txt",
#     r"D:\github\svg_exp\svg-stage2\平面几何\v3.5-平台标注500题-20251204\svg-stage2-2d-gemini-v3.5_500_ids.txt",
# ]

# 行数范围控制参数 - 二维列表格式 [[start_row, end_row], [start_row, end_row], ...]
# 使用直观的行号（从1开始），end_row不填或为None表示到最后一行
ROW_RANGES = [[8001, 10000]]  # 处理所有匹配的数据
# ROW_RANGES = [[1, None]]  # 处理所有匹配的数据
# ROW_RANGES = [[1, 2]]  # 测试时只处理前2行数据
# ROW_RANGES = [[1, 10], [20, 30]]  # 示例：处理第1-10行和第20-30行
# ROW_RANGES = [[1, None]]  # 示例：处理从第1行到最后一行

# ============================================================================
# 核心功能函数
# ============================================================================


def load_prompt(path: str) -> str:
    """
    加载prompt模板

    Args:
        path (str): prompt文件路径

    Returns:
        str: prompt内容
    """
    try:
        with open(path, "r", encoding="utf-8-sig") as f:  # 使用utf-8-sig处理BOM
            return f.read()
    except Exception as e:
        print(f"错误：无法加载prompt文件 {path}: {e}")
        sys.exit(1)


def normalize_id(raw_id: str) -> str:
    """
    标准化ID格式

    Args:
        raw_id (str): 原始ID

    Returns:
        str: 标准化后的ID
    """
    if raw_id is None:
        return ""
    s = str(raw_id).strip()
    if "#" in s:
        s = s.split("#", 1)[0]
    if len(s) > 60 and "_" in s:
        s = s.split("_")[-1]
    return s


def detect_data_format(data):
    """
    检测数据格式类型

    Args:
        data: 加载的JSON数据或文件路径

    Returns:
        str: 'simple' 表示简单格式 [{id, question}],
             'simple_content' 表示使用content字段的简单格式 [{id, content}],
             'nested' 表示嵌套格式 {category: [{content, id}]},
             'items_array' 表示弧度画图错误格式 {name, items: [{id, content}]},
             'transcript' 表示无后缀NLJSON格式（每行一个JSON对象）
    """
    # 检查是否为文件路径（用于检测transcript格式）
    if isinstance(data, str) and os.path.exists(data):
        file_path = data
        try:
            # 读取第一行来检测格式
            with open(file_path, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                if first_line:
                    first_item = json.loads(first_line)
                    # 检查是否是transcript格式（包含tranScript.scienceStruct结构）
                    if (
                        "tranScript" in first_item
                        and isinstance(first_item.get("tranScript"), dict)
                        and "scienceStruct" in first_item.get("tranScript", {})
                        and "content"
                        in first_item.get("tranScript", {}).get("scienceStruct", {})
                    ):
                        return "transcript"
                    # 检查是否是标准NLJSON格式（包含query字段）
                    elif "query" in first_item:
                        return "nljson"
                    # 检查是否是input嵌套格式（包含id和input字段）
                    elif "id" in first_item and "input" in first_item:
                        return "input_nested"
                    else:
                        return "nljson"  # 默认当作普通NLJSON处理
                return "unknown"
        except Exception:
            return "unknown"

    # 原有逻辑处理标准JSON对象
    if isinstance(data, list):
        # 简单格式：直接是数组
        # 检查第一个元素的字段结构，判断是使用question还是content字段
        if data and isinstance(data[0], dict):
            if "question" in data[0]:
                return "simple"
            elif "content" in data[0]:
                return "simple_content"
        # 如果数组为空或元素不是字典，默认为simple格式
        return "simple"
    elif isinstance(data, dict):
        # 检查是否为弧度画图错误格式
        if "name" in data and "items" in data and isinstance(data["items"], list):
            return "items_array"
        # 嵌套格式：对象包含多个类别数组
        else:
            return "nested"
    else:
        raise ValueError(f"不支持的数据格式：{type(data)}")


def extract_nested_data(nested_data):
    """
    从嵌套格式数据中提取所有题目

    Args:
        nested_data: 嵌套格式的数据 {category: [{content, id}]}

    Returns:
        list: 标准化的题目列表 [{id, question}]
    """
    extracted_data = []

    for category, questions in nested_data.items():
        if not isinstance(questions, list):
            print(f"[WARNING] 类别 '{category}' 不是数组格式，跳过")
            continue

        print(f"[OK] 处理类别：{category}，包含 {len(questions)} 道题目")

        for item in questions:
            if not isinstance(item, dict):
                print(f"[WARNING] 跳过非对象格式的题目")
                continue

            # 从嵌套格式中提取数据并转换为标准格式
            question_text = item.get("content", "")
            item_id = item.get("id", "")

            if not question_text or not item_id:
                print(
                    f"[WARNING] 跳过无效题目 - ID: {item_id}, Content: {question_text[:50] if question_text else 'None'}"
                )
                continue

            # 转换为标准格式
            standard_item = {"id": item_id, "question": question_text}
            extracted_data.append(standard_item)

    return extracted_data


def extract_items_array_data(items_data):
    """
    从弧度画图错误格式数据中提取所有题目

    Args:
        items_data: 弧度画图错误格式的数据 {name, items: [{id, content}]}

    Returns:
        list: 标准化的题目列表 [{id, question}]
    """
    extracted_data = []

    # 检查数据格式
    if not isinstance(items_data, dict):
        print(f"[ERROR] 数据不是对象格式")
        return extracted_data

    if "name" not in items_data or "items" not in items_data:
        print(f"[ERROR] 数据格式不正确，缺少 name 或 items 字段")
        return extracted_data

    name = items_data.get("name", "")
    items = items_data.get("items", [])

    if not isinstance(items, list):
        print(f"[ERROR] items 字段不是数组格式")
        return extracted_data

    print(f"[OK] 处理数据集：{name}，包含 {len(items)} 道题目")

    for item in items:
        if not isinstance(item, dict):
            print(f"[WARNING] 跳过非对象格式的题目")
            continue

        # 从弧度画图错误格式中提取数据并转换为标准格式
        question_text = item.get("content", "")
        item_id = item.get("id", "")

        if not question_text or not item_id:
            print(
                f"[WARNING] 跳过无效题目 - ID: {item_id}, Content: {question_text[:50] if question_text else 'None'}"
            )
            continue

        # 转换为标准格式
        standard_item = {"id": item_id, "question": question_text}
        extracted_data.append(standard_item)

    return extracted_data


def extract_transcript_data(transcript_file_path):
    """
    从无后缀NLJSON格式文件（transcript嵌套结构）中提取所有题目

    Args:
        transcript_file_path (str): transcript格式文件路径

    Returns:
        list: 标准化的题目列表 [{id, question}]
    """
    extracted_data = []

    if not os.path.exists(transcript_file_path):
        print(f"[WARNING] transcript文件不存在: {transcript_file_path}")
        return extracted_data

    try:
        with open(transcript_file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    item = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"警告：第{line_num}行JSON解析失败: {e}")
                    continue

                # 提取tranScript.scienceStruct.content字段作为题目内容
                try:
                    content = (
                        item.get("tranScript", {})
                        .get("scienceStruct", {})
                        .get("content", "")
                    )
                except (AttributeError, TypeError):
                    # 如果结构不完整，跳过该条目
                    print(
                        f"[WARNING] 第{line_num}行缺少tranScript.scienceStruct.content结构，跳过"
                    )
                    continue

                # 使用topic_id作为题目ID
                item_id = item.get("topic_id", "")

                if not content or not item_id:
                    print(
                        f"[WARNING] 跳过无效题目 - ID: {item_id}, Content: {content[:50] if content else 'None'}"
                    )
                    continue

                # 转换为标准格式
                standard_item = {"id": item_id, "question": content}
                extracted_data.append(standard_item)

    except Exception as e:
        print(f"[ERROR] 读取transcript文件失败 {transcript_file_path}: {e}")

    return extracted_data


def extract_simple_data_with_content(simple_data):
    """
    从使用content字段的简单格式数据中提取所有题目

    Args:
        simple_data: 使用content字段的简单格式数据 [{id, content}]

    Returns:
        list: 标准化的题目列表 [{id, question}]
    """
    extracted_data = []

    if not isinstance(simple_data, list):
        print(f"[ERROR] 数据不是数组格式")
        return extracted_data

    print(f"[OK] 处理简单格式数据（content字段），包含 {len(simple_data)} 道题目")

    for item in simple_data:
        if not isinstance(item, dict):
            print(f"[WARNING] 跳过非对象格式的题目")
            continue

        # 从简单格式中提取数据并转换为标准格式
        question_text = item.get("content", "")
        item_id = item.get("id", "")

        if not question_text or not item_id:
            print(
                f"[WARNING] 跳过无效题目 - ID: {item_id}, Content: {question_text[:50] if question_text else 'None'}"
            )
            continue

        # 转换为标准格式
        standard_item = {"id": item_id, "question": question_text}
        extracted_data.append(standard_item)

    return extracted_data


def extract_nljson_data(nljson_file_path):
    """
    从NLJSON格式文件中提取所有题目，从query字段中提取题目内容

    Args:
        nljson_file_path (str): NLJSON格式文件路径

    Returns:
        list: 标准化的题目列表 [{id, question}]
    """
    extracted_data = []

    if not os.path.exists(nljson_file_path):
        print(f"[WARNING] NLJSON文件不存在: {nljson_file_path}")
        return extracted_data

    try:
        with open(nljson_file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    item = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"警告：第{line_num}行JSON解析失败: {e}")
                    continue

                # 提取query字段中的题目内容
                query_text = item.get("query", "")

                # 查找"题目如下："锚点，提取后面的内容
                anchor = "# 题目如下："
                anchor_index = query_text.find(anchor)

                if anchor_index != -1:
                    # 提取锚点后面的内容作为题目
                    question_text = query_text[anchor_index + len(anchor) :].strip()
                else:
                    # 如果没有找到锚点，尝试使用其他方法提取题目
                    # 这里可以添加更多的提取逻辑，或者跳过这条记录
                    print(f"[WARNING] 第{line_num}行未找到题目锚点，跳过")
                    continue

                # 使用id字段作为题目ID
                item_id = item.get("id", "")

                if not question_text or not item_id:
                    print(
                        f"[WARNING] 跳过无效题目 - ID: {item_id}, Question: {question_text[:50] if question_text else 'None'}"
                    )
                    continue

                # 转换为标准格式
                standard_item = {"id": item_id, "question": question_text}
                extracted_data.append(standard_item)

    except Exception as e:
        print(f"[ERROR] 读取NLJSON文件失败 {nljson_file_path}: {e}")

    return extracted_data


def extract_input_nested_data(input_nested_file_path):
    """
    从input嵌套格式文件中提取所有题目，保留完整的input对象

    Args:
        input_nested_file_path (str): input嵌套格式文件路径

    Returns:
        list: 标准化的题目列表 [{id, input: JSON对象}]
    """
    extracted_data = []

    if not os.path.exists(input_nested_file_path):
        print(f"[WARNING] input嵌套格式文件不存在: {input_nested_file_path}")
        return extracted_data

    try:
        with open(input_nested_file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    item = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"警告：第{line_num}行JSON解析失败: {e}")
                    continue

                # 提取id和input字段
                item_id = item.get("id", "")
                input_obj = item.get("input", {})

                if not item_id or not input_obj:
                    print(
                        f"[WARNING] 跳过无效题目 - ID: {item_id}, Input: {'有内容' if input_obj else 'None'}"
                    )
                    continue

                # 转换为标准格式，保留完整的input对象
                standard_item = {
                    "id": item_id,
                    "question": json.dumps(input_obj, ensure_ascii=False),
                }
                extracted_data.append(standard_item)

    except Exception as e:
        print(f"[ERROR] 读取input嵌套格式文件失败 {input_nested_file_path}: {e}")

    return extracted_data


def load_ids_from_file(ids_file_path: str) -> set:
    """
    从文本文件加载ID列表

    Args:
        ids_file_path (str): ID文件路径

    Returns:
        set: ID集合，如果文件不存在则返回空集合
    """
    ids = set()
    try:
        with open(ids_file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:  # 跳过空行
                    ids.add(line)
        print(f"[OK] 从ID文件加载了 {len(ids)} 个唯一ID")
        return ids
    except FileNotFoundError:
        print(f"[INFO] ID文件不存在，将处理所有数据：{ids_file_path}")
        return set()
    except Exception as e:
        print(f"[WARNING] 读取ID文件失败，将处理所有数据：{ids_file_path}, 错误：{e}")
        return set()


def load_ids_from_files(paths: list[str]) -> set:
    """合并多个ID文件（忽略不存在/空路径）。"""
    all_ids: set[str] = set()
    for p in paths or []:
        if not p:
            continue
        all_ids |= load_ids_from_file(p)
    return all_ids


def load_ids_from_files(paths: list[str]) -> set:
    """合并多个ID文件（忽略不存在/空路径）。"""
    all_ids: set[str] = set()
    for p in paths or []:
        if not p:
            continue
        all_ids |= load_ids_from_file(p)
    return all_ids


def filter_data_by_ids(data: list, target_ids: set) -> list:
    """
    根据ID集合筛选数据

    Args:
        data (list): 原始数据列表
        target_ids (set): 目标ID集合，如果为空则返回原数据

    Returns:
        list: 筛选后的数据列表
    """
    if not target_ids:
        # 如果没有指定ID，返回原数据
        return data

    filtered_data = []
    matched_count = 0

    for item in data:
        item_id = normalize_id(item.get("id", ""))
        if item_id in target_ids:
            filtered_data.append(item)
            matched_count += 1

    print(f"[OK] 根据ID列表筛选完成")
    print(f"[OK] 从 {len(data)} 条数据中匹配到 {matched_count} 条")

    # 显示未匹配的ID数量
    missing_count = len(target_ids) - matched_count
    if missing_count > 0:
        print(f"[WARNING] 有 {missing_count} 个ID未找到匹配的数据")

    return filtered_data


def exclude_data_by_ids(data: list, exclude_ids: set) -> list:
    """
    根据排除ID集合移除数据

    Args:
        data (list): 原始数据列表
        exclude_ids (set): 需要排除的ID集合，如果为空则返回原数据

    Returns:
        list: 过滤后的数据列表
    """
    if not exclude_ids:
        return data

    retained = []
    excluded_count = 0

    for item in data:
        item_id = normalize_id(item.get("id", ""))
        if item_id in exclude_ids:
            excluded_count += 1
            continue
        retained.append(item)

    print(f"[OK] 根据排除ID列表过滤完成")
    print(
        f"[OK] 从 {len(data)} 条数据中排除 {excluded_count} 条，保留 {len(retained)} 条"
    )
    return retained


def load_data_with_merge(data_paths):
    """
    从多个路径加载数据并基于ID去重合并

    Args:
        data_paths (list): 数据文件路径列表

    Returns:
        tuple: (merged_data, format_type) 合并后的数据和数据格式
    """
    all_data = {}
    data_format = None
    total_items = 0

    for path in data_paths:
        if not os.path.exists(path):
            print(f"[WARNING] 数据文件不存在，跳过：{path}")
            continue

        try:
            # 首先检测文件格式（传入文件路径）
            current_format = detect_data_format(path)

            # 第一次检测到格式时记录
            if data_format is None:
                data_format = current_format
            elif data_format != current_format:
                print(
                    f"[WARNING] 数据文件 {path} 的格式 {current_format} 与之前检测的格式 {data_format} 不同"
                )

            # 根据格式加载数据
            if current_format == "transcript":
                # transcript格式需要特殊处理
                data = extract_transcript_data(path)
            elif current_format == "nljson":
                # NLJSON格式需要特殊处理
                data = extract_nljson_data(path)
            elif current_format == "input_nested":
                # input嵌套格式需要特殊处理
                data = extract_input_nested_data(path)
            else:
                # 其他格式可以尝试直接加载整个文件
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)
                except json.JSONDecodeError:
                    # 如果直接加载失败，可能是NLJSON格式，尝试逐行解析
                    print(f"[INFO] 尝试逐行解析文件：{path}")
                    with open(path, "r", encoding="utf-8") as f:
                        raw_data = []
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()
                            if line:
                                try:
                                    raw_data.append(json.loads(line))
                                except json.JSONDecodeError as e:
                                    print(f"[WARNING] 第{line_num}行JSON解析失败: {e}")
                                    continue

                # 再次检测格式（使用已加载的数据）
                if isinstance(raw_data, list) or isinstance(raw_data, dict):
                    rechecked_format = detect_data_format(raw_data)
                    if rechecked_format != current_format:
                        print(
                            f"[INFO] 重新检测到的格式 {rechecked_format} 与初始检测的格式 {current_format} 不同，使用重新检测的格式"
                        )
                        current_format = rechecked_format

                # 根据格式提取数据
                if current_format == "simple":
                    data = raw_data
                elif current_format == "simple_content":
                    data = extract_simple_data_with_content(raw_data)
                elif current_format == "nested":
                    data = extract_nested_data(raw_data)
                elif current_format == "items_array":
                    data = extract_items_array_data(raw_data)
                else:
                    print(f"[WARNING] 跳过不支持格式的文件：{path}")
                    continue

            # 基于ID合并数据
            current_count = 0
            for item in data:
                item_id = normalize_id(item.get("id", ""))
                if item_id:
                    if item_id not in all_data:
                        all_data[item_id] = item
                        current_count += 1
                    else:
                        print(f"[INFO] 发现重复ID，已跳过：{item_id}")

            print(
                f"[OK] 从 {path} 加载了 {current_count} 条唯一数据（原始：{len(data)} 条）"
            )
            total_items += current_count

        except Exception as e:
            print(f"[ERROR] 加载数据文件失败 {path}: {e}")
            continue

    # 转换为列表
    merged_data = list(all_data.values())
    print(f"[OK] 总共合并了 {len(merged_data)} 条唯一数据")

    return merged_data, data_format


def get_data_by_ranges(data_list, row_ranges):
    """
    根据二维列表参数提取指定范围的数据
    row_ranges: [[start1, end1], [start2, end2], ...]  # 行号从1开始，end_row为None表示到最后一行
    返回指定范围内的数据列表，保持原始顺序
    """
    selected_data = []
    total_rows = len(data_list)

    print(f"[OK] 数据范围设置：{row_ranges}")

    for i, (start_row, end_row) in enumerate(row_ranges):
        # 将行号转换为索引（行号1-10对应索引0-9）
        start_index = max(0, start_row - 1)

        # 处理结束行号
        if end_row is None or end_row == "" or end_row == 0:
            end_index = total_rows - 1  # 到最后一行
            range_desc = f"第{start_row}行到最后一行"
        else:
            end_index = min(total_rows - 1, end_row - 1)
            range_desc = f"第{start_row}-{end_row}行"

        if start_index > end_index:
            print(f"[WARNING] 范围{range_desc}无效，跳过")
            continue

        range_data = data_list[start_index : end_index + 1]
        selected_data.extend(range_data)

        print(f"[OK] 范围{i + 1}：{range_desc}，包含{len(range_data)}条记录")

    print(f"[OK] 总共选择了{len(selected_data)}条记录进行处理")
    return selected_data


def single_process(data, save_path, prompt_template):
    """
    处理数据并生成SVG prompt输入

    Args:
        data (list): 题目数据列表
        save_path (str): 保存路径
        prompt_template (str): prompt模板
    """
    try:
        # 确保保存目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        # 准备输出数据
        output_data = []
        processed_count = 0

        for item in data:
            # 获取题目ID和内容
            data_id = normalize_id(item.get("id", ""))
            question = item.get("question", "")

            if not data_id or not question:
                print(
                    f"警告：跳过无效数据 - ID: {data_id}, Question: {question[:50] if question else 'None'}"
                )
                continue

            # 拼接prompt和题目
            full_query = prompt_template + "\n" + question

            # 构造输出对象
            output_item = {
                "id": data_id,
                "query": full_query,
                "param": {"temperature": 0.7},
            }

            output_data.append(output_item)
            processed_count += 1

            # 显示进度
            if processed_count % 100 == 0:
                print(f"已处理 {processed_count} 条数据...")

        # 保存数据（JSON Lines格式）
        with open(save_path, "w", encoding="utf-8") as f:
            for item in output_data:
                json_line = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
                f.write(json_line + "\n")

        print(f"\n[OK] 处理完成！")
        print(f"[OK] 成功处理 {processed_count} 条数据")
        print(f"[OK] 输出文件：{save_path}")

        # 显示第一条数据示例
        if output_data:
            print("\n示例数据（第一条）:")
            print(f"  ID: {output_data[0]['id']}")
            print(f"  Query长度: {len(output_data[0]['query'])} 字符")
            print(f"  Query预览: ...{output_data[0]['query'][-100:]}")

        return processed_count

    except Exception as e:
        print(f"错误：处理数据失败: {e}")
        return 0


# ============================================================================
# 主函数
# ============================================================================


def generate_output_filename(base_name: str, count: int) -> str:
    """
    生成带数据数量的输出文件名

    Args:
        base_name (str): 基础文件名（不含扩展名）
        count (int): 处理的数据数量

    Returns:
        str: 完整的文件名，格式为 base_name_{count}.json
    """
    return f"{base_name}_{count}.json"


def main():
    """主函数"""
    print("=" * 80)
    print("生成SVG Prompt输入数据脚本")
    print("=" * 80)

    # 检查必要文件
    if not DATA_PATHS:
        print("错误：数据源列表为空")
        return

    has_valid_path = False
    for path in DATA_PATHS:
        if os.path.exists(path):
            has_valid_path = True
            break

    if not has_valid_path:
        print("错误：所有数据源文件都不存在")
        return

    if not os.path.exists(PROMPT_PATH):
        print(f"错误：Prompt文件不存在：{PROMPT_PATH}")
        return

    # 加载数据
    print(f"\n[步骤 1/3] 从多个数据源加载数据...")
    try:
        data, data_format = load_data_with_merge(DATA_PATHS)

        if not data:
            print("[ERROR] 错误：没有成功加载任何数据")
            return

        print(f"[OK] 最终数据格式：{data_format}")

    except Exception as e:
        print(f"错误：加载数据失败: {e}")
        return

    # 根据ID文件筛选数据（如果存在）
    print(f"\n[步骤 1.5/3] 根据ID文件筛选数据...")
    target_ids = load_ids_from_files(IDS_FILE_PATHS)
    data = filter_data_by_ids(data, target_ids)
    if not data:
        print(f"[ERROR] 错误：没有匹配到任何数据")
        return

    # 根据排除ID文件过滤数据（如果指定）
    print(f"\n[步骤 1.6/3] 根据排除ID文件过滤数据...")
    exclude_ids = load_ids_from_files(EXCLUDE_IDS_FILE_PATHS)
    if not exclude_ids:
        print("[INFO] 未指定排除ID文件，跳过排除逻辑")

    if exclude_ids:
        data = exclude_data_by_ids(data, exclude_ids)
        if not data:
            print(f"[ERROR] 错误：排除后没有剩余数据")
            return

    # 加载prompt模板
    print(f"\n[步骤 2/3] 加载Prompt模板...")
    prompt_template = load_prompt(PROMPT_PATH)
    print(f"[OK] 成功加载Prompt模板，长度：{len(prompt_template)} 字符")

    # 提取指定范围的数据
    print(f"\n[步骤 2.5/3] 提取指定范围的数据...")
    data = get_data_by_ranges(data, ROW_RANGES)
    if not data:
        print(f"[ERROR] 错误：没有选择到数据")
        return

    # 处理数据
    print(f"\n[步骤 3/3] 生成SVG Prompt输入数据...")

    # 使用单进程处理
    temp_output_path = os.path.join(SAVE_DIR, "temp_output.json")
    processed_count = single_process(data, temp_output_path, prompt_template)

    # 生成带数量的最终文件名
    if processed_count > 0:
        final_filename = generate_output_filename(OUTPUT_FILE_NAME, processed_count)
        final_output_path = os.path.join(SAVE_DIR, final_filename)

        # 重命名临时文件为最终文件名
        if os.path.exists(final_output_path):
            # 如果最终文件已存在，删除它
            os.remove(final_output_path)
        os.rename(temp_output_path, final_output_path)
        output_path = final_output_path
    else:
        output_path = temp_output_path

    # 完成
    print("\n" + "=" * 80)
    print("任务完成！")
    print("=" * 80)
    if processed_count > 0:
        print(f"输出文件路径：{output_path}")
        print(f"可用于下一步LLM处理")


if __name__ == "__main__":
    main()
