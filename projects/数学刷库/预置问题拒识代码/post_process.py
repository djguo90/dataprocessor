import os
import sys
from functools import reduce
import tqdm
import json
from pathlib import Path
common_utils_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../..")
sys.path.append(common_utils_path)

# 引入你的工具库
from common_utils import read_jsonl, get_values_by_key_path, checkpoint_to_file, run_pipeline

from common_utils import read_jsonl, read_json

def get_result(orig_data_path, orig_null_path, latex_null_path, video_check_path, preset_question_result_path, save_result_path):
    samples_orig = read_jsonl(orig_data_path)
    samples_orig_null = list(read_json(orig_null_path))
    samples_orig_null = reduce(lambda x, y: x | y, samples_orig_null)
    samples_orig_null = set(samples_orig_null.keys())
    print(len(samples_orig_null))
    samples_latex_null = list(read_json(latex_null_path))
    samples_latex_null = reduce(lambda x, y: x | y, samples_latex_null)
    samples_latex_null = set(samples_latex_null.keys())
    print(len(samples_latex_null))
    samples_video_check_null = read_jsonl(video_check_path)
    samples_video_check_null = set([x["topic_id"] for x in samples_video_check_null if x["tran_script_operate_type"]=="null"])
    print(len(samples_video_check_null))

    samples_preset_question_result = list(read_json(preset_question_result_path))
    samples_preset_question_result = reduce(lambda x, y: x | y, samples_preset_question_result)
    id2question_keep = {}
    for sample_id in samples_preset_question_result:
        if samples_preset_question_result[sample_id] is None:
            id2question_keep[sample_id] = []
        else:
            id2question_keep[sample_id] = [samples_preset_question_result[sample_id][_]["content"] for _ in samples_preset_question_result[sample_id]]
    print(len(id2question_keep))
    Path(save_result_path).parent.mkdir(exist_ok=True, parents=True)
    with open(save_result_path, "w") as writer:
        for sample in tqdm.tqdm(samples_orig):
            sample_id = sample["topic_id"]
            if sample_id in samples_orig_null:
                result = {
                    "topic_id": sample_id,
                    "preset_question_operate_type": "same",
                    "preset_question_version": "preset_question_orig_null"
                }
            elif sample_id in samples_latex_null:
                result = {
                    "topic_id": sample_id,
                    "preset_question_operate_type": "null",
                    "preset_question_version": "preset_question_latex_check",
                    "preset_question": {"scienceStruct": None, "ttsUrl": None}      
                }
            elif sample_id in samples_video_check_null:
                result = {
                    "topic_id": sample_id,
                    "preset_question_operate_type": "null",
                    "preset_question_version": "preset_question_video_check",
                    "preset_question": {"scienceStruct": None, "ttsUrl": None}      
                }
            else:
                assert sample_id in id2question_keep
                if not id2question_keep[sample_id]:
                    result = {
                        "topic_id": sample_id,
                        "preset_question_operate_type": "null",
                        "preset_question_version": "preset_question_quality_check",
                        "preset_question": {"scienceStruct": None, "ttsUrl": None}      
                    }
                else:
                    questions = json.loads(sample["preset_question"][0]["presetQuestion"])["scienceStruct"]

                    if len(id2question_keep[sample_id]) == len(questions):
                        result = {
                            "topic_id": sample_id,
                            "preset_question_operate_type": "same",
                            "preset_question_version": "preset_question_quality_check"
                        }
                    else:
                        questions_to_keep = {x:questions[x] for x in questions if questions[x]["content"] in id2question_keep[sample_id]}
                        result = {
                            "topic_id": sample_id,
                            "preset_question_operate_type": "update",
                            "preset_question_version": "preset_question_quality_check",
                            "preset_question": {"scienceStruct": questions_to_keep, "ttsUrl": None}      
                        }
            writer.write(json.dumps(result, ensure_ascii=False)+"\n")


