# -*- coding: utf-8 -*-
import os
import time
import json
import re
import argparse
import logging
import requests
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple, Union, Optional, Any, Set

FilePath = Union[str, os.PathLike]
MetricType = Dict[str, Union[int, float, str]]
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(module)s:%(lineno)d - %(levelname)s: %(message)s")
logger = logging.getLogger(__file__)


def batch_unzip(directory: str, delete_zip: bool = True, delete_failed: bool = True, 
                extract_dir: str = None, override: bool = False, prefix_pattern=None):
    # 检查目录是否存在
    if not os.path.isdir(directory):
        raise ValueError(f"目录不存在: {directory}")

    success_count = 0
    fail_count = 0

    # 遍历目录中的所有文件
    for filename in os.listdir(directory):
        # 检查是否为zip文件
        if filename.lower().endswith('.zip'):
            zip_path = os.path.join(directory, filename)
            if extract_dir is None:
                extract_dir = directory
            else:
                os.makedirs(extract_dir, exist_ok=True)
            try:
                json_filename = filename.replace(".zip", ".json")
                if prefix_pattern:
                    new_name = re.sub(prefix_pattern, "", json_filename)
                # json_file = os.path.join(extract_dir, json_filename)
                # if os.path.exists(json_file) and not override:
                #     print(f"文件已存在: {json_file}")
                #     continue

                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)

                os.rename(os.path.join(extract_dir, json_filename), os.path.join(extract_dir, new_name))
                logger.info(f"成功解压: {filename} -> {json_filename}")
                success_count += 1
                if delete_zip:
                    os.remove(zip_path)
                    logger.info(f"删除压缩包: {zip_path}")
            except Exception as e:
                logger.error(f"解压失败 {filename}: {str(e)}")
                fail_count += 1
                if delete_failed:
                    os.remove(zip_path)
                    logger.info(f"删除失败压缩包: {zip_path}")
                    
    
    logger.info(f"\n解压完成 - 成功: {success_count}, 失败: {fail_count}")
    if fail_count > 0:
        return False
    return True


def move_files(src_dir, dst_dir, file_type=".zip"):
    """
    将 src_dir 目录及其所有子目录中的 file_type 文件移动到 dst_dir 目录。

    参数:
        src_dir (str): 源目录路径
        dst_dir (str): 目标目录路径
        file_type (str): 文件类型，默认值为 ".zip"

    返回:
        None
    """
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir, exist_ok=True)

    for dirpath, _, filenames in os.walk(src_dir):
        for filename in filenames:
            if filename.lower().endswith(file_type):
                old_path = os.path.join(dirpath, filename)
                new_path = os.path.join(dst_dir, filename)
                # # 若目标已存在同名文件，可追加序号避免覆盖
                # counter = 1
                # base_name, ext = os.path.splitext(filename)
                # while os.path.exists(new_path):
                #     new_name = f"{base_name}_{counter}{ext}"
                #     new_path = os.path.join(dst_dir, new_name)
                #     counter += 1
                os.rename(old_path, new_path)
                logger.info(f"移动 zip 文件：{old_path} -> {new_path}")


def get_file_line_count(filepath):
    with open(filepath, "r", encoding="utf-8") as fp:
        line_count = sum(1 for l in fp if l.strip())
    return line_count


def check_latex_format_api(text: str) -> bool:
    try:
        url = "http://localhost:3000/latex2html"
        # url = "http://172.30.94.254:3000/latex2html"
        payload = {
            "text": text
        }
        # 发送 POST 请求
        response = requests.post(url, json=payload)
        # 输出响应
        if response.status_code == 200:
            data = response.json()
            code = data.get("code")
            if code == 200:
                return True
            else:
                return False
        else:
            logger.error(f"检查LaTeX格式API返回异常：{response.status_code}")
            return True
    except Exception as e:
        logger.error(f"检查LaTeX格式API异常：{e}")
        return True
   

def check_question_latex_format(question) -> bool:
    text = question["content"] + "\n".join(question["options"])
    match = re.search("[a-zA-Z]+", text)
    if match is None:
        return True

    if '\x0crac' in text:
        logger.debug(f"转移字符错误！")
        return False
    return check_latex_format_api(text)


def check_preset_options(questions: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Dict[str, Any]]]:
    preset_questions = dict()
    for qid, question in questions.items():
        try:
            options = question.get("options")
            if options is None:
                logger.debug("预置问题选项缺失")
                continue

            answer = question.get("answer")
            if answer is None:
                logger.debug("预置问题答案缺失")
                continue

            if answer not in options:
                logger.debug(f"预置问题答案不在选项中： {question}")
                continue

            if '不知道' not in options:
                logger.debug(f"预置问题选项中缺失'不知道'： {question}")
                continue

            if len(options) > 4 or len(options) < 3:
                logger.debug(f"有效选项超过规定： {options}")
                continue

            if len(options) != len(set(options)):
                logger.debug(f"选项中存在重复元素： {options}")
                continue

            preset_questions[qid] = question
        except Exception as e:
            logger.error(f"预置问题结构异常({e})：{question}")
            continue

    if len(preset_questions) == 0:
        return None

    return preset_questions


def check_preset_position(questions: Dict[str, Dict[str, Any]], explain: str) -> Dict[str, Dict[str, Any]]:
    preset_questions = dict()
    for qid, question in questions.items():
        position = question.get("position")
        if position is None:
            logger.debug(f"预置问题位置缺失： {question}")
            continue

        if position not in explain:
            logger.debug(f"预置问题位置不在逐字稿中： {question}")
            continue

        preset_questions[qid] = question

    if len(preset_questions) == 0:
        return None

    return preset_questions


def question_preprocess(question):
    question = question.replace("\\enter", "")
    question = re.sub("(?:&nbsp;)+", " ", question)
    question = question.replace("ifly-latex-begin", "$").replace("ifly-latex-end", "$")
    question = re.sub(r"<question_number>(.+?)</question_number>", r"\1", question, flags=re.S)
    question = re.sub(r"<underline>(.+?)</underline>", r"\1", question, flags=re.S)
    question = re.sub(r"<answerarea></answerarea>", "()", question)
    question = re.sub(r"<answerarea>(.+?)</answerarea>", r"\1", question)
    question = question.replace("<img />", "")
    question = question.strip()
    return question.strip()


