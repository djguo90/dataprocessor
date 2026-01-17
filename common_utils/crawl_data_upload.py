# -*- coding=utf-8 -*-
"""
    @Author: JQY
    @Date  : 2025/11/20 20:02
    @Desc  :
"""
import os
import time
import copy
import requests
import json

# ==========================================
#               配置区域 (请修改此处)
# ==========================================
CONFIG = {}
BASE_HOST = "124.70.203.196:3200"


# ==========================================
#               原始 API 封装
# ==========================================

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
BASE_FILE_BOUNDARY = "----WebKitFormBoundaryAsLongAsYouLoveMe"


def login(_username, _password):
    headers = copy.deepcopy(BASE_HEADERS)
    body = {"username": _username, "password": _password}
    resp = requests.post(BASE_HOST_URL + "/login", headers=headers, json=body)
    resp = dict(resp.json())
    if "code" in resp and resp["code"] == 200:
        return resp["data"]["token"]
    else:
        raise RuntimeError(f"Login failed: {resp.get('msg', 'Unknown error')}")


def get_data_sources(_token):
    headers = copy.deepcopy(BASE_HEADERS)
    headers["Authorization"] = "Bearer " + _token
    resp = requests.get(BASE_HOST_URL + "/data_sources?mode=all", headers=headers)
    resp = dict(resp.json())
    if "code" in resp and resp["code"] == 1:
        return resp["data"]
    raise RuntimeError("get_data_sources failed!")


def get_data_departments(_token):
    headers = copy.deepcopy(BASE_HEADERS)
    headers["Authorization"] = "Bearer " + _token
    resp = requests.get(BASE_HOST_URL + "/data_departments?mode=all", headers=headers)
    resp = dict(resp.json())
    if "code" in resp and resp["code"] == 1:
        # 假设返回列表不为空，取第一个部门
        if resp["data"]:
            return resp["data"][0]["name"]
        else:
            raise RuntimeError("No departments found!")
    raise RuntimeError("get_data_departments failed!")


def submit_one_file(_token, _filepath):
    headers = copy.deepcopy(BASE_HEADERS)
    headers["Authorization"] = "Bearer " + _token
    if "Content-Type" in headers:
        headers.pop("Content-Type")

    _filename = os.path.basename(_filepath)
    # 服务器端文件名生成逻辑：时间戳 + 原文件名
    _server_filename = str(int(time.time() * 1000)) + "-" + _filename

    print(f"   [Info] Uploading file content as: {_server_filename}")

    with open(_filepath, "rb") as f:
        # 注意：原代码这里硬编码了 application/json，如果上传zip可能需要修改
        body = {"file": (
            _server_filename,
            f.read(),
            "application/json"
        )}

    resp = requests.post(
        BASE_HOST_URL + "/add_task_update_file",
        headers=headers,
        files=body
    )
    resp = dict(resp.json())

    if "code" in resp and resp["code"] == 0:
        return _server_filename
    else:
        raise RuntimeError(f"File upload failed: {resp.get('msg', 'Unknown')}")


def submit_one_task(_token, _department, _model_name, _source, _desc, _filename, _rom_id, _rom_name):
    headers = copy.deepcopy(BASE_HEADERS)
    headers["Authorization"] = "Bearer " + _token
    body = {
        "department": _department,
        "model_name": _model_name,
        "source": _source,
        "desc": _desc,
        "file_name": _filename,
        "rom_id": _rom_id,
        "rom_name": _rom_name
    }
    resp = requests.post(BASE_HOST_URL + "/add_task_add_taskinfo", headers=headers, json=body)
    resp = dict(resp.json())
    if "code" in resp and resp["code"] == 0:
        return True
    else:
        raise RuntimeError(f"Task submission failed: {resp.get('msg', 'Unknown')}")


