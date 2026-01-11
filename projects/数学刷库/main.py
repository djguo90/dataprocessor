"""
数学单模视频清洗
"""
import json
from pathlib import Path
from json_process_funcs import read_jsonl, get_values_by_key_path, save_jsonl
import requests
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 读取原始数据
def read_init_data(data_path):
    yield from read_jsonl(data_path)

# 过滤无视频数据
def filter_empty_video(samples, tran_script_key, phase):
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
            if phase == "初中":
                assert "content" in tran_script["scienceStruct"]
                assert "readQuestion" in tran_script["scienceStruct"]
                assert "analyses" in tran_script["scienceStruct"]
                assert "standardAnswers" in tran_script["scienceStruct"]
                assert "conclusion" in tran_script["scienceStruct"]
            elif phase == "小学":  # NOTE 未验证过
                assert "content" in tran_script["scienceStruct"]
                assert "readQuestion" in tran_script["scienceStruct"]
                assert "analyse" in tran_script["scienceStruct"]
                assert "standardAnswer" in tran_script["scienceStruct"]
                assert "conclusion" in tran_script["scienceStruct"]
            else:
                continue
        except:
            continue
        yield sample

# 数据格式化
def format_input(samples, tran_script_key, phase):
    for sample in samples:
        tran_script = get_values_by_key_path(sample, tran_script_key)[0]
        if isinstance(tran_script, str):
            tran_script = json.loads(tran_script)
        if phase == "初中":
            video_cont = tran_script["scienceStruct"]["content"]
            video_read = tran_script["scienceStruct"]["readQuestion"]
            video_analyses = tran_script["scienceStruct"]["analyses"]
            video_answers = tran_script["scienceStruct"]["standardAnswers"]
            video_conclusion = tran_script["scienceStruct"]["conclusion"]
        elif phase == "小学":
            video_cont = tran_script["scienceStruct"]["content"]
            video_read = tran_script["scienceStruct"]["readQuestion"]
            video_analyse = tran_script["scienceStruct"]["analyse"]
            video_answer = tran_script["scienceStruct"]["standardAnswer"]
            video_conclusion = tran_script["scienceStruct"]["conclusion"]
            video_analyses = [video_analyse]
            video_answers = [video_answer]
        else:
            continue
        assert len(video_analyses) == len(video_answers)
        assert len(video_analyses) >= 1

        result = {}
        result["读题"] = {"讲解内容": video_read["explainContent"]}
        for i, (ana, ans) in enumerate(zip(video_analyses, video_answers)):
            if len(video_analyses) == 1:
                result[f"分析"] = {"讲解内容": ana["explainContent"], "展示内容": ana["displayContent"]}
                result[f"标准作答"] = {"讲解内容": ans["explainContent"], "展示内容": ans["displayContent"]}
            else:
                result[f"分析{i+1}"] = {"讲解内容": ana["explainContent"], "展示内容": ana["displayContent"]}
                result[f"标准作答{i+1}"] = {"讲解内容": ans["explainContent"], "展示内容": ans["displayContent"]}
        result["总结"] = {"讲解内容": video_conclusion["explainContent"], "展示内容": video_conclusion["displayContent"]}
        final_result = {"id": sample["topic_id"], "video_question": video_cont, "video": result}
        yield final_result

# 转为视频过滤爬取输入格式
def to_crawl_in(samples, prompt_path):
    with open(prompt_path) as reader:
        prompt_template = reader.read().strip()
    for sample in samples:
        prompt = prompt_template.replace("{{ques}}", sample["video_question"]).replace("{{video}}", json.dumps(sample["video"], ensure_ascii=False, indent=2))
        sample["query"] = prompt
        yield sample

# 保存爬取输入
def save_crawl_in(samples, save_dir, part, phase):
    save_path = Path(f"{save_dir}", f"{phase}单模视频质量过滤爬取输入", f"{phase}_单模_part{part}_video_check_crawl_in.json").as_posix()
    save_jsonl(samples, save_path, overwrite=True)
    return save_path