def extract_paths(line, level: str, mode):
    try:
        if level == "primary":
            if mode == "online":
                preset_question = line["presetQuestion"]["scienceStruct"] #小学重刷
            else:
                preset_question = line["preset_question"][0]["presetQuestion"] # 小学题库
                preset_question = json.loads(preset_question)["scienceStruct"]
        else:
            if mode == "online":
                preset_question = line["guidLearnStruct"]["presetQuestion"]["scienceStruct"] # 初中重刷
            else:
                preset_question = line["guidLearnStruct"]["presetQuestion"]["scienceStruct"] # 初中重刷
    except Exception as e:
        return None
    
    try:
        if level == "primary":
            if mode == "online":
                tran_script = line["tranScript"]["scienceStruct"]["analyse"]["explainContent"] #小学重刷     
            else:
                tran_script = line["tran_script"][0]["tranScript"] #小学题库 
                tran_script = json.loads(tran_script)
                tran_script = tran_script["scienceStruct"]["analyse"]["explainContent"]   
        else:
            if mode == "online":
                tran_script =  line["guidLearnStruct"]["tranScript"]["scienceStruct"]["analyses"] # 初中重刷
            else:
                tran_script =  line["guidLearnStruct"]["tranScript"]["scienceStruct"]["analyses"] # 初中重刷
    except Exception as e:
        return None
    
    tid = line.get("topic_id") or line.get("topicId")
    if tid is None:
        raise ValueError("topic_id not found in line")
    line = {
        "topic_id": tid,
        "tran_script": tran_script,
        "preset_question": preset_question,
        "preset_question_operate_type": line.get("preset_question_operate_type", ""),
    }
    return line
 

def extract_primary_from_offline(line):
    try:
        if line.get("tran_script") is None:
            return None
        tran_script = line["tran_script"]
        assert len(tran_script) == 1, f"tran_script字段长度不是1：{len(tran_script)}"
        tran_script = tran_script[0]
        if tran_script.get("tranScript") is None:
            return None
        tran_script = tran_script["tranScript"]
        tran_script = json.loads(tran_script)
        tran_script = tran_script["scienceStruct"]["analyse"]["explainContent"]

        preset_question = line["preset_question"]
        assert len(preset_question) == 1, f"preset_question字段长度不是1：{len(preset_question)}"
        preset_question = preset_question[0]
        if preset_question.get("presetQuestion") is None:
            return None
        preset_question = preset_question["presetQuestion"]
        preset_question = json.loads(preset_question)
        preset_question = preset_question["scienceStruct"]

        tid = line["topic_id"]
        line = {
            "topic_id": tid,
            "tran_script": tran_script,
            "preset_question": preset_question,
        }
        return line
    except Exception as e:
        logger.error(f"错误信息：{e}")
        return None


def update_primary_to_offline(line, questions, reflash=False):
    try:
        if reflash:
            preset_question = line["presetQuestion"]["scienceStruct"] # 小学重刷
        else:
            preset_question = json.loads(line["preset_question"][0]["presetQuestion"])["scienceStruct"] # 小学题库
    except Exception as e:
        preset_question = None
    
    if preset_question:
        if questions:
            if len(questions) != len(preset_question):
                operate_type = "update"
                preset_question = {"scienceStruct": questions, "ttsUrl": None}
            else:
                operate_type = "same"
                preset_question = None
        else:
            operate_type = "null"
            preset_question = {"scienceStruct": None, "ttsUrl": None}
    else:
        operate_type = "same"

    line = {
        "topic_id": line["topic_id"],
        "preset_question_operate_type": operate_type,
        "preset_question_version": "filter_preset_question_1113"      
    }

    if preset_question:
        line["preset_question"] = preset_question 
 
    return line
    

def extract_junior_from_offline(line):
    preset_questions = line.get("preset_question")
    if preset_questions is None:
        return None

    tran_scripts = line.get("tran_script")
    if tran_scripts is None:
        return None 

    def group_preset_question(preset_question):
        questions = {}
        for key, pq in preset_question.items():
            idx = pq.get("index", 0)
            idx = int(idx)
            if questions.get(idx) is None:
                questions[idx] = {}     
            questions[idx][key] = pq
        return questions

    scripts = {}
    for tran_script in tran_scripts:
        bid = tran_script["index"]
        try:
            tran_script = json.loads(tran_script["tranScript"])["scienceStruct"]["analyses"]
        except KeyError as e:
            continue
        except json.JSONDecodeError as e:
            continue
        
        tran_script = {i: s["explainContent"] for i, s in enumerate(tran_script)}
        scripts[bid] = tran_script
    
    if len(scripts) == 0:
        return None
    
    items = dict()
    for preset_question in preset_questions:
        bid = preset_question["index"]
        if bid not in scripts:
            continue

        try:
            preset_question = json.loads(preset_question["presetQuestion"])["scienceStruct"]
        except KeyError as e:
            continue
        except json.JSONDecodeError as e:
            continue
        
        preset_question = group_preset_question(preset_question)
        for gid, qs in preset_question.items():
            script = scripts[bid].get(gid)
            if script is None:
                continue
            
            if items.get(bid) is None:
                items[bid] = {}
           
            items[bid][gid] = {"preset_question": qs, "tran_script": script}
                   
    if len(items) == 0:
        return None
    
    tid = line["topic_id"]
    content = line["content"]["txt"]
    content = question_preprocess(content)

    line = {
        "topic_id": tid,
        "content": content,
        "items": items,
    }

    return line


def update_junior_to_offline(line, questions):
    def _expand_result_questions(items):
        questions = {}
        for idx, q in items.items():
            key = idx.split("#")[-1]
            questions[key] = q
        return questions

    try: 
        preset_question = json.loads(line["preset_question"][0]["presetQuestion"])["scienceStruct"] # 小学多模冲刷
        # preset_question = line["guidLearnStruct"]["presetQuestion"]["scienceStruct"]["scienceStruct"]
    except Exception as e:
        preset_question = None
        operate_type = "same"
        line = {
            "topic_id": line["topic_id"],
            "preset_question_operate_type": operate_type,
            "preset_question_version": "filter_preset_question_1113"
        }
        return line

    if questions:
        
        questions = _expand_result_questions(questions)
        if len(questions) != len(preset_question):
            operate_type = "update"
        else:
            operate_type = "same"
    else:
        operate_type = "null"      
    if operate_type == "same":
        line = {
            "topic_id": line["topic_id"],
            "preset_question_operate_type": operate_type,
            "preset_question_version": "filter_preset_question_1113"
        }
    else:
        line = {
            "topic_id": line["topic_id"],
            "preset_question_operate_type": operate_type,
            "preset_question_version": "filter_preset_question_1113",
            "preset_question": {"scienceStruct": questions, "ttsUrl": None}      
        }

    return line


