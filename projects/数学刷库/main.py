"""
数学单模视频清洗 (Refactored with checkpoint_to_file)
"""
import json
import re
import argparse
from pathlib import Path
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 引入你的工具库
from common_utils import read_jsonl, get_values_by_key_path, checkpoint_to_file

# ==================== 基础处理逻辑 (保持不变) ====================

def read_init_data(data_path):
    yield from read_jsonl(data_path)

def filter_empty_video(samples, tran_script_key, phase):
    """过滤无视频或结构不正确的数据"""
    for sample in samples:
        tran_scripts = get_values_by_key_path(sample, tran_script_key)
        if len(tran_scripts) != 1:
            continue
        tran_script = tran_scripts[0]
        try:
            if isinstance(tran_script, str):
                tran_script = json.loads(tran_script)
            else:
                assert isinstance(tran_script, dict)
            
            struct = tran_script.get("scienceStruct", {})
            required_keys = ["content", "readQuestion", "conclusion"]
            
            if phase == "初中":
                required_keys.extend(["analyses", "standardAnswers"])
            elif phase == "小学":
                required_keys.extend(["analyse", "standardAnswer"])
            else:
                continue

            if not all(k in struct for k in required_keys):
                continue
                
        except:
            continue
        yield sample

def format_input(samples, tran_script_key, phase):
    """将原始数据格式化为待处理格式"""
    for sample in samples:
        tran_script = get_values_by_key_path(sample, tran_script_key)[0]
        if isinstance(tran_script, str):
            tran_script = json.loads(tran_script)
            
        struct = tran_script["scienceStruct"]
        
        if phase == "初中":
            video_cont = struct["content"]
            video_read = struct["readQuestion"]
            video_analyses = struct["analyses"]
            video_answers = struct["standardAnswers"]
            video_conclusion = struct["conclusion"]
        elif phase == "小学":
            video_cont = struct["content"]
            video_read = struct["readQuestion"]
            video_analyses = [struct["analyse"]]
            video_answers = [struct["standardAnswer"]]
            video_conclusion = struct["conclusion"]
        else:
            continue

        result = {}
        result["读题"] = {"讲解内容": video_read.get("explainContent", "")}
        
        for i, (ana, ans) in enumerate(zip(video_analyses, video_answers)):
            suffix = "" if len(video_analyses) == 1 else str(i + 1)
            result[f"分析{suffix}"] = {
                "讲解内容": ana.get("explainContent", ""), 
                "展示内容": ana.get("displayContent", "")
            }
            result[f"标准作答{suffix}"] = {
                "讲解内容": ans.get("explainContent", ""), 
                "展示内容": ans.get("displayContent", "")
            }
            
        result["总结"] = {
            "讲解内容": video_conclusion.get("explainContent", ""), 
            "展示内容": video_conclusion.get("displayContent", "")
        }
        
        final_result = {
            "id": sample["topic_id"], 
            "video_question": video_cont, 
            "video": result
        }
        yield final_result

def to_crawl_in(samples, prompt_path):
    """生成爬虫输入Prompt"""
    with open(prompt_path) as reader:
        prompt_template = reader.read().strip()
    for sample in samples:
        prompt = prompt_template.replace("{{ques}}", sample["video_question"]).replace("{{video}}", json.dumps(sample["video"], ensure_ascii=False, indent=2))
        sample["query"] = prompt
        yield sample

def filter_video_logic(samples):
    """处理视频拒识逻辑"""
    for sample in samples:
        answer = sample.get("answer", "")
        if '"审核结果": "不合格"' in answer:
            result = {
                "topic_id": sample["id"], 
                "tran_script_version": "单模视频过滤", 
                "tran_script_operate_type": "null"
            }
            yield result

# --- Network Utils ---

def create_retry_session(retries=3, backoff_factor=0.5, timeout=30):
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.timeout = timeout
    session.headers.update({
        'User-Agent': 'Mozilla/5.0',
        'Content-Type': 'application/json',
        'Connection': 'keep-alive'
    })
    return session

def safe_post_request(url, payload, max_attempts=5):
    session = create_retry_session(retries=3, timeout=60)
    for attempt in range(max_attempts):
        try:
            response = session.post(url, json=payload)
            response.raise_for_status()
            return response
        except Exception as e:
            time.sleep(2 ** attempt)
            if attempt == max_attempts - 1:
                print(f"Request failed: {e}")
    return None

