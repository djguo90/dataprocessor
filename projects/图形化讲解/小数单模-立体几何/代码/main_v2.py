import tqdm
from pathlib import Path
import json
import json_repair
import re
from checklist import remove_redundant_spaces, fix_continued_equality
from latex_to_image import latex_to_image
import os
import sys

common_utils_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../..")
sys.path.append(common_utils_path)
from common_utils import read_jsonl, save_jsonl, has_key_path, get_values_by_key_path, run_pipeline, checkpoint_to_file

import logging
logger = logging.getLogger(__name__)


# 读取原始数据
def init_data(orig_data_path):
    yield from read_jsonl(orig_data_path)

# 拆数据并保存到文件
def split_data(samples, test_count, other_count, n_test_part, save_dir, tixing):
    """
    将样本列表拆分为指定数量的测试集和自动计算份数的其他集，并保存到对应目录
    测试集：固定拆分为n_test_part份，每份test_count个样本
    其他集：根据实际数据量拆分为若干份（每份other_count个），不足一份的部分直接舍弃
    
    参数:
        samples: 待拆分的样本列表（可迭代对象）
        result_save_dir_test: 测试集保存目录路径
        result_save_dir_other: 其他集保存目录路径
        test_count: 每个测试集部分的样本数量，默认200
        other_count: 每个其他集部分的样本数量，默认500
        n_test_part: 测试集的拆分份数，默认2（对应200、200）
    返回:
        None（直接将拆分后的样本保存为文本文件）
    """
    import random
    import os
    # 设置随机种子，保证拆分结果可复现
    random.seed(101)
    
    # 1. 转换为列表并全局打乱
    samples = list(samples)
    random.shuffle(samples)
    
    # 2. 计算测试集总需求并检查是否足够
    total_test_needed = test_count * n_test_part  # 测试集总需求：200*2=400
    if len(samples) < total_test_needed:
        raise ValueError(f"测试集样本数不足！需要{total_test_needed}个样本，但仅提供了{len(samples)}个")
    
    # 3. 拆分测试集（前400个样本拆为200、200）
    test_samples_total = samples[:total_test_needed]
    test_parts = [
        test_samples_total[i*test_count : (i+1)*test_count]
        for i in range(n_test_part)
    ]
    
    # 4. 拆分其他集（核心调整：自动计算份数，舍弃不足一份的部分）
    remaining_samples = samples[total_test_needed:]  # 测试集之外的所有剩余样本
    # 计算能拆分成多少个完整的other_count份
    n_other_part = len(remaining_samples) // other_count
    # 只保留完整份数的样本（舍弃最后不足一份的部分）
    other_samples_total = remaining_samples[:n_other_part * other_count]
    # 按other_count拆分其他集
    other_parts = [
        other_samples_total[i*other_count : (i+1)*other_count]
        for i in range(n_other_part)
    ]

    # 保存数据
    result_path = {
        "试标":{},
        "训练集":{}
    }
    for idx, part in enumerate(test_parts, 1):
        save_path = Path(save_dir, tixing, "1.原始数据", f"{tixing}_试标_原始数据_part{idx:03d}.json").as_posix()
        save_jsonl(part, save_path)
        result_path["试标"][idx] = save_path
    for idx, part in enumerate(other_parts, 1):
        save_path = Path(save_dir, tixing, "1.原始数据", f"{tixing}_训练集_原始数据_part{idx:03d}.json").as_posix()
        save_jsonl(part, save_path)
        result_path["训练集"][idx] = save_path
    return result_path

# 去除题干或解析为空的数据
def remove_empty_content_analysis(samples, content_key_path, analysis_key_path):
    for sample in samples:
        if not has_key_path(sample, content_key_path):
            continue
        if not has_key_path(sample, analysis_key_path):
            continue
        content = get_values_by_key_path(sample, content_key_path)
        if len(content) != 1:
            continue
        if not isinstance(content[0], str):
            continue
        if content[0].strip() == "":
            continue
        analysis = get_values_by_key_path(sample, analysis_key_path)
        if len(analysis) != 1:
            continue
        if not isinstance(analysis[0], str):
            continue
        if analysis[0].strip() == "":
            continue
        yield sample