def extract_primary_from_close(line):
    try: 
        preset_question = line["presetQuestion"]["scienceStruct"]
        # preset_question = line["guidLearnStruct"]["presetQuestion"]["scienceStruct"]["scienceStruct"]
    except Exception as e:
        return None
        
    try:
        tran_script = line["tranScript"]["scienceStruct"]["analyse"]["explainContent"]
        # tran_script = line["guidLearnStruct"]["tranScript"]["scienceStruct"]["scienceStruct"]["analyse"]["explainContent"]
    except Exception as e:
        return None

    tid = line.get("topic_id") or line.get("topicId")
    if tid is None:
        raise ValueError("topic_id not found in line")
    line = {
        "topic_id": tid,
        "tran_script": tran_script,
        "preset_question": preset_question,
        "preset_question_operate_type": line.get("preset_question_operate_type", ""),
    }
    return line


def update_primary_to_close(line, questions):
    try: 
        preset_question = line["presetQuestion"]["scienceStruct"] # 小学多模冲刷
        # preset_question = line["guidLearnStruct"]["presetQuestion"]["scienceStruct"]["scienceStruct"]
    except Exception as e:
        preset_question = None
        # operate_type = "same"
        operate_type = "null" # NOTE 可能根据需求修改

    if preset_question:
        if questions:
            if len(questions) != len(preset_question):
                operate_type = "update"
            else:
                operate_type = "same"
        else:
            operate_type = "null"
        
        line["presetQuestion"]["scienceStruct"] = questions
        #line["guidLearnStruct"]["presetQuestion"]["scienceStruct"]["scienceStruct"] = questions
    line["preset_question_operate_type"] = operate_type
    return line
 

def update_primary_to_online_reflash(line, questions):
    try: 
        preset_question = line["presetQuestion"]["scienceStruct"] # 小学多模冲刷
        # preset_question = line["guidLearnStruct"]["presetQuestion"]["scienceStruct"]["scienceStruct"]
    except Exception as e:
        preset_question = None
        operate_type = "null"

    if preset_question:
        if questions:
            operate_type = "update"
        else:
            operate_type = "null"
        
    line = {
            "topic_id": line["topic_id"],
            "preset_question_operate_type": operate_type,
            "preset_question_version": "filter_preset_question_1113",
            "preset_question": {"scienceStruct": questions, "ttsUrl": None}      
        }
    
    return line
 


def extract_junior_from_close(line):
    try:    
        preset_question = line["guidLearnStruct"]["presetQuestion"]["scienceStruct"]
    except Exception as e:
        return None
    
    try:
        tran_script =  line["guidLearnStruct"]["tranScript"]["scienceStruct"]["analyses"]
    except Exception as e:
        return None
    
    def group_preset_question(preset_question):
        questions = {}
        for key, pq in preset_question.items():
            idx = pq.get("index", 0)
            idx = int(idx)
            if questions.get(idx) is None:
                questions[idx] = {}     
            questions[idx][key] = pq
        return questions
    
    preset_question = group_preset_question(preset_question)
    tran_script = {i: s["explainContent"] for i, s in enumerate(tran_script)}

    if len(tran_script) > len(preset_question):
        tran_script = {bid: script for bid, script in tran_script.items() if bid in preset_question}
    
    assert len(tran_script) == len(preset_question), f"tran_script字段长度不是preset_question字段长度：{len(tran_script)} != {len(preset_question)}"
    
    items = {"00": dict()}
    for bid, qs in preset_question.items():
        script = tran_script.get(bid)
        if script is None:
            continue
        items["00"][bid] = {"preset_question": qs, "tran_script": script}
    if len(items["00"]) == 0:
        return None
    
    tid = line["topicId"]
    content = line["guidLearnStruct"]["tranScript"]["scienceStruct"]["content"]
    content = question_preprocess(content)
    
    line = {
        "topic_id": tid,
        "content": content,
        "items": items,
    }
    return line


def update_junior_to_close(line, questions):
    def _expand_result_questions(items):
        questions = {}
        for idx, q in items.items():
            key = idx.split("#")[-1]
            questions[key] = q
        return questions

    try:    
        preset_question = line["guidLearnStruct"]["presetQuestion"]["scienceStruct"]
    except Exception as e:
        preset_question = None
        line["preset_question_operate_type"] = "same"

    if preset_question:
        if questions:
            
            questions = _expand_result_questions(questions)
            if len(questions) != len(preset_question):
                preset_question_operate_type = "update"
            else:
                preset_question_operate_type = "same"
        else:
            preset_question_operate_type = "null"      
            
        line["guidLearnStruct"]["presetQuestion"]["scienceStruct"] = questions
        line["preset_question_operate_type"] = preset_question_operate_type

    return line