# 读取爬取输出结果
def read_crawl_out(save_dir, part, phase):
    path = Path(f"{save_dir}", f"{phase}单模视频质量过滤爬取输出", f"{phase}_单模_part{part}_video_check_crawl_out.json").as_posix()
    yield from read_jsonl(path)

# 解析视频拒识结果
def filter_video(samples):
    for sample in samples:
        answer = sample["answer"]
        if '"审核结果": "不合格"' in answer:
            result = {"topic_id": sample["id"], "tran_script_version": "单模视频过滤", "tran_script_operate_type": "null"}
            yield result

# 保存视频拒识结果
def save_filter_video_result(samples, save_dir, part, phase):
    save_path = Path(f"{save_dir}", f"{phase}单模视频过滤结果", f"{phase}_单模_part{part}_video_check_result.json").as_posix()
    save_jsonl(samples, save_path)
    return save_path

# 读取视频拒识结果
def read_filter_video_result(save_dir, part, phase):
    save_path = Path(f"{save_dir}", f"{phase}单模视频过滤结果", f"{phase}_单模_part{part}_video_check_result.json").as_posix()
    yield from read_jsonl(save_path)

# latex过滤
def create_retry_session(retries=3, backoff_factor=0.5, timeout=30):
    """
    创建带有重试机制的requests会话
    
    Args:
        retries: 最大重试次数
        backoff_factor: 重试间隔系数（间隔时间 = backoff_factor * (2 ** (重试次数 - 1))）
        timeout: 请求超时时间（秒）
    
    Returns:
        requests.Session: 配置好的会话对象
    """
    # 配置重试策略
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],  # 这些状态码触发重试
        allowed_methods=["POST"]  # 允许重试的请求方法
    )
    
    # 创建适配器并挂载到会话
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # 设置默认超时
    session.timeout = timeout
    
    # 添加请求头，模拟浏览器请求（避免被服务器识别为爬虫）
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Content-Type': 'application/json',
        'Connection': 'keep-alive'
    })
    
    return session

# 修改你原来的请求代码（对应main.py第149行）
def safe_post_request(url, payload, max_attempts=5):
    """
    安全的POST请求函数，包含重试和异常处理
    
    Args:
        url: 请求地址
        payload: 请求体
        max_attempts: 最大尝试次数
    
    Returns:
        requests.Response: 响应对象 | None
    """
    # 创建带重试机制的会话
    session = create_retry_session(retries=3, timeout=60)
    
    attempt = 0
    while attempt < max_attempts:
        try:
            # 发送POST请求
            response = session.post(url, json=payload)
            
            # 检查响应状态码
            response.raise_for_status()  # 非2xx状态码会抛出HTTPError
            return response
            
        except requests.exceptions.ConnectionError as e:
            attempt += 1
            wait_time = 2 ** attempt  # 指数退避等待
            print(f"连接错误: {e}，第 {attempt} 次重试，等待 {wait_time} 秒...")
            time.sleep(wait_time)
            
        except requests.exceptions.Timeout as e:
            attempt += 1
            wait_time = 2 ** attempt
            print(f"请求超时: {e}，第 {attempt} 次重试，等待 {wait_time} 秒...")
            time.sleep(wait_time)
            
        except requests.exceptions.HTTPError as e:
            print(f"HTTP错误: {e}，状态码: {response.status_code}")
            return None
            
        except Exception as e:
            print(f"未知错误: {e}")
            return None
    
    print(f"已尝试 {max_attempts} 次，请求失败")
    return None

