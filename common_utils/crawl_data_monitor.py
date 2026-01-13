import json
import requests
import curses
import copy
import time

USERNAME = "郭冬杰"
PASSWORD = "wy7TMap3"
TASKS = [
    "资源教育部-辅学-图形化讲解_174_gemini-3-pro-preview-thinking_郭冬杰_1768274045415-小数单模-立体几何_训练集_phase1爬取输入_part001_pv3",
    "资源教育部-辅学-图形化讲解_175_gemini-3-pro-preview-thinking_郭冬杰_1768274046136-小数单模-立体几何_训练集_phase1爬取输入_part002_pv3",
    "资源教育部-辅学-图形化讲解_176_gemini-3-pro-preview-thinking_郭冬杰_1768274046857-小数单模-立体几何_训练集_phase1爬取输入_part003_pv3",
    "资源教育部-辅学-图形化讲解_177_gemini-3-pro-preview-thinking_郭冬杰_1768274047491-小数单模-立体几何_训练集_phase1爬取输入_part004_pv3",
    "资源教育部-辅学-图形化讲解_178_gemini-3-pro-preview-thinking_郭冬杰_1768274049168-小数单模-立体几何_训练集_phase1爬取输入_part005_pv3",
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