class PresetQuestionManager:
    def __init__(self,
                 step: str,
                 enable_prefilter: bool = False,
                 enable_latex_check: bool = False,
                 enable_duplicate_check: bool = False,
                 mode: str = "offline",
                 level: str = "sj",
                 ):
        self.step = step
        self.mode = mode
        self.level = level
        self.enable_latex_check = enable_latex_check
        self.enable_duplicate_check = enable_duplicate_check
        self.enable_prefilter = enable_prefilter

        self.total_count = 0
        self.valid_count = 0

        self.error_count = 0
        self.duplicate_count = 0
        self.json_decode_error_count = 0
        self.latex_error_count = 0

        self.prompt_template = None
        self.request_count = 0

        self.null_count = 0
        self.update_count = 0
        self.same_count = 0

        self.state_null = set()
        self.script_state_dict = set()
        self.missed_data = []
        self.ids = set()

    def extract_line(self, line):
        if self.mode == "offline":
            if self.level == "junior":
                return extract_junior_from_offline(line)
            elif self.level == "primary":
                return extract_primary_from_offline(line)
            else:
                raise ValueError(f"未知的level：{self.level}")
        elif self.mode == "online":
            if self.level == "junior":
                return extract_junior_from_close(line)
            elif self.level == "primary":
                return extract_primary_from_close(line)
            else:
                raise ValueError(f"未知的level：{self.level}")
        elif self.mode == "open":
            if self.level == "primary":
                return extract_primary_from_open(line)
            elif self.level == "junior":
                return extract_junior_from_open(line)
            else:
                raise ValueError(f"未知的level：{self.level}")
        else:
            raise ValueError(f"mode must be offline, but got {self.mode}")
 
    def extract_file(self, filepath: FilePath, save_file: FilePath) -> MetricType:
        valid_count = 0
        null_count = 0
        duplicate_count = 0
        json_decode_error_count = 0

        with open(filepath, "r", encoding="utf-8") as fi, \
                open(save_file, "w", encoding="utf-8") as fo:
            for line in fi:
                try:
                    line = json.loads(line)
                except json.JSONDecodeError as e:
                    logger.error(f"错误信息：{e}")
                    json_decode_error_count += 1
                    continue
                
                topic_id = line.get("topic_id") or line.get("topicId")
                if topic_id is None:
                    raise KeyError(f"topic_id字段不存在：{line.keys()}")
                    
                if self.enable_duplicate_check:
                    if topic_id in self.ids:
                        duplicate_count += 1
                        continue
                    self.ids.add(topic_id)

                line = self.extract_line(line)
                if line is None:
                    null_count += 1
                    self.state_null.add(topic_id)
                    continue
                
                valid_count += 1
                if isinstance(line, list):        
                    for item in line:
                        item = json.dumps(item, ensure_ascii=False) + "\n"
                        fo.write(item)
                else:
                    line = json.dumps(line, ensure_ascii=False) + "\n"
                    fo.write(line)
            
        total_count = valid_count + null_count + duplicate_count + json_decode_error_count
        self.total_count += total_count
        self.valid_count += valid_count
        self.null_count += null_count
        self.duplicate_count += duplicate_count
        self.json_decode_error_count += json_decode_error_count

        metrics = {
            "总样本数": total_count,
            "有效样本数": valid_count,
            "空样本数": null_count,
            "重复样本数": duplicate_count,
            "解析错误样本数": json_decode_error_count,
            "有效样本率": f"{valid_count / total_count * 100:.2f}%",
            "空样本率": f"{null_count / total_count * 100:.2f}%",
            "重复样本率": f"{duplicate_count / total_count * 100:.2f}%",
            "json解析错误样本率": f"{json_decode_error_count / total_count * 100:.2f}%"
        }

        return metrics

    def prefilter(self, line):
        def _prefilter(preset_question, tran_script):
            question = check_preset_options(preset_question)
            if question is None:
                return None

            question = check_preset_position(question, tran_script)
            if question is None:
                return None
            return question  

        try:
            if self.level == "junior":
                chunks = dict()
                items = line["items"]
                for bid, item in items.items():
                    for gid, question in item.items():
                        tran_script = question["tran_script"]
                        preset_question = question["preset_question"]
                        preset_question = _prefilter(preset_question, tran_script)
                        if preset_question is None:
                            continue

                        if bid not in chunks:
                            chunks[bid] = dict()
                        chunks[bid][gid] = {"preset_question": preset_question, "tran_script": tran_script}
                if len(chunks) == 0:
                    return None
                line["items"] = chunks
                return line
               
            elif self.level == "primary":
                preset_question = line["preset_question"]
                tran_script = line["tran_script"]
                preset_question = _prefilter(preset_question, tran_script)
                if preset_question is None:
                    return None
                line["preset_question"] = preset_question
                return line
        except Exception as e:
            logger.error(f"错误信息：{e}")
            return None

    def check_latex_format(self, line):
        def _check_latex_format(preset_question):
            questions = dict()
            for qid, question in preset_question.items():
                if not check_question_latex_format(question):
                    logger.debug(f"{qid}: LaTeX格式异常：{question}")
                    continue
                questions[qid] = question
            if len(questions) == 0:
                return None
            return questions

        if self.level == "junior":
            chunks = dict()
            items = line["items"]
            for bid, item in items.items():
                for gid, question in item.items():
                    preset_question = question["preset_question"]
                    preset_question = _check_latex_format(preset_question)
                    if preset_question is None:
                        continue

                    if bid not in chunks:
                        chunks[bid] = dict()
                    tran_script = question["tran_script"]
                    chunks[bid][gid] = {"preset_question": preset_question, "tran_script": tran_script}
            
            if len(chunks) == 0:
                return None

            line["items"] = chunks
            return line
               
        elif self.level == "primary":
            preset_question = line["preset_question"]
            tran_script = line["tran_script"]
            preset_question = _check_latex_format(preset_question)
            if preset_question is None:
                return None
            line["preset_question"] = preset_question
        return line

    def preprocess_file(self, filepath: FilePath, save_file: FilePath) -> MetricType:
        total_count = 0
        valid_count = 0
        null_count = 0
        error_count = 0
        latex_error_count = 0

        with open(filepath, "r", encoding="utf-8") as fi, \
                open(save_file, "w", encoding="utf-8") as fo:
            for raw in fi:
                line = json.loads(raw)
                topic_id = line["topic_id"]
                index = line.get("index")
                if index:
                    topic_id = f"{topic_id}#{index}"

                if self.enable_prefilter:
                    line = self.prefilter(line)
                    if line is None:
                        error_count += 1
                        self.state_null.add(topic_id)
                        continue

                if self.enable_latex_check:
                    line = self.check_latex_format(line)
                    if line is None:
                        latex_error_count += 1
                        self.state_null.add(topic_id)
                        continue
                        
                valid_count += 1
                line = json.dumps(line, ensure_ascii=False) + "\n"
                fo.write(line)
                
        null_count = error_count + latex_error_count
        total_count = valid_count + null_count

        self.total_count += total_count
        self.valid_count += valid_count
        self.null_count += null_count
        self.error_count += error_count
        self.latex_error_count += latex_error_count

        metrics = {
            "总样本数": total_count,
            "有效样本数": valid_count,
            "空样本数": null_count,
            "错误样本数": error_count,
            "LaTeX错误样本数": latex_error_count,
            "有效样本率": f"{valid_count / total_count * 100:.2f}%",
            "空样本率": f"{null_count / total_count * 100:.2f}%",
            "错误样本率": f"{error_count / total_count * 100:.2f}%",
            "LaTeX错误样本率": f"{latex_error_count / total_count * 100:.2f}%",
        }

        return metrics

    def read_prompt_template(self, filepath: FilePath) -> str:
        with open(filepath, "r", encoding="utf-8") as fp:
            self.prompt_template = fp.read().strip()
        logger.info(f"读取{self.level} prompt模板：\n{self.prompt_template}\n")

    def create_prompt_request(self, line: Dict[str, Union[Dict, str]]) -> List[Dict[str, str]]:
       
        def _create_primary_query(explain: str, questions: Dict[str, Any]) -> str:
            content = questions["content"]
            options = questions["options"]
            answer = questions["answer"]

            ids = "ABCD" if len(options) == 4 else "ABC"
            options = [f"{i}. {o}" for i, o in zip(ids, options)]
            choice_question = "\n".join([content] + options)

            prompt = self.prompt_template.replace("{{MATH_SCRIPT}}", explain)
            prompt = prompt.replace("{{CHOICE_QUESTION}}", choice_question)
            prompt = prompt.replace("{{ANSWER}}", answer)
            return prompt
        
        def _create_junior_query(question: str, explain: str, questions: Dict[str, Any]) -> str:
            # if question is None:
            #     question = ""
            content = questions["content"]
            options = questions["options"]
            answer = questions["answer"]
            ids = "ABCD" if len(options) == 4 else "ABC"
            options = [f"{i}. {o}" for i, o in zip(ids, options)]
            choice_question = "\n".join([content] + options)
            
            prompt = self.prompt_template.replace("{{MATH_QUESTION}}", question)
            prompt = prompt.replace("{{MATH_SCRIPT}}", explain)
            prompt = prompt.replace("{{CHOICE_QUESTION}}", choice_question)
            prompt = prompt.replace("{{ANSWER}}", answer)
            return prompt
        
        request_list = []
        tid = line["topic_id"]
        if self.level == "junior":
            question_content = line["content"]
            chunks = line["items"]
            for cid, chunk in chunks.items():
                for gid, groups in chunk.items():
                    tran_script = groups["tran_script"]
                    preset_question = groups["preset_question"]
                    for key, question in preset_question.items():
                        prompt = _create_junior_query(question_content, tran_script, question)
                        qid = f"{cid}#{gid}#{key}"
                        request = {"topic_id": tid, "qid": qid, "question": question, "query": prompt}
                        request_list.append(request)
        elif self.level == "primary":
            tran_script = line["tran_script"]
            questions = line["preset_question"]
            for qid, question in questions.items():
                prompt = _create_primary_query(tran_script, question)
                request = {"topic_id": tid, "qid": qid, "question": question, "query": prompt}
                request_list.append(request)

        return request_list

    def create_request_file(self, filepath: FilePath, save_file: FilePath) -> MetricType:
        total_count = 0
        request_count = 0
        with open(filepath, "r", encoding="utf-8") as fi, \
                open(save_file, "w", encoding="utf-8") as fo:
            for line in fi:
                line = json.loads(line)
                
                requests = self.create_prompt_request(line)
                request_count += len(requests)
                total_count += 1
                for request in requests:
                    request = json.dumps(request, ensure_ascii=False) + "\n"
                    fo.write(request)

        self.total_count += total_count
        self.request_count += request_count

        metrics = {
            "总样本数": total_count,
            "总请求数": request_count,
            "平均请求数": request_count / total_count
        }
        return metrics

    def add_prefix_to_filenames(self, root_dir, prefix, suffix=".jsonl", count=False):
        """
        递归遍历 root_dir 目录及其所有子目录，为每一个文件（不含目录）的文件名前加上指定前缀。

        参数:
            root_dir (str): 要处理的起始目录路径
            prefix (str): 要添加的前缀字符串
            suffix (str): 要添加的后缀字符串

        返回:
            None
        """
        line_count = 0
        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                old_path = os.path.join(dirpath, filename)
                filename = os.path.splitext(filename)[0]
                new_name = prefix + filename + suffix
                new_path = os.path.join(dirpath, new_name)
                os.rename(old_path, new_path)
                msg = f"重命名文件：{filename} -> {new_name}"
                if count:
                    file_count = get_file_line_count(new_path)
                    line_count += file_count
                    msg += f"，共{file_count}行"
                logger.info(msg)
        return line_count

    def check_response_answer(self, answer) -> bool:
        answer = answer.strip()
        if answer not in ["没有正确选项", "答案不唯一", "答案不正确", "题目合格"]:
            logger.debug(f"异常的答案：{[answer]}")
            answer = answer.strip().split("\n")[-1]
            answer = answer.split("。")[-1]
            logger.debug(f"修正的答案：{answer}")
            if "题目合格" in answer:
                return True
            else:
                return False

        if answer == "题目合格":
            return True
        return False

    def parse_response_file(self, response_file, question_file) -> MetricType:
        prompt_tokens = []
        completion_tokens = []
        question_dict = dict()
        request_count = 0
        valid_request_count = 0
        with open(response_file, "r", encoding="utf-8") as fp:
            for line in fp:
                try:
                    line = json.loads(line)
                    tid = line["topic_id"]
                    qid = line["qid"]
                    request_count += 1

                    if question_dict.get(tid) is None:
                        question_dict[tid] = dict()

                    answer = line.get("answer_mode4") or line.get("answer")
                    if answer is None:
                        logger.error(f"tid={tid}, qid={qid} 没有answer")
                        continue

                    valid_request_count += 1
                    flag = self.check_response_answer(answer)
                    if flag:
                        question = line["question"]
                        question_dict[tid][qid] = question

                    prompt_tokens.append(line.get("prompt_tokens", 0))
                    completion_tokens.append(line.get("completion_tokens", 0))
                except json.JSONDecodeError as e:
                    logger.error(e)

        metrics = {
            "总响应数": request_count,
            "有效响应数": valid_request_count,
            "有效响应率": valid_request_count / request_count * 100,
            "平均prompt_tokens长度": int(sum(prompt_tokens) / len(prompt_tokens)),
            "平均completion_tokens长度": int(sum(completion_tokens) / len(completion_tokens))
        }
        logger.info(f"解析响应文件：{metrics}")
        self.json_decode_error_count += (request_count - valid_request_count)

        valid_count = 0
        null_count = 0
        total_count = len(question_dict)
        question_map = dict()
        for tid, question in question_dict.items():
            if len(question) == 0:
                question = None
                null_count += 1
            else:
                valid_count += 1
            question_map[tid] = question
        logger.info(f"共更新{total_count}条预置问题，其中{null_count}条为空，{valid_count}条非空")

        metrics = {
            "总样本数": total_count,
            "非空样本数": valid_count,
            "空样本数": null_count,
            "非空样本率": valid_count / total_count * 100,
            "空样本率": null_count / total_count * 100,
        }
        self.total_count += total_count
        self.valid_count += valid_count
        self.null_count += null_count

        with open(question_file, "w", encoding="utf-8") as fp:
            json.dump(question_map, fp, ensure_ascii=False)

        return metrics

    def load_null_state_file(self, state_file: str):
        with open(state_file, "r", encoding="utf-8") as fp:
            self.state_null = json.load(fp)
        logger.info(f"加载空状态文件：{state_file}，共{len(self.state_null)}条空状态")

    def merge_input_and_result(self, input_file: str, save_file: str, result_file: str):
        with open(result_file, "r", encoding="utf-8") as fp:
            results = json.load(fp)
            logger.info(f"共{len(results)}条结果")
        
        question_update_count = 0
        question_null_count = 0
        question_same_count = 0
        with open(input_file, "r", encoding="utf-8") as fp, open(save_file, "w", encoding="utf-8") as f_save:
            for line in fp:
                line = json.loads(line)
                tid = line["topic_id"]
                new_questions = results.get(tid)
                if self.mode == "offline":
                    if self.level == "junior":
                        line = merge_to_junior_offline(line, new_questions)
                    elif self.level == "primary":
                        raise ValueError(f"离线模式下，等级为{self.level}时，不支持合并")
                    else:
                        raise ValueError(f"未知等级：{self.level}")
                elif self.mode == "online":
                    if self.level == "junior":
                        raise ValueError(f"在线模式下，等级为{self.level}时，不支持合并")
                    elif self.level == "primary":
                        line = merge_to_primary_online(line, new_questions)

                    else:
                        raise ValueError(f"未知等级：{self.level}")
                else:
                    raise ValueError(f"未知模式：{self.mode}")

                state = line["preset_question_operate_type"]
                if state == "null":
                    question_null_count += 1
                elif state == "update":
                    question_update_count += 1
                elif state == "same":
                    question_same_count += 1
                else:
                    raise ValueError(f"未知状态：{state}")
                
                line = json.dumps(line, ensure_ascii=False) + '\n'
                f_save.write(line)

        total_count = question_null_count + question_update_count + question_same_count

        self.update_count += question_update_count
        self.null_count += question_null_count
        self.same_count += question_same_count
        self.total_count += total_count
      
        metrics = {
            "总样本数": total_count,
            "预置问题为空数": question_null_count,
            "更新预置问题数": question_update_count,
            "未变化预置问题数": question_same_count,
            "预置问题为空率": f"{question_null_count / total_count * 100:.2f}%",
            "更新预置问题率": f"{question_update_count / total_count * 100:.2f}%",
            "未变化预置问题率": f"{question_same_count / total_count * 100:.2f}%"
        }
        return metrics

    def update_preset_question(self, input_file: str, save_file: str, result_file: str, reflash=False):
        with open(result_file, "r", encoding="utf-8") as fp:
            results = json.load(fp)
            logger.info(f"读取答案：共{len(results)}条结果")
        
        question_update_count = 0
        question_null_count = 0
        question_same_count = 0
        front_is_null_count = 0
        with open(input_file, "r", encoding="utf-8") as fp, open(save_file, "w", encoding="utf-8") as f_save:
            for raw in fp:
                line = json.loads(raw)
                tid = line.get("topic_id") or line.get("topicId")
                if not tid:
                    raise ValueError(f"未找到ID：{line.keys()}")
                    
                questions = results.get(tid)
                if self.mode == "offline":
                    if tid in self.state_null:
                        line = {
                            "topic_id": tid,
                            "preset_question_version": "filter_preset_question_1113",
                            "preset_question_operate_type": "same"
                        }
                    else:
                        if self.level == "junior":
                            line = update_junior_to_offline(line, questions)
                        elif self.level == "primary":
                            line = update_primary_to_offline(line, questions)
                        else:
                            raise ValueError(f"未知等级：{self.level}")
                        
                        if tid in self.script_state_dict:
                            line["preset_question_operate_type"] = "null"
                            line["preset_question"] = {"scienceStruct": None, "ttsUrl": None}
                            front_is_null_count += 1
                elif self.mode == "online":
                    if tid in self.state_null:
                        if reflash:
                            line = {
                                "topic_id": tid,
                                "preset_question_version": "filter_preset_question_1113",
                                "preset_question_operate_type": "update",
                                "preset_question": {"scienceStruct": None, "ttsUrl": None}
                            }
                        else:
                            line["preset_question_operate_type"] = "same"
                    else: 
                        if self.level == "junior":
                            line = update_junior_to_close(line, questions)
                        elif self.level == "primary":
                            if reflash:
                                line = update_primary_to_online_reflash(line, questions)
                            else:
                                line = update_primary_to_close(line, questions)
                        else:
                            raise ValueError(f"未知等级：{self.level}")
                else:
                    raise ValueError(f"未知模式：{self.mode}")
                
                state = line["preset_question_operate_type"]
                if state == "null":
                    question_null_count += 1
                elif state == "update":
                    question_update_count += 1
                elif state == "same":
                    question_same_count += 1
                else:
                    raise ValueError(f"未知状态：{state}")

                if self.mode == "online" and not reflash:
                    del line["preset_question_operate_type"]

                line = json.dumps(line, ensure_ascii=False) + '\n'
                f_save.write(line)
    
        total_count = question_null_count + question_update_count + question_same_count
        self.update_count += question_update_count
        self.null_count += question_null_count
        self.same_count += question_same_count
        self.total_count += total_count
        
        metrics = {
            "总样本数": total_count,
            "前置为空数": front_is_null_count,
            "预置问题为空数": question_null_count,
            "更新预置问题数": question_update_count,
            "未变化预置问题数": question_same_count,
            "预置问题为空率": f"{question_null_count / total_count * 100:.2f}%",  
            "更新预置问题率": f"{question_update_count / total_count * 100:.2f}%",
            "未变化预置问题率": f"{question_same_count / total_count * 100:.2f}%"
        }
        return metrics

    def pipeline(self, filepath: FilePath, save_file: FilePath, result_file: FilePath=None):
        if self.step == "extract":
            metrics = self.extract_file(filepath, save_file)
        elif self.step == "preprocess":
            metrics = self.preprocess_file(filepath, save_file)
        elif self.step == "request":
            metrics = self.create_request_file(filepath, save_file)
        elif self.step == "response":
            metrics = self.parse_response_file(filepath, question_file=save_file)
        elif self.step == "merge":
            # metrics = self.merge_input_and_result(filepath, save_file, result_file)
            metrics = self.merge_preset_question(filepath, save_file)
        elif self.step == "update":
            # metrics = self.update_preset_question(filepath, save_file, result_file, reflash=True)
            metrics = self.update_preset_question(filepath, save_file, result_file, reflash=False)
        else:
            raise ValueError(f"未知步骤：{self.step}")

        return metrics

    def walk_directory(self, input_dir, output_dir, result_dir=None):
        args = []
        for root, _, files in os.walk(input_dir):
            for file in sorted(files):
                if file.startswith("_"):
                    logger.info(f"跳过文件：{file}")
                    continue
                filepath = os.path.join(root, file)
                relative_path = os.path.relpath(root, input_dir)
                relative_path = relative_path.replace(".", "")
                savedir = os.path.join(output_dir, relative_path)
                if not os.path.exists(savedir):
                    os.makedirs(savedir)
                    logger.info(f"创建目录：{savedir}")
                save_file = os.path.join(savedir, file)
                if result_dir is not None:
                    if not file.endswith(".json"):
                        file += ".json"
                    result_file = os.path.join(result_dir, relative_path, file)
                    if not os.path.exists(result_file):
                        result_file = os.path.join(result_dir, file)
                    
                    args.append((filepath, result_file, save_file))
                else:
                    args.append((filepath, save_file))
        return args
    
    def process_directory(self, input_dir, output_dir, result_dir=None):
        args = self.walk_directory(input_dir, output_dir, result_dir)
        for arg in args:
            if result_dir is not None:
                filepath, result_file, save_file = arg
            else:
                filepath, save_file = arg
                result_file = None

            relative_path = os.path.relpath(filepath, input_dir)
            logger.info(f"提交任务：{relative_path}")
            metrics = self.pipeline(filepath, save_file, result_file)
            for key, value in metrics.items():
                logger.info(f"{key}：{value}")
        logger.info(f"完成目录：{input_dir}")

    def process_directory_with_threads(self, input_dir, output_dir, max_workers=4):
        futures = {}
        args = self.walk_directory(input_dir, output_dir)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for filepath, save_file in args:
                relative_path = os.path.relpath(filepath, input_dir)
                logger.info(f"提交任务：{relative_path}")
                future = executor.submit(self.pipeline, filepath, save_file)
                futures[future] = relative_path
                time.sleep(1)

            logger.info(f"提交任务数：{len(futures)}")
            completed_count = 0
            for future in as_completed(futures):
                fname = futures[future]
                try:
                    metrics = future.result()
                    logger.info(f"完成任务 {fname}")
                    logger.info(metrics)
                    completed_count += 1
                except Exception as e:
                    logger.error(f"处理文件 {fname} 时出错: {str(e)}")

            logger.info(f"完成任务数：{completed_count}/{len(futures)}")

    def dump_null_state(self, null_state_file: Optional[FilePath] = None, default_state: str = "null", state_dict: Optional[Set[str]] = None):
        if state_dict is None:
            state_dict = self.state_null

        logger.info(f"状态为空样本数：{len(state_dict)}")
        if len(state_dict) > 0 and null_state_file:
            with open(null_state_file, "w", encoding="utf-8") as fp:
                state_dict = {tid: default_state for tid in state_dict}
                json.dump(state_dict, fp, ensure_ascii=False)
            logger.info(f"空状态文件已保存至 {null_state_file}")

    def get_script_null_state(self, script_dir, state_key: str = "tran_script_operate_type"):
        logger.info(f"获取脚本空状态样本数：{script_dir}")
        script_state_dict = set()
        if os.path.isfile(script_dir):
            if script_dir.endswith(".txt"):
                with open(script_dir, "r", encoding="utf-8") as f:  
                    for line in f:
                        line = line.strip()
                        script_state_dict.add(line)
            else:
                with open(script_dir, "r", encoding="utf-8") as fp:
                    for line in fp:
                        line = json.loads(line)
                        script_operate_type = line[state_key]
                        if script_operate_type == "null":
                            script_state_dict.add(line["topic_id"])   
        else:
            for root, _, files in os.walk(script_dir):
                for file in files:
                    logger.info(f"处理文件：{file}")
                    script_file = os.path.join(root, file)
                    with open(script_file, "r", encoding="utf-8") as fp:
                        for line in fp:
                            line = json.loads(line)
                            script_operate_type = line[state_key]
                            if script_operate_type == "null":
                                script_state_dict.add(line["topic_id"])
                    logger.info(f"{file}获取空状态样本数：{len(script_state_dict)}")
        
        script_null_count = len(script_state_dict)
        self.script_state_dict = script_state_dict
        logger.info(f"脚本空状态样本数：{script_null_count}")              
     
    def load_new_result(self, result_dir: FilePath):
        self.new_states = dict()
        def load_file(filepath):
            dup_count = 0
            with open(filepath, "r", encoding="utf-8") as f:
                for raw in f:
                    line = json.loads(raw)
                    tid = line["topic_id"]
                    if tid in self.new_states:
                        dup_count += 1
                        if dup_count % 5000 == 0:
                            logger.info(f"重复ID数：{tid}")
                        continue
                    self.new_states[tid] = raw
            logger.info(f"加载文件 {filepath} 重复ID数：{dup_count}")
        
        logger.info(f"加载新结果：{result_dir}")
        if os.path.isfile(result_dir):
            load_file(result_dir)
        else:
            for root, _, files in os.walk(result_dir):
                for file in files:
                    logger.info(f"处理文件：{file}")
                    result_file = os.path.join(root, file)
                    load_file(result_file)
        logger.info(f"新结果样本数：{len(self.new_states)}")
                  
    def merge_preset_question(self, input_file: str, save_file: str):
        question_update_count = 0
        question_same_count = 0
        with open(input_file, "r", encoding="utf-8") as fp, open(save_file, "w", encoding="utf-8") as f_save:
            for raw in fp:
                line = json.loads(raw)
                tid = line.get("topic_id") or line.get("topicId")
                if not tid:
                    raise ValueError(f"未找到ID：{line.keys()}")

                state = self.new_states.get(tid)
                if state:
                    f_save.write(state)
                    question_update_count += 1
                else:
                    f_save.write(raw)
                    question_same_count += 1

        total_count = question_update_count + question_same_count
        self.update_count += question_update_count
        self.same_count += question_same_count
        self.total_count += total_count
        
        metrics = {
            "总样本数": total_count,
            "更新预置问题数": question_update_count,
            "未变化预置问题数": question_same_count,
            "更新预置问题率": f"{question_update_count / total_count * 100:.2f}%",
            "未变化预置问题率": f"{question_same_count / total_count * 100:.2f}%"
        }
        return metrics 
    
    def compute_metrics(self, save_file: Optional[FilePath] = None):
        if self.step == "extract":
            metrics = {
                "总样本数": self.total_count,
                "有效样本数": self.valid_count,
                "空样本数": self.null_count,
                "重复样本数": self.duplicate_count,
                "解析错误样本数": self.json_decode_error_count,
                "有效样本率": f"{self.valid_count / self.total_count * 100:.2f}%",
                "空样本率": f"{self.null_count / self.total_count * 100:.2f}%",
                "重复样本率": f"{self.duplicate_count / self.total_count * 100:.2f}%",
                "json解析错误样本率": f"{self.json_decode_error_count / self.total_count * 100:.2f}%"
            }
        elif self.step == "preprocess":
            metrics = {
                "总样本数": self.total_count,
                "有效样本数": self.valid_count,
                "空样本数": self.null_count,
                "错误样本数": self.error_count,
                "LaTeX错误样本数": self.latex_error_count,
                "有效样本率": f"{self.valid_count / self.total_count * 100:.2f}%",
                "空样本率": f"{self.null_count / self.total_count * 100:.2f}%",
                "错误样本率": f"{self.error_count / self.total_count * 100:.2f}%",
                "LaTeX错误样本率": f"{self.latex_error_count / self.total_count * 100:.2f}%",
            }
        elif self.step == "request":
            metrics = {
                "总样本数": self.total_count,
                "总请求数": self.request_count,
                "平均请求数": self.request_count / self.total_count
            }
        elif self.step == "response":
            metrics = {
                "总样本数": self.total_count,
                "有效样本数": self.valid_count,
                "空样本数": self.null_count,
                "有效样本率": f"{self.valid_count / self.total_count * 100:.2f}%",
                "空样本率": f"{self.null_count / self.total_count * 100:.2f}%",
                "JSONDecodeError响应数": self.json_decode_error_count
            }
        elif self.step == "merge":
            metrics = {
                "总样本数": self.total_count,
                "更新预置问题数": self.update_count,
                "未变化预置问题数": self.same_count,
                "更新预置问题率": f"{self.update_count / self.total_count * 100:.2f}%",
                "未变化预置问题率": f"{self.same_count / self.total_count * 100:.2f}%"
            }
        elif self.step == "update":
            metrics = {
                "总样本数": self.total_count,
                "更新预置问题数": self.update_count,
                "未变化预置问题数": self.same_count,
                "预置问题为空率": f"{self.null_count / self.total_count * 100:.2f}%",
                "更新预置问题率": f"{self.update_count / self.total_count * 100:.2f}%",
                "未变化预置问题率": f"{self.same_count / self.total_count * 100:.2f}%"
            }
        else:
            raise ValueError(f"未知步骤：{self.step}")

        for key, value in metrics.items():
            logger.info(f"{key}：{value}")

        if save_file:
            with open(save_file, "w", encoding="utf-8") as fp:
                json.dump(metrics, fp, ensure_ascii=False, indent=4)
        
   