# 组装phase1爬取输入
def get_phase1_crawl_in(samples, phase1_prompt_path, phase1_correct_prompt_path, id_key_path, content_key_path, analysis_key_path):
    with open(phase1_prompt_path) as reader:
        prompt_template = reader.read().strip()
    with open(phase1_correct_prompt_path) as reader:
        correct_prompt_template = reader.read().strip()
    for sample in samples:
        topic_id = get_values_by_key_path(sample, id_key_path)[0]
        content = get_values_by_key_path(sample, content_key_path)[0]
        analysis =  get_values_by_key_path(sample, analysis_key_path)[0]
        prompt = prompt_template.replace("{{question}}", content).replace("{{analysis}}", analysis)
        yield {"id": topic_id, "query": [prompt, correct_prompt_template]}

# 解析phase1爬取数据
def parse_phase1_result(samples, orig_samples, content_key_path, id_key_path):
    id2content = {}
    for sample in orig_samples:
        content = get_values_by_key_path(sample, content_key_path)[0].strip()
        sample_id = get_values_by_key_path(sample, id_key_path)[0].strip()
        id2content[sample_id] = content
    for sample in samples:
        sample_id = sample["id"]
        # if sample_id not in id2content:
        #     # print(11111)
        #     continue
        # print(len(id2content))
        sample_content = id2content[sample_id]
        try:
            sample_answer = sample["answer"][-1]["content"]
            sample_answer = sample_answer[sample_answer.index("【修改后视频脚本】") + len("【修改后视频脚本】"):].strip()
            yield {"id": sample_id, "question": sample_content, "phase1_answer": sample_answer}
        except:
            continue


# 组装phase2爬取数据
def get_phase2_crawl_in(samples, phase2_prompt_path, phase2_correct_prompt_path):
    with open(phase2_prompt_path) as reader:
        prompt_template = reader.read().strip()
    with open(phase2_correct_prompt_path) as reader:
        correct_prompt_template = reader.read().strip()
    for sample in samples:
        sample_id = sample["id"]
        sample_question = sample["question"]
        sample_phase1_answer = sample["phase1_answer"]
        query = prompt_template.replace("{{question}}", sample_question).replace("{{script}}", sample_phase1_answer)
        yield {"id":sample_id, "query":[query, correct_prompt_template]}


# 解析phase2爬取输出
def parse_phase2_result(samples_orig, samples_phase1, samples_phase2, content_key_path, analyse_key_path, id_key_path):
    id2content = {}
    id2analyse = {}
    id2phase1_answer = {}
    for sample in samples_orig:
        # print(json.dumps(sample, ensure_ascii=False, indent=2))
        content = get_values_by_key_path(sample, content_key_path)[0].strip()
        analyse = get_values_by_key_path(sample, analyse_key_path)[0].strip()
        sample_id = get_values_by_key_path(sample, id_key_path)[0].strip()
        id2content[sample_id] = content
        id2analyse[sample_id] = analyse
    for sample in samples_phase1:
        id2phase1_answer[sample["id"]] = sample["phase1_answer"]
    for sample in samples_phase2:
        sample_id = sample["id"]
        # if sample_id not in id2content:
        #     # print(1111)
        #     continue
        # if sample_id not in id2analyse:
        #     continue
        # if sample_id not in id2phase1_answer:
        #     continue
        sample_content = id2content[sample_id]
        sample_analyse = id2analyse[sample_id]
        sample_phase1_answer = id2phase1_answer[sample_id]
        sample_phase2_answer = sample["answer"][-1]["content"]
        try:
            sample_phase2_answer = sample_phase2_answer[sample_phase2_answer.index("【修改后结果】") + len("【修改后结果】"):].strip()
            yield {"id": sample_id, "question": sample_content, "analyse": sample_analyse, "phase1_answer": sample_phase1_answer, "phase2_answer": sample_phase2_answer}
        except:
            continue