if __name__ == "__main__":
    # get_result(
    #     orig_data_path="/mnt/pan8T/temp_jiahe3/datas_jun_offline/raw/3kw/datas/junior_sm_1.json",
    #     orig_null_path="/mnt/pan8T/temp_xsji4/DataManagement/data/offline/SingleJunior/_extract_state_is_null.json", 
    #     latex_null_path=[
    #         "/mnt/pan8T/temp_xsji4/DataManagement/data/offline/SingleJunior/_preprocess_batchs_state_is_null.json", 
    #         "/mnt/pan8T/temp_xsji4/DataManagement/data/offline/SingleJunior/_preprocess_batchs_failed_state_is_null.json"
    #     ], 
    #     video_check_path="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次/初中单模视频综合过滤结果-v2/part1_video_check_result.json",
    #     preset_question_result_path="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次/初中单模视频预置问题爬取处理/junior_sm_1.json", 
    #     save_result_path="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次/初中单模视频预置问题综合过滤结果/junior_sm_1.json"
    # )

    get_result(
        orig_data_path="/mnt/pan8T/temp_jiahe3/datas_jun_offline/raw/3kw/datas/junior_sm_2.json",
        orig_null_path="/mnt/pan8T/temp_xsji4/DataManagement/data/offline/SingleJunior/_extract_state_is_null.json", 
        latex_null_path=[
            "/mnt/pan8T/temp_xsji4/DataManagement/data/offline/SingleJunior/_preprocess_batchs_state_is_null.json", 
            "/mnt/pan8T/temp_xsji4/DataManagement/data/offline/SingleJunior/_preprocess_batchs_failed_state_is_null.json"
        ], 
        video_check_path="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次/初中单模视频综合过滤结果-v2/part2_video_check_result.json",
        preset_question_result_path="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次/初中单模视频预置问题爬取处理/junior_sm_2.json", 
        save_result_path="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次/初中单模视频预置问题综合过滤结果/junior_sm_2.json"
    )

    get_result(
        orig_data_path="/mnt/pan8T/temp_jiahe3/datas_jun_offline/raw/3kw/datas/junior_sm_3.json",
        orig_null_path="/mnt/pan8T/temp_xsji4/DataManagement/data/offline/SingleJunior/_extract_state_is_null.json", 
        latex_null_path=[
            "/mnt/pan8T/temp_xsji4/DataManagement/data/offline/SingleJunior/_preprocess_batchs_state_is_null.json", 
            "/mnt/pan8T/temp_xsji4/DataManagement/data/offline/SingleJunior/_preprocess_batchs_failed_state_is_null.json"
        ], 
        video_check_path="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次/初中单模视频综合过滤结果-v2/part3_video_check_result.json",
        preset_question_result_path="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次/初中单模视频预置问题爬取处理/junior_sm_3.json", 
        save_result_path="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次/初中单模视频预置问题综合过滤结果/junior_sm_3.json"
    )
    
    get_result(
        orig_data_path="/mnt/pan8T/temp_jiahe3/datas_jun_offline/raw/3kw/datas/junior_sm_4.json",
        orig_null_path="/mnt/pan8T/temp_xsji4/DataManagement/data/offline/SingleJunior/_extract_state_is_null.json", 
        latex_null_path=[
            "/mnt/pan8T/temp_xsji4/DataManagement/data/offline/SingleJunior/_preprocess_batchs_state_is_null.json", 
            "/mnt/pan8T/temp_xsji4/DataManagement/data/offline/SingleJunior/_preprocess_batchs_failed_state_is_null.json"
        ], 
        video_check_path="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次/初中单模视频综合过滤结果-v2/part4_video_check_result.json",
        preset_question_result_path="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次/初中单模视频预置问题爬取处理/junior_sm_4.json", 
        save_result_path="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次/初中单模视频预置问题综合过滤结果/junior_sm_4.json"
    )

    get_result(
        orig_data_path="/mnt/pan8T/temp_jiahe3/datas_jun_offline/raw/3kw/datas/junior_sm_5.json",
        orig_null_path="/mnt/pan8T/temp_xsji4/DataManagement/data/offline/SingleJunior/_extract_state_is_null.json", 
        latex_null_path=[
            "/mnt/pan8T/temp_xsji4/DataManagement/data/offline/SingleJunior/_preprocess_batchs_state_is_null.json", 
            "/mnt/pan8T/temp_xsji4/DataManagement/data/offline/SingleJunior/_preprocess_batchs_failed_state_is_null.json"
        ], 
        video_check_path="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次/初中单模视频综合过滤结果-v2/part5_video_check_result.json",
        preset_question_result_path="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次/初中单模视频预置问题爬取处理/junior_sm_5.json", 
        save_result_path="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次/初中单模视频预置问题综合过滤结果/junior_sm_5.json"
    )

    get_result(
        orig_data_path="/mnt/pan8T/temp_jiahe3/datas_jun_offline/raw/3kw/datas/junior_sm_6.json",
        orig_null_path="/mnt/pan8T/temp_xsji4/DataManagement/data/offline/SingleJunior/_extract_state_is_null.json", 
        latex_null_path=[
            "/mnt/pan8T/temp_xsji4/DataManagement/data/offline/SingleJunior/_preprocess_batchs_state_is_null.json", 
            "/mnt/pan8T/temp_xsji4/DataManagement/data/offline/SingleJunior/_preprocess_batchs_failed_state_is_null.json"
        ], 
        video_check_path="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次/初中单模视频综合过滤结果-v2/part6_video_check_result.json",
        preset_question_result_path="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次/初中单模视频预置问题爬取处理/junior_sm_6.json", 
        save_result_path="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次/初中单模视频预置问题综合过滤结果/junior_sm_6.json"
    )

    get_result(
        orig_data_path="/mnt/pan8T/temp_jiahe3/datas_jun_offline/raw/3kw/datas/junior_sm_7.json",
        orig_null_path="/mnt/pan8T/temp_xsji4/DataManagement/data/offline/SingleJunior/_extract_state_is_null.json", 
        latex_null_path=[
            "/mnt/pan8T/temp_xsji4/DataManagement/data/offline/SingleJunior/_preprocess_batchs_state_is_null.json", 
            "/mnt/pan8T/temp_xsji4/DataManagement/data/offline/SingleJunior/_preprocess_batchs_failed_state_is_null.json"
        ], 
        video_check_path="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次/初中单模视频综合过滤结果-v2/part7_video_check_result.json",
        preset_question_result_path="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次/初中单模视频预置问题爬取处理/junior_sm_7.json", 
        save_result_path="/mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次/初中单模视频预置问题综合过滤结果/junior_sm_7.json"
    )
    