def args_parse():
    parser = argparse.ArgumentParser(description="离线数据处理客户端")
    parser.add_argument("--mode", type=str, required=True, help="处理模式")
    parser.add_argument("--step", type=str, required=True, help="处理步骤")
    parser.add_argument("--input_dir", type=str, required=True, help="输入目录路径")
    parser.add_argument("--save_dir", type=str, required=True, help="输出目录路径")
    parser.add_argument("--result_dir", type=str, help="结果目录路径")
    parser.add_argument("--max_workers", type=int, default=1, help="最大线程数")
    parser.add_argument("--enable_duplicate_check", type=bool, default=False, help="是否启用重复检查")
    parser.add_argument("--enable_prefilter", type=bool, default=False, help="是否启用预置问题过滤")
    parser.add_argument("--enable_latex_check", type=bool, default=False, help="是否启用LaTeX格式检查")
    parser.add_argument("--prompt_template_file", type=str, default=None, help="提示模板文件路径")
    parser.add_argument("--level", type=str, default="sj", help="处理级别")
    parser.add_argument("--rename_prefix", type=str, default=None, help="重命名前缀")
    parser.add_argument("--question_file", type=str, default=None, help="预置问题文件路径")
    parser.add_argument("--state_file", type=str, default=None, help="状态文件路径")
    parser.add_argument("--metrics_file", type=str, default=None, help="指标文件路径")

    args = parser.parse_args()
    return args