def filter_latex(samples):
    import re
    import requests
    url = "http://localhost:3000/latex2html"
    for sample in samples:
        assert "id" in sample
        is_latex_good = True
        question = sample["video_question"]
        video = sample["video"]
        video_display = []
        for k in video:
            # print(video[k])
            if "展示内容" in video[k]:
                if not k.startswith("标准作答"):
                    video_display.extend(list(video[k]["展示内容"].keys()))
                else:
                    video_display.extend(video[k]["展示内容"])
        video_display = [question] + video_display
        for c in video_display:
            # c = re.sub(r'(\n\t)(?!\w)', "", c)
            # c = c.replace("\"", "'")
            c = c.replace("\tau", "\\tau").replace("\triangle", "\\triangle").replace("\times", "\\times").replace("\therefore", "\\therefore")
            c = c.replace("\text", "\\text")
            c = c.replace("\neg", "\\neg").replace("\neq", "\\neq").replace("\nabl", "\\nabl").replace("\newline", "\\newline")
            c = c.replace("\t", "").replace("\n", "").replace("\"", "'")
            c_dump = json.dumps(c, ensure_ascii=False)
            if ("\\" in c_dump or "^" in c_dump) and "$" not in c:
                # print(c_dump)
                is_latex_good = False
                break
        video_display_str = "\n".join(video_display)
        if re.search(r'[a-zA-Z]', video_display_str) is None:
            # print(display_q)
            # print("*"*100)
            continue
        payload = {"text": video_display_str}
        response = safe_post_request(url, payload)
        if response is None:
            print(f"ID {sample['id']} 未响应")
        else:
            if response.status_code == 200:
                data = response.json()
                code = data.get("code")
                if code != 200:
                    is_latex_good = False
        if not is_latex_good:
            result = {"topic_id": sample["id"], "tran_script_version": "单模视频latex过滤", "tran_script_operate_type": "null"}
            yield result

# 保存latex过滤结果
def save_filter_latex_result(samples, save_dir, part, phase):
    save_path = Path(f"{save_dir}", f"{phase}单模视频latex过滤结果", f"{phase}_单模_part{part}_latex_check_result.json").as_posix()
    save_jsonl(samples, save_path)
    return save_path

# 读取latex过滤结果
def read_filter_latex_result(save_dir, part, phase):
    save_path = Path(f"{save_dir}", f"{phase}单模视频latex过滤结果", f"{phase}_单模_part{part}_latex_check_result.json").as_posix()
    yield from read_jsonl(save_path)

# 读取解析结果
def read_analysis_result(analysis_result_path):
    yield from read_jsonl(analysis_result_path)

# 解析过滤结果
def filter_analysis(samples):
    for sample in samples:
        if sample["analysis_operate_type"] in ["delete", "null"]:
            result = {"topic_id": sample["topic_id"], "tran_script_version": "单模视频解析过滤继承", "tran_script_operate_type": "null"}
            yield result

# 保存解析过滤结果
def save_filter_analysis_result(samples, save_dir, phase):
    save_path = Path(f"{save_dir}", f"{phase}单模视频解析过滤继承结果", f"{phase}_单模_analysis_check_result.json").as_posix()
    save_jsonl(samples, save_path)
    return save_path

# 读取解析过滤结果
def read_filter_analysis_result(save_dir, phase):
    save_path = Path(f"{save_dir}", f"{phase}单模视频解析过滤继承结果", f"{phase}_单模_analysis_check_result.json").as_posix()
    yield from read_jsonl(save_path)

# 综合过滤
def filter_all(samples_orig, samples_video, samples_analysis, samples_latex):
    id2result = {}
    for l_json in samples_latex:
        id2result[l_json["topic_id"]] = l_json
    for l_json in samples_analysis:
        id2result[l_json["topic_id"]] = l_json
    for l_json in samples_video:
        id2result[l_json["topic_id"]] = l_json
    for sample in samples_orig:
        if "topic_id" not in sample:
            continue
        if sample["topic_id"] in id2result:
            yield id2result[sample["topic_id"]]
        else:
            yield {"topic_id": sample["topic_id"], "tran_script_version": "单模视频过滤", "tran_script_operate_type": "same"}