# 一阶段过checklist
def check_list(samples):
    for sample in samples:
        phase1_answer = sample["phase1_answer"]
        phase1_answer = phase1_answer.replace("</JSON>\n<JSON>", ",").replace("</JSON><JSON>", ",").replace("<JSON>", "[").replace("</JSON>", "]")
        # 无法解析的过滤掉
        try:
            phase1_answer = json_repair.loads(phase1_answer)
        except:
            continue
        # 上屏内容去除多余的空格、换行
        is_bad = False
        for step in phase1_answer:
            if not isinstance(step, dict):
                is_bad = True
                break
            if "step" not in step:
                print(1)
                is_bad = True
                break
            if "type" not in step:
                print(1)
                is_bad = True
                break
            if "cont" not in step:
                print(1)
                is_bad = True
                break
            if "mark_cont" not in step:
                print(1)
                is_bad = True
                break
            if "display_cont" not in step:
                print(1)
                is_bad = True
                break
            if "visual_guide" not in step:
                print(1)
                is_bad = True
                break
        if is_bad:
            continue
        try:
            for step in phase1_answer:
                if step["type"] == "出选择题":
                    continue
                step["display_cont"] = remove_redundant_spaces(step["display_cont"])
                step["display_cont"] = fix_continued_equality(step["display_cont"])
                step["display_cont"] = remove_redundant_spaces(step["display_cont"])
                if step["type"] == "思维导图节点":
                    step["display_cont"] = "【导图】" + step["display_cont"]
        except:
            continue
        phase1_answer = "\n".join([f"<JSON>{json.dumps(_, ensure_ascii=False)}</JSON>" for _ in phase1_answer])
        sample["phase1_answer"] = phase1_answer
        # TODO 答案展示内容为空
        yield sample

# 转成代码可以处理的格式
def to_manim_format(samples, html_template_path):
    import re
    with open(html_template_path) as reader:
        html_template = reader.read().strip()
    for sample in samples:
        # ===================== 步骤1：提取一阶段输出的JSON数据 =====================
        phase1_answer = sample["phase1_answer"]
        phase1_answer = phase1_answer.replace("</JSON>\n<JSON>", ",").replace("</JSON><JSON>", ",").replace("<JSON>", "[").replace("</JSON>", "]")
        stage1_data = json_repair.loads(phase1_answer)

        # ===================== 步骤2：提取二阶段的script块 =====================
        phase2_answer = sample["phase2_answer"]
        pattern_stage2 = r"【每一步的输出】\n+```html\n([\s\S]*?)\n```"
        match_stage2 = re.search(pattern_stage2, phase2_answer)
        stage2_scripts = {}  # 存储 {step_id: script_content}

        if match_stage2:
            stage2_html_str = match_stage2.group(1)
            # 匹配所有script_step_x的块
            script_pattern = r'<script id=\"script_step_(\d+)\">\n([\s\S]*?)\n</script>'
            script_matches = re.findall(script_pattern, stage2_html_str)
            # 转换为{数字id: 脚本内容}的字典
            stage2_scripts = {int(step_id): content.strip() for step_id, content in script_matches}
        # TODO 注意把autoAvoidOverlap(svg)删掉吧
        for x in stage2_scripts:
            stage2_scripts[x] = stage2_scripts[x].replace("autoAvoidOverlap(svg);", "").replace("autoAvoidOverlap(svg)", "")
        # print(sample["id"], stage2_scripts)

        # ===================== 步骤3：构建讲解字段 =====================
        # 拼接所有content作为总讲解
        total_explanation = "".join([item["cont"] for item in stage1_data if item["type"] != "出选择题"])

        # ===================== 步骤4：构建讲解展示字段 =====================
        explanation_display = {}
        orig_step = None
        prefix = ""
        for item in stage1_data:
            if item["type"] == "出选择题":
                continue
            content = item["cont"]
            text_content = item["display_cont"].strip()
            if item["step"] != orig_step:
                prefix = f"$\\textcolor{{blue}}{{【{item['step']}】}}$"
                text_content = prefix.strip() + "\n" + text_content.strip()
                prefix = text_content
            else:
                if text_content:
                    text_content = prefix.strip() + "\n" + text_content.strip()
                    prefix = text_content
                else:
                    text_content = ""
            orig_step = item["step"]
            graph_content = item["visual_guide"]
            explanation_display[content] = [text_content, graph_content]

        # ===================== 步骤5：构建视频脚本JSON =====================
        video_script = {
            "输出的新的视频脚本": {
                "讲解": total_explanation,
                "讲解展示": explanation_display
            }
        }
        # 格式化JSON，确保中文显示和缩进
        video_script_json = json.dumps(video_script, ensure_ascii=False, indent=2)

        # ===================== 步骤6：构建thinking_steps =====================
        thinking_steps_str = "thinking_steps = []"

        # ===================== 步骤7：构建语义块列表 =====================
        semantic_blocks = []
        for idx, item in enumerate(stage1_data):
            if item["type"] == "出选择题":
                continue
            block = {
                "narration": item["cont"],
                "ops": []
            }
            # 第一个块添加空的initial_html
            if idx == 0:
                block["initial_html"] = html_template
            # 匹配对应的script内容
            item_id = item["idx"]
            if item_id in stage2_scripts:
                script_content = stage2_scripts[item_id]
                op = {
                    "action": "insert",
                    "element_id": "",
                    "html": f"<script id=\"script_step_{item_id}\">\n" + script_content + "\n</script>"
                }
                block["ops"].append(op)
            semantic_blocks.append(block)
        # 格式化语义块JSON
        semantic_blocks_json = json.dumps(semantic_blocks, ensure_ascii=False, indent=2)
        # print(json.loads(semantic_blocks_json)[0]["initial_html"])

        # ===================== 步骤8：组装最终输出 =====================
        target_format = (
            f"```json\n{video_script_json}\n```\n\n"
            f"{str(thinking_steps_str)}\n\n"
            f"```json\n{semantic_blocks_json}\n```"
        )
        # blocks = re.findall(r"```json\n(.*?)\n```", target_format, flags=re.S)
        # print(json.loads(blocks[1])[0]["initial_html"])
        sample["answer"] = target_format
        yield sample


