import json
import requests
import curses
import copy
import time

USERNAME = "郭冬杰"
PASSWORD = "wy7TMap3"
TASKS = [
    # "资源教育-语言学习_0715_HWL_TEXT_互动视频_爬取输入_PV0714_part0",
    # "资源教育-语言学习_0715_HWL_TEXT_互动视频_爬取输入_PV0714_part1",
    # "资源教育-语言学习_0715_HWL_TEXT_互动视频_爬取输入_PV0714_part2",
    # "资源教育-语言学习_0715_HWL_TEXT_互动视频_爬取输入_PV0714_part3",
    # "资源教育-语言学习_0715_HWL_TEXT_互动视频_爬取输入_PV0714_part4",
    # "资源教育-语言学习_0715_HWL_TEXT_互动视频_爬取输入_PV0714_part5",
    # "资源教育-语言学习_0715_HWL_TEXT_互动视频_爬取输入_PV0714_part6",
    # "资源教育-语言学习_0715_HWL_TEXT_互动视频_爬取输入_PV0714_part7",
    # "资源教育-语言学习_0715_HWL_TEXT_互动视频_爬取输入_PV0714_part8",
    # "资源教育-语言学习_0715_HWL_TEXT_互动视频_爬取输入_PV0714_part9",
    # "资源教育-语言学习_4401_doubao-seed-1-6-250615_郭冬杰_1762158679525_互动视频_试题屏数据_互动视频爬取输入_英语单模_1028_Prompt_P0930_Source_dbseed_1"
    # "资源教育-语言学习_4605_doubao-seed-1-6-250615_郭冬杰_1762704295012_互动视频_试题屏数据_互动视频爬取输入_英语单模_1020_Prompt_P0930_Source_dbseed_1"
    # "资源教育-语言学习_4881_doubao-seed-1-6-250615_郭冬杰_1763376351960_互动视频_试题屏数据_互动视频爬取输入_英语单模_0926_Prompt_P0930_Source_dbseed_1"
    # "资源教育-理科认知_5052_doubao-seed-1-6-250615_郭冬杰_1764146970637_初数单模_清洗输入_lite",

    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00000_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00001_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00002_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00003_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00004_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00005_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00006_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00007_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00008_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00009_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00010_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00011_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00012_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00013_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00014_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00015_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00016_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00017_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00018_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00019_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00020_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00021_video_check_crawl_in_new",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00022_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00023_video_check_crawl_in_new",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00024_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00025_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00026_video_check_crawl_in_new",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00027_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00028_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00029_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00030_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00031_video_check_crawl_in_new",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00032_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00033_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00034_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00035_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00036_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00037_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00038_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00039_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00040_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00041_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00042_video_check_crawl_in_new",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00043_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00044_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00045_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00046_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00047_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00048_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00049_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00050_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00051_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00052_video_check_crawl_in",
    # "资源教育部-辅学offline_251231_doubao-seed-1.6-0615_1114攻关_cz_sm_part00053_video_check_crawl_in",
    "资源教育部-辅学offline_640_doubao-seed-1-6-250615_郭冬杰_1767834105727_小学_单模_part1_video_check_crawl_in"
]
SLEEP = 10 * 60

# %%

BASE_HOST = "124.70.203.196:3200"
BASE_HOST_URL = "http://" + BASE_HOST
BASE_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Connection": "keep-alive",
    "Content-Type": "application/json;charset=UTF-8",
    "Host": BASE_HOST,
    "Origin": BASE_HOST_URL,
    "Referer": BASE_HOST_URL + "/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
}


def login(_username, _password):
    headers = copy.deepcopy(BASE_HEADERS)
    body = {"username": _username, "password": _password}
    resp = requests.post(BASE_HOST_URL + "/login", headers=headers, json=body)
    resp = dict(resp.json())
    if "code" in resp and resp["code"] == 200:
        return resp["data"]["token"]
    else:
        raise RuntimeError("Login failed!")


def get_data_departments(_token):
    headers = copy.deepcopy(BASE_HEADERS)
    headers["Authorization"] = "Bearer " + _token
    resp = requests.get(BASE_HOST_URL + "/data_departments?mode=all", headers=headers)
    resp = dict(resp.json())
    if "code" in resp and resp["code"] == 1:
        return resp["data"][0]["name"]
    raise RuntimeError("get_data_departments failed!")


def update_task(_token, _task_name):
    headers = copy.deepcopy(BASE_HEADERS)
    headers["Authorization"] = "Bearer " + _token
    body = {
        "type_name": _task_name,
    }
    resp = requests.post(BASE_HOST_URL + "/operate_task_update_progress", headers=headers, json=body)
    resp = dict(resp.json())
    if "code" in resp and resp["code"] == 0:
        return True, resp["msg"]
    elif "code" in resp and resp["code"] == -1:
        return False, resp["msg"]
    else:
        raise RuntimeError("operate_task_update_progress failed!")


def reset_task(_token, _task_name):
    headers = copy.deepcopy(BASE_HEADERS)
    headers["Authorization"] = "Bearer " + _token
    body = {
        "type_name": _task_name,
    }
    resp = requests.post(BASE_HOST_URL + "/operate_task_reset", headers=headers, json=body)
    resp = dict(resp.json())
    if "code" in resp and resp["code"] == 0:
        return True, resp["msg"]
    elif "code" in resp and resp["code"] == -1:
        return False, resp["msg"]
    else:
        raise RuntimeError("operate_task_reset failed!")


_token = login(USERNAME, PASSWORD)
_department = get_data_departments(_token)
tasks = {task: {"cnt": 0, "total": 0} for task in TASKS}
while True:
    for task, info in tasks.items():
        if info["total"] > 0 and info["cnt"] == info["total"]:
            continue
        try:
            _success, _resp = update_task(_token, task)
            if not _success:
                continue
            info["cnt"] = _resp["count_sucess"]
            info["total"] = _resp["count_all"]
            if info["cnt"] == info["total"]:
                continue
            _success, _resp = reset_task(_token, task)
        except Exception as e:
            print("订阅失败.")
            continue
        # print()
    for task, info in tasks.items():
        print(f"【{info['cnt']}/{info['total']}】{task}")
    print("=" * 100)
    time.sleep(SLEEP)