def client():
    args = args_parse()
    if args.mode not in ["offline", "online"]:
        raise ValueError(f"mode must be one of ['offline', 'online'], but got {args.mode}")

    if args.step not in ["extract", "preprocess", "request", "response", "merge", "update"]:
        raise ValueError(
            f"step must be one of ['extract', 'preprocess', 'request', 'response', 'merge', 'update'], but got {args.step}")

    logger.info(json.dumps(args.__dict__, ensure_ascii=False, indent=4))

    manager = PresetQuestionManager(
        step=args.step,
        enable_duplicate_check=args.enable_duplicate_check,
        enable_prefilter=args.enable_prefilter,
        enable_latex_check=args.enable_latex_check,
        mode=args.mode,
        level=args.level
    )

    if args.step == "extract":
        if args.max_workers > 1:
            manager.process_directory_with_threads(args.input_dir, args.save_dir, max_workers=args.max_workers)
        else:
            manager.process_directory(args.input_dir, args.save_dir)
        manager.dump_null_state(args.state_file, "same")
    elif args.step == "preprocess":
        if args.max_workers > 1:
            manager.process_directory_with_threads(args.input_dir, args.save_dir, max_workers=args.max_workers)
        else:
            manager.process_directory(args.input_dir, args.save_dir)
        manager.dump_null_state(args.state_file, "null")
    elif args.step == "request":
        manager.read_prompt_template(args.prompt_template_file)
        manager.process_directory(args.input_dir, args.save_dir)
        if args.rename_prefix:
            line_count = manager.add_prefix_to_filenames(args.save_dir, args.rename_prefix)
            logger.info(f"重命名完成，共处理{line_count}行数据")
    elif args.step == "response":
        # delete_zip=False
        # delete_failed=True
        # target_directory = os.path.dirname(args.input_dir)
        # flag = batch_unzip(target_directory, delete_zip, delete_failed, extract_dir=f"{target_directory}/jsonl", prefix_pattern=r"资源教育部.+?1114攻关_")
        # if not flag:
        #     logger.error("解压失败，退出程序")
        #     return

        # if not delete_zip:
        #     move_files(target_directory, f"{target_directory}/zip", file_type=".zip")
        manager.process_directory(args.input_dir, args.save_dir)
    elif args.step == "update":
        if args.state_file:
            manager.load_null_state_file(args.state_file)
        
        if args.question_file:
            manager.get_script_null_state(args.question_file)

        # if os.path.isfile(args.input_dir):
        #     os.makedirs(os.path.dirname(args.save_dir), exist_ok=True)
        #     manager.update_preset_question(args.input_dir, args.save_dir, args.result_dir)
        # else:
        manager.process_directory(args.input_dir, args.save_dir, args.result_dir)
    elif args.step == "merge":
        manager.load_new_result(args.result_dir)
        manager.process_directory(args.input_dir, args.save_dir)
    manager.compute_metrics(args.metrics_file)
    logger.info("完成！")


if __name__ == "__main__":
    client()
    # client("online")