# 保存解析文本
def save_content_analysis_result(samples, save_dir, id_key_path, analysis_key_path, content_key_path, include_id_path):
    Path(save_dir).mkdir(exist_ok=True, parents=True)
    with open(include_id_path) as reader:
        include_ids = set([x.strip() for x in reader])
    for sample in samples:
        sample_id = get_values_by_key_path(sample, id_key_path)[0]
        if sample_id not in include_ids:
            continue
        sample_analysis = get_values_by_key_path(sample, analysis_key_path)[0]
        sample_content = get_values_by_key_path(sample, content_key_path)[0]
        save_path_analysis = Path(save_dir) / f"{sample_id}-1.png"
        save_path_content = Path(save_dir) / f"{sample_id}-2.png"
        if Path(save_path_analysis).exists() and Path(save_path_content).exists():
            continue
        latex_to_image(sample_analysis, save_path_analysis)
        latex_to_image(sample_content, save_path_content)


@checkpoint_to_file
def pipeline_phase1_crawl_input(orig_split_data_path, phase1_prompt_path, phase1_correct_prompt_path, id_key_path, content_key_path, analysis_key_path):
    """
    阶段1：生成爬取输入
    读取 -> 过滤空视频 -> 格式化 -> 生成Prompt
    """
    samples = read_jsonl(orig_split_data_path)
    samples = remove_empty_content_analysis(samples, content_key_path, analysis_key_path)
    samples = get_phase1_crawl_in(samples, phase1_prompt_path, phase1_correct_prompt_path, id_key_path, content_key_path, analysis_key_path)
    yield from samples

@checkpoint_to_file
def pipeline_phase2_crawl_input(orig_split_data_path, phase1_crawl_out_path, phase2_prompt_path, phase2_correct_prompt_path, id_key_path, content_key_path):
    """
    阶段1：生成爬取输入
    读取 -> 过滤空视频 -> 格式化 -> 生成Prompt
    """
    samples_orig = read_jsonl(orig_split_data_path)
    samples = read_jsonl(phase1_crawl_out_path)
    samples = parse_phase1_result(samples, samples_orig, content_key_path, id_key_path)
    samples = get_phase2_crawl_in(samples, phase2_prompt_path, phase2_correct_prompt_path)
    yield from samples