def filter_latex_logic(samples):
    """Latex 过滤逻辑"""
    url = "http://localhost:3000/latex2html"
    for sample in samples:
        assert "id" in sample
        is_latex_good = True
        question = sample["video_question"]
        video = sample["video"]
        video_display = [question]
        
        for k in video:
            content = video[k].get("展示内容", "")
            if isinstance(content, dict):
                video_display.extend(list(content.keys()))
            elif isinstance(content, list):
                video_display.extend(content)
            elif isinstance(content, str):
                video_display.append(content)

        # 简单的清洗和检查
        processed_display = []
        for c in video_display:
            if not isinstance(c, str): continue
            # 简单的替换逻辑 (保留原来的)
            c = c.replace("\tau", "\\tau").replace("\triangle", "\\triangle") \
                 .replace("\times", "\\times").replace("\therefore", "\\therefore") \
                 .replace("\text", "\\text").replace("\neg", "\\neg") \
                 .replace("\neq", "\\neq").replace("\nabl", "\\nabl") \
                 .replace("\newline", "\\newline").replace("\t", "").replace("\n", "").replace("\"", "'")
            
            c_dump = json.dumps(c, ensure_ascii=False)
            if ("\\" in c_dump or "^" in c_dump) and "$" not in c:
                is_latex_good = False
                break
            processed_display.append(c)

        if not is_latex_good:
            yield {"topic_id": sample["id"], "tran_script_version": "单模视频latex过滤", "tran_script_operate_type": "null"}
            continue
            
        video_display_str = "\n".join(processed_display)
        if re.search(r'[a-zA-Z]', video_display_str) is None:
            continue
            
        payload = {"text": video_display_str}
        response = safe_post_request(url, payload)
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get("code") != 200:
                is_latex_good = False
        else:
             # 如果服务不通，策略是保留还是过滤？此处保持原逻辑(认为是坏的?)
             # 原逻辑里如果未响应似乎没有置为False，这里需注意
             pass 

        if not is_latex_good:
            yield {"topic_id": sample["id"], "tran_script_version": "单模视频latex过滤", "tran_script_operate_type": "null"}

def filter_analysis_logic(samples):
    for sample in samples:
        if sample.get("analysis_operate_type") in ["delete", "null"]:
            yield {"topic_id": sample["topic_id"], "tran_script_version": "单模视频解析过滤继承", "tran_script_operate_type": "null"}

def filter_all_logic(samples_orig, samples_video, samples_analysis, samples_latex):
    id2result = {}
    # 优先级覆盖：latex > analysis > video (根据原逻辑顺序)
    # 原逻辑是先遍历latex, analysis, video放入字典，后放入的会覆盖前面的
    # 假设一个ID只会在一种过滤中出现问题，或者取并集
    
    for l in samples_latex: id2result[l["topic_id"]] = l
    for l in samples_analysis: id2result[l["topic_id"]] = l
    for l in samples_video: id2result[l["topic_id"]] = l
    
    for sample in samples_orig:
        tid = sample.get("topic_id")
        if not tid: continue
        
        if tid in id2result:
            yield id2result[tid]
        else:
            yield {"topic_id": tid, "tran_script_version": "单模视频过滤", "tran_script_operate_type": "same"}


# ==================== 核心修改：Pipeline 函数 (使用 @checkpoint_to_file) ====================

@checkpoint_to_file
def pipeline_crawl_input(orig_data_path, tran_script_key, phase, prompt_path):
    """
    阶段1：生成爬取输入
    读取 -> 过滤空视频 -> 格式化 -> 生成Prompt
    """
    samples = read_init_data(orig_data_path)
    samples = filter_empty_video(samples, tran_script_key, phase)
    samples = format_input(samples, tran_script_key, phase)
    yield from to_crawl_in(samples, prompt_path)

@checkpoint_to_file
def pipeline_crawl_output_filter(crawl_out_path):
    """
    阶段2：处理爬取输出
    读取爬虫结果 -> 过滤不合格
    """
    # 这里直接读文件即可，read_jsonl在common_utils里
    samples = read_jsonl(crawl_out_path) 
    yield from filter_video_logic(samples)

@checkpoint_to_file
def pipeline_latex_filter(orig_data_path, tran_script_key, phase):
    """
    阶段3：Latex 过滤
    读取 -> 格式化 -> 请求服务过滤
    """
    samples = read_init_data(orig_data_path)
    samples = filter_empty_video(samples, tran_script_key, phase)
    samples = format_input(samples, tran_script_key, phase)
    yield from filter_latex_logic(samples)

@checkpoint_to_file
def pipeline_analysis_filter(analysis_result_paths):
    """
    阶段4：解析过滤继承
    """
    # 支持多个路径pattern
    samples = read_jsonl(analysis_result_paths)
    yield from filter_analysis_logic(samples)