# 保存综合过滤结果
def save_filter_all_result(samples, save_dir, part, phase):
    save_path = Path(f"{save_dir}", f"{phase}单模视频综合过滤结果", f"part{part}_video_check_result.json").as_posix()
    save_jsonl(samples, save_path)
    return save_path

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", type=str, choices=["小学", "初中"], default="初中", help="学段")
    parser.add_argument("--part", type=str, default="1", help="数据part，注意下面的orig_data_path可以根据这个参数指定，如果只有一个part，可以不用")
    parser.add_argument("--tran_script_key", "--tkey", type=str, default=".tran_script[].tranScript", help="视频脚本所在字段")
    parser.add_argument("--prompt_path", "--ppath", type=str, default="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/效果验证/小初单模视频逐字稿+读题筛选prompt_P1127.md", help="视频脚本过滤的prompt")
    parser.add_argument("--save_dir", "--sdir", type=str, default="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次", help="保存结果的路径")
    parser.add_argument("--stage", type=str, default="latex过滤结果", choices=["保存爬取输入", "爬取输出结果", "latex过滤结果", "解析过滤结果", "综合过滤结果"], help="不同的阶段")
    parser.add_argument("--orig_data_path", type=str, default="/mnt/pan8T/topic_repair/jianwang25_topic_source_data/xiaoshu_sm/all_json/part-00001-3e3ce051-8a5e-40ad-997f-eac4fbd5e7af-c000")
    parser.add_argument("--analysis_result_path", type=str, nargs="+", default=["/mnt/pan8T/temp_jiahe3/results/junior/3kw/final_result_check_latex_html/*json"])
    args = parser.parse_args()

    # # 初数单模
    # orig_data_path = f"/mnt/pan8T/topic_repair/jianwang25_topic_source_data/xiaoshu_sm/all_json/part-{int(args.part):05d}-3e3ce051-8a5e-40ad-997f-eac4fbd5e7af-c000"
    # analysis_result_path = "/mnt/pan8T/temp_jiahe3/results/junior/3kw/final_result_check_latex_html/*json"

    # 保存爬取输入
    if args.stage == "保存爬取输入":
        samples = read_init_data(args.orig_data_path)
        samples = filter_empty_video(samples, args.tran_script_key, args.phase)
        samples = format_input(samples, args.tran_script_key, args.phase)
        samples = to_crawl_in(samples, args.prompt_path)
        save_crawl_in(samples, args.save_dir, args.part, args.phase)
    # 视频过滤结果
    elif args.stage == "爬取输出结果":
        samples = read_crawl_out(args.save_dir, args.part, args.phase)
        samples = filter_video(samples)
        save_filter_video_result(samples, args.save_dir, args.part, args.phase)
    
    # latex过滤结果
    elif args.stage == "latex过滤结果":
        samples = read_init_data(args.orig_data_path)
        samples = filter_empty_video(samples, args.tran_script_key, args.phase)
        samples = format_input(samples, args.tran_script_key, args.phase)
        samples = filter_latex(samples)
        save_filter_latex_result(samples, args.save_dir, args.part, args.phase)
    # 解析过滤结果
    elif args.stage == "解析过滤结果":
        samples = read_analysis_result(args.analysis_result_path)
        samples = filter_analysis(samples)
        save_filter_analysis_result(samples, args.save_dir, args.phase)
    # 综合过滤
    elif args.stage == "综合过滤结果":
        samples_orig = read_init_data(args.orig_data_path)
        samples_analysis = read_filter_analysis_result(args.save_dir, args.phase)
        samples_latex = read_filter_latex_result(args.save_dir, args.part, args.phase) 
        samples_video = read_filter_video_result(args.save_dir, args.part, args.phase)
        samples = filter_all(samples_orig, samples_video, samples_analysis, samples_latex)
        save_filter_all_result(samples, args.save_dir, args.part, args.phase)




    # with open("/mnt/pan8T/temp_djguo/存量库清洗-初中单模/代码/test_data/初中单模视频过滤爬取输出/初中_单模_part1_video_check_crawl_out_orig.json") as reader, \
    #      open("/mnt/pan8T/temp_djguo/存量库清洗-初中单模/代码/test_data/初中单模视频过滤爬取输出/初中_单模_part1_video_check_crawl_out.json", "w") as writer:
    #      for l in reader:
    #          l = json.loads(l)
    #          l.pop("crawl_prompt_tokens")
    #          l.pop("crawl_completion_tokens")
    #          l.pop("crawl_state")
    #          l["answer"] = l["crawl_messages"][-1]["content"]
    #          l.pop("crawl_messages")
    #          writer.write(json.dumps(l, ensure_ascii=False) + "\n")