@checkpoint_to_file
def pipeline_to_manim_format(orig_split_data_path, phase1_answer_path, phase2_answer_path, id_key_path, content_key_path, analysis_key_path, html_template_path):
    """
    阶段1：生成爬取输入
    读取 -> 过滤空视频 -> 格式化 -> 生成Prompt
    """
    samples_orig = read_jsonl(orig_split_data_path)
    samples_orig = remove_empty_content_analysis(samples_orig, content_key_path, analysis_key_path)
    samples_phase1 = read_jsonl(phase1_answer_path)
    samples_phase1 = parse_phase1_result(samples_phase1, samples_orig, content_key_path, id_key_path)
    samples_phase2 = read_jsonl(phase2_answer_path)
    samples_orig = read_jsonl(orig_split_data_path)  # NOTE samples_orig被消费了，需要重新再生成一遍
    samples_orig = remove_empty_content_analysis(samples_orig, content_key_path, analysis_key_path)
    samples = parse_phase2_result(samples_orig, samples_phase1, samples_phase2, content_key_path, analysis_key_path, id_key_path)
    samples = check_list(samples)
    samples = to_manim_format(samples, html_template_path)
    yield from samples


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--save_dir", type=str, default="/mnt/pan8T/temp_djguo/math_xx_sm_svg/正式生产/数据")
    parser.add_argument("--tixing", type=str, default="小数单模-立体几何")
    parser.add_argument("--stage", type=str, default="获得解析文本", choices=["拆分数据", "phase1爬取输入", "phase2爬取输入", "转Manim格式", "获得题目解析文本"])
    parser.add_argument("--test_count", type=int, default=200)
    parser.add_argument("--other_count", type=int, default=500)
    parser.add_argument("--n_test_part", type=int, default=2)
    parser.add_argument("--data_type", type=str, default="试标", choices=["试标", "训练集"])
    parser.add_argument("--part", type=int, default=1)
    parser.add_argument("--id_key_path", type=str, default=".topic_id")
    parser.add_argument("--content_key_path", type=str, default=".video_content")
    parser.add_argument("--analysis_key_path", type=str, default=".analysis.html")
    parser.add_argument("--phase1_prompt_version", type=str, default="v2")
    parser.add_argument("--phase2_prompt_version", type=str, default="v2")
    parser.add_argument("--html_template_path", type=str, default="/mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/代码/htmlTemplate.html")
    parser.add_argument("--rendered_ids_path", type=str)
    args = parser.parse_args()

    orig_data_paths = [
        "/mnt/pan8T/temp_djguo/单模图形化/题型分类/题型分类结果/训练集/part1/立体图形的周长、面积、表面积、体积（容积）的计算.json",
        "/mnt/pan8T/temp_djguo/单模图形化/题型分类/题型分类结果/训练集/part2/立体图形的周长、面积、表面积、体积（容积）的计算.json",
        "/mnt/pan8T/temp_djguo/单模图形化/题型分类/题型分类结果/训练集/part3/立体图形的周长、面积、表面积、体积（容积）的计算.json",
        "/mnt/pan8T/temp_djguo/单模图形化/题型分类/题型分类结果/训练集/part4/立体图形的周长、面积、表面积、体积（容积）的计算.json",
        "/mnt/pan8T/temp_djguo/单模图形化/题型分类/题型分类结果/训练集/part5/立体图形的周长、面积、表面积、体积（容积）的计算.json",
    ]

    if args.phase1_prompt_version == "v1":
        phase1_prompt_path = "/mnt/pan8T/temp_djguo/math_xx_sm_svg/solid_geometry/prompts/prompt_SVG_phase1_v0104.md"
    elif args.phase1_prompt_version == "v2":
        phase1_prompt_path = "/mnt/pan8T/temp_djguo/math_xx_sm_svg/solid_geometry/prompts/prompt_SVG_phase1_v0105.md"
    elif args.phase1_prompt_version == "v3":
        phase1_prompt_path = "/mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/prompts/prompt_SVG_phase1_v0108.md"
    elif args.phase1_prompt_version == "v4":
        phase1_prompt_path = "/mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/prompts/prompt_SVG_phase1_v0108.md"
        phase1_correct_prompt_path = "/mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/prompts/prompt_SVG_phase1_check_v0113.md"
    elif args.phase1_prompt_version == "v5":
        phase1_prompt_path = "/mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/prompts/prompt_SVG_phase1_v0115.md"
        phase1_correct_prompt_path = "/mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/prompts/prompt_SVG_phase1_check_v0113.md"
    
    if args.phase2_prompt_version == "v1":
        phase2_prompt_path = "/mnt/pan8T/temp_djguo/math_xx_sm_svg/solid_geometry/prompts/prompt_SVG_phase2_v0105.md"
    elif args.phase2_prompt_version == "v2":
        phase2_prompt_path = "/mnt/pan8T/temp_djguo/math_xx_sm_svg/solid_geometry/prompts/prompt_SVG_phase2_v0106.md"
    elif args.phase2_prompt_version == "v3":
        phase2_prompt_path = "/mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/prompts/prompt_SVG_phase2_v0108.md"
    elif args.phase2_prompt_version == "v4":
        phase2_prompt_path = "/mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/prompts/prompt_SVG_phase2_v0108.md"
        phase2_correct_prompt_path = "/mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/prompts/prompt_SVG_phase2_check_v0113.md"
    elif args.phase2_prompt_version == "v5":
        phase2_prompt_path = "/mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/prompts/prompt_SVG_phase2_v0117.md"
        phase2_correct_prompt_path = "/mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/prompts/prompt_SVG_phase2_check_v0113.md"
    elif args.phase2_prompt_version == "v6":
        phase2_prompt_path = "/mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/prompts/prompt_SVG_phase2_v0117.md"
        phase2_correct_prompt_path = "/mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/prompts/prompt_SVG_phase2_check_v0119.md"
    
    orig_split_data_path = Path(args.save_dir, args.tixing, "1.原始数据", f"{args.tixing}_{args.data_type}_原始数据_part{args.part:03d}.json").as_posix()
    phase1_crawl_in_save_path = Path(args.save_dir, args.tixing, "2.phase1爬取输入_v2", f"{args.tixing}_{args.data_type}_phase1爬取输入_part{args.part:03d}_p{args.phase1_prompt_version}.json").as_posix()
    phase1_crawl_out_save_path = Path(args.save_dir, args.tixing, "2.phase1爬取输出_v2", f"{args.tixing}_{args.data_type}_phase1爬取输出_part{args.part:03d}_p{args.phase1_prompt_version}.json").as_posix()
    phase2_crawl_in_save_path = Path(args.save_dir, args.tixing, "3.phase2爬取输入_v2", f"{args.tixing}_{args.data_type}_phase2爬取输入_part{args.part:03d}_p1{args.phase1_prompt_version}_p2{args.phase2_prompt_version}.json").as_posix()
    phase2_crawl_out_save_path = Path(args.save_dir, args.tixing, "3.phase2爬取输出_v2", f"{args.tixing}_{args.data_type}_phase2爬取输出_part{args.part:03d}_p1{args.phase1_prompt_version}_p2{args.phase2_prompt_version}.json").as_posix()
    manim_save_path = Path(args.save_dir, args.tixing, "4.manim可处理格式_v2", f"{args.tixing}_{args.data_type}_manim可处理格式_part{args.part:03d}_p1{args.phase1_prompt_version}_p2{args.phase2_prompt_version}.json").as_posix()
    content_analysis_save_dir = Path(args.save_dir, args.tixing, "6.题目与解析图片_v2", f"{args.tixing}_{args.data_type}_题目与解析图片_part{int(args.part):03d}_p1{args.phase1_prompt_version}_p2{args.phase2_prompt_version}").as_posix()
    if args.stage == "拆分数据":
        samples = init_data(orig_data_paths)
        split_data(samples, args.test_count, args.other_count, args.n_test_part, args.save_dir, args.tixing)
    elif args.stage == "phase1爬取输入":
        run_pipeline(
            pipeline_phase1_crawl_input(
                save_path=phase1_crawl_in_save_path, 
                mode="write", 
            )(
                orig_split_data_path=orig_split_data_path, 
                phase1_prompt_path=phase1_prompt_path,
                phase1_correct_prompt_path=phase1_correct_prompt_path,
                id_key_path=args.id_key_path, 
                content_key_path=args.content_key_path, 
                analysis_key_path=args.analysis_key_path
            )
        )
    elif args.stage == "phase2爬取输入":
        run_pipeline(
            pipeline_phase2_crawl_input(
                save_path=phase2_crawl_in_save_path, 
                mode="write", 
            )(
                orig_split_data_path=orig_split_data_path, 
                phase1_crawl_out_path=phase1_crawl_out_save_path,
                phase2_prompt_path=phase2_prompt_path,
                phase2_correct_prompt_path=phase2_correct_prompt_path,
                id_key_path=args.id_key_path, 
                content_key_path=args.content_key_path, 
            )
        )
    elif args.stage == "获得题目解析文本":
        samples = read_jsonl(orig_split_data_path)
        samples = remove_empty_content_analysis(samples, args.content_key_path, args.analysis_key_path)
        save_content_analysis_result(samples, content_analysis_save_dir, args.id_key_path, args.analysis_key_path, args.content_key_path, args.rendered_ids_path)
    elif args.stage == "转Manim格式":
        run_pipeline(
            pipeline_to_manim_format(
                save_path=manim_save_path, 
                mode="write", 
            )(
                orig_split_data_path=orig_split_data_path, 
                phase1_answer_path=phase1_crawl_out_save_path, 
                phase2_answer_path=phase2_crawl_out_save_path, 
                id_key_path=args.id_key_path, 
                content_key_path=args.content_key_path, 
                analysis_key_path=args.analysis_key_path, 
                html_template_path=args.html_template_path
            )
        )