@checkpoint_to_file
def pipeline_combine_all(orig_data_path, video_res_path, analysis_res_path, latex_res_path):
    """
    阶段5：综合所有结果
    注意：这里需要把前面步骤生成的文件读进来
    """
    # 1. 原始数据 (作为基准流)
    samples_orig = read_init_data(orig_data_path)
    
    # 2. 读取各阶段的中间结果 (List化以便查找，如果数据量巨大需优化逻辑)
    # 因为要构建 id2result 字典，必须先加载到内存
    samples_video = list(read_jsonl(video_res_path))
    samples_analysis = list(read_jsonl(analysis_res_path))
    samples_latex = list(read_jsonl(latex_res_path))
    
    yield from filter_all_logic(samples_orig, samples_video, samples_analysis, samples_latex)


# ==================== Main ====================

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", type=str, choices=["小学", "初中"], default="初中")
    parser.add_argument("--part", type=str, default="1")
    parser.add_argument("--tran_script_key", "--tkey", type=str, default=".tran_script[].tranScript")
    parser.add_argument("--prompt_path", "--ppath", type=str, default="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/效果验证/小初单模视频逐字稿+读题筛选prompt_P1127.md")
    parser.add_argument("--save_dir", "--sdir", type=str, default="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次")
    parser.add_argument("--stage", type=str, required=True, 
                        choices=["保存爬取输入", "爬取输出结果", "latex过滤结果", "解析过滤结果", "综合过滤结果"])
    parser.add_argument("--orig_data_path", type=str, default="/mnt/pan8T/topic_repair/jianwang25_topic_source_data/xiaoshu_sm/all_json/part-00001-3e3ce051-8a5e-40ad-997f-eac4fbd5e7af-c000")
    # 支持 list 参数
    parser.add_argument("--analysis_result_path", type=str, nargs="+", default=["/mnt/pan8T/temp_jiahe3/results/junior/3kw/final_result_check_latex_html/*json"])
    
    args = parser.parse_args()

    # 预定义文件路径规则 (集中管理路径，避免散落在各处)
    path_crawl_in = Path(f"{args.save_dir}", f"{args.phase}单模视频质量过滤爬取输入", f"{args.phase}_单模_part{args.part}_video_check_crawl_in.json").as_posix()
    
    # 假设爬取输出的文件名规则（通常是输入文件名改一下后缀，或者是人工指定）
    # 这里假设输入文件跑完模型后，放在 "爬取输出" 目录
    path_crawl_out = Path(f"{args.save_dir}", f"{args.phase}单模视频质量过滤爬取输出", f"{args.phase}_单模_part{args.part}_video_check_crawl_out.json").as_posix()
    
    path_video_res = Path(f"{args.save_dir}", f"{args.phase}单模视频过滤结果", f"{args.phase}_单模_part{args.part}_video_check_result.json").as_posix()
    path_latex_res = Path(f"{args.save_dir}", f"{args.phase}单模视频latex过滤结果", f"{args.phase}_单模_part{args.part}_latex_check_result.json").as_posix()
    path_analysis_res = Path(f"{args.save_dir}", f"{args.phase}单模视频解析过滤继承结果", f"{args.phase}_单模_analysis_check_result.json").as_posix()
    path_final_res = Path(f"{args.save_dir}", f"{args.phase}单模视频综合过滤结果", f"part{args.part}_video_check_result.json").as_posix()

    print(f"当前阶段: {args.stage}")
    
    # ==================== 执行逻辑 ====================
    # 使用方式： func(save_path=..., mode="write")(业务参数...)

    if args.stage == "保存爬取输入":
        pipeline_crawl_input(
            save_path=path_crawl_in, 
            mode="write", 
            overwrite=True  # 通常生成输入是第一步，可以覆盖
        )(
            orig_data_path=args.orig_data_path,
            tran_script_key=args.tran_script_key,
            phase=args.phase,
            prompt_path=args.prompt_path
        )

    elif args.stage == "爬取输出结果":
        pipeline_crawl_output_filter(
            save_path=path_video_res,
            mode="write"
        )(
            crawl_out_path=path_crawl_out
        )

    elif args.stage == "latex过滤结果":
        pipeline_latex_filter(
            save_path=path_latex_res,
            mode="write"
        )(
            orig_data_path=args.orig_data_path,
            tran_script_key=args.tran_script_key,
            phase=args.phase
        )

    elif args.stage == "解析过滤结果":
        pipeline_analysis_filter(
            save_path=path_analysis_res,
            mode="write"
        )(
            analysis_result_paths=args.analysis_result_path
        )

    elif args.stage == "综合过滤结果":
        # 这一步依赖前面的结果文件存在
        pipeline_combine_all(
            save_path=path_final_res,
            mode="write"
        )(
            orig_data_path=args.orig_data_path,
            video_res_path=path_video_res,
            analysis_res_path=path_analysis_res,
            latex_res_path=path_latex_res
        )