def get_data_task_info(_token, _department, _filename):
    # 用于验证任务是否创建成功
    headers = copy.deepcopy(BASE_HEADERS)
    headers["Authorization"] = "Bearer " + _token

    search_name = _filename
    if ".zip" in search_name:
        search_name = search_name[:search_name.rfind(".zip")]
    if ".json" in search_name:
        search_name = search_name[:search_name.rfind(".json")]

    body = {
        "page": 1,
        "page_size": 100,
        "search_msg": search_name,  # 使用原始文件名或处理过的文件名搜索
        "department": [_department],
        "status": [],
        "model_names": []
    }
    resp = requests.post(BASE_HOST_URL + "/data_tasksinfos", headers=headers, json=body)
    resp = dict(resp.json())

    if "code" in resp and resp["code"] == 0:
        if resp["data"]["count_totle"] >= 1:
            return resp["data"]["infos"][0]
    return None


# base_CONFIG = {
#     "username": "呼啸",  # 用户名
#     "password": "p5dme3Mj",  # 密码
#     "department": "资源教育部-辅学offline", # 部门名称
#     "file_path": "",  # 要上传的本地文件路径 (支持绝对路径)
#     "model_name": "doubao-seed-1-6-251015",  # 模型名称
#     "desc": "【理科认知】所属项目：【2025-LKRZ-理科辅学2.0优化项目】 任务编号：【PR-1253132584298】",  # 任务描述
#     "source_name": "doubao-seed-1-6-thinking"  # 数据源名称。
# }

base_CONFIG = {
    "username": "郭冬杰",  # 用户名
    "password": "wy7TMap3",  # 密码
    "department": "资源教育部-辅学-图形化讲解", # 部门名称
    "model_name": "gemini-3-pro-preview-thinking",  # 模型名称
    "source_name": "All",  # 数据源名称。
    "desc": "",  # 任务描述
    "rom_id": "PR-1483346667119",
    "rom_name": "小初单多模图形化讲解+大模型调用",
}

upload_fns = [
    '/mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解/小数单模-立体几何/2.phase1爬取输入_v2/小数单模-立体几何_试标_phase1爬取输入_part001_pv5.json',
]

for upload_fn in upload_fns:
    CONFIG = copy.deepcopy(base_CONFIG)
    CONFIG['file_path'] = upload_fn
    print("-" * 50)
    print("开始执行上传任务脚本...")
    print("-" * 50)

    # 0. 检查本地文件是否存在
    if not os.path.exists(CONFIG["file_path"]):
        print(f"[Error] 本地文件不存在: {CONFIG['file_path']}")
        continue

    try:
        # 1. 登录
        print(f"[1/5] Logging in as {CONFIG['username']}...")
        token = login(CONFIG["username"], CONFIG["password"])
        print("   Login successful.")

        # 2. 获取部门信息
        print("[2/5] Fetching department info...")
        #department = get_data_departments(token)
        department = CONFIG["department"]
        print(f"   Department: {department}")

        # 3. 获取并选择数据源
        print("[3/5] Fetching data sources...")
        target_source = CONFIG["source_name"]


        # 4. 上传物理文件
        print(f"[4/5] Uploading file: {CONFIG['file_path']}...")
        server_filename = submit_one_file(token, CONFIG["file_path"])
        print(f"   File uploaded successfully. Server ID: {server_filename}")

        # 5. 提交任务信息
        print("[5/5] Submitting task info...")
        submit_one_task(
            _token=token,
            _department=department,
            _model_name=CONFIG["model_name"],
            _source=target_source,
            _desc=CONFIG["desc"],
            _filename=server_filename,
            _rom_id=CONFIG["rom_id"],
            _rom_name=CONFIG["rom_name"]
        )
        print("   Task submission request sent.")

        # 6. (可选) 验证任务状态
        print("-" * 30)
        print("Verifying task status...")
        # 注意：搜索时通常用原始文件名搜索，去掉时间戳前缀
        original_filename = os.path.basename(CONFIG['file_path'])
        task_info = get_data_task_info(token, department, original_filename)

        if task_info:
            print("✅ Success! Task found in system.")
            print(f"   Task ID: {task_info.get('_id', 'N/A')}")
            print(f"   Status: {task_info.get('status', 'Unknown')}")
        else:
            print("⚠️ Task submitted but not immediately found in search list (might involve processing delay).")

    except RuntimeError as e:
        print(f"\n❌ Process Failed: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
