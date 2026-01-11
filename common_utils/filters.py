import glob
import json
from typing import List, Union, Any
import logging
from .manipulation import get_values_by_key_path
logger = logging.getLogger(__name__)

def _extract_key_value(item: Any, path: str) -> Union[str, None]:
    """
    辅助函数：从 item 中提取 path 对应的值，并转为 string 以便去重。
    如果 path 匹配到多个值（如列表），则将其转换为 tuple 字符串。
    """
    vals = get_values_by_key_path(item, path)
    
    if not vals:
        return None
    
    # 只有一个值，直接取出来（模拟原 simple 行为）
    if len(vals) == 1:
        v = vals[0]
    else:
        # 有多个值（比如 path 包含了 []），将其作为 tuple 处理
        v = tuple(vals)
        
    return str(v) if v is not None else None

def remove_duplicates_interior(samples, key_paths: Union[str, List[str]]):
    """
    内部根据字段去重
    """
    if isinstance(key_paths, str):
        key_paths = [key_paths]
    seen = set()
    for sample in samples:
        key_list = []
        for path in key_paths:
            v_str = _extract_key_value(sample, path)
            key_list.append(v_str)
        
        key_tuple = tuple(key_list)
        if key_tuple not in seen:
            seen.add(key_tuple)
            yield sample

def remove_duplicates_exterior(samples, target_file_patterns, key_paths):
    """
    外部根据字段去重（读取 target_file_patterns 中的数据建立黑名单）
    """
    if isinstance(target_file_patterns, str):
        target_file_patterns = [target_file_patterns]
    if isinstance(key_paths, str):
        key_paths = [key_paths]
        
    target_file_paths = []
    for tfp in target_file_patterns:
        matched = glob.glob(tfp, recursive=True)
        if not matched:
            # [日志点 1]：黑名单路径写错了，这很危险，会导致去重失效
            logger.warning(f"[外部去重] 目标文件模式未匹配到任何文件: {tfp}")
        target_file_paths.extend(matched)
    target_file_paths = sorted(target_file_paths)
    
    # [日志点 2]：告知用户正在进行高耗时操作
    if target_file_paths:
        logger.info(f"[外部去重] 开始加载去重库，共 {len(target_file_paths)} 个文件...")
    
    target_key_set = set()
    loaded_count = 0
    # 预加载黑名单
    for tfp in sorted(target_file_paths):
        with open(tfp, "r", encoding="utf-8") as reader:
            for l in reader:
                try:
                    l_json = json.loads(l)
                    key_list = []
                    for path in key_paths:
                        v_str = _extract_key_value(l_json, path)
                        key_list.append(v_str)
                    target_key_set.add(tuple(key_list))
                    loaded_count += 1
                except Exception:
                    continue
    logger.info(f"[外部去重] 去重库加载完成。包含 {len(target_key_set)} 个唯一键 (原始记录 {loaded_count} 条)")

    # 过滤流
    duplicate_count = 0
    yield_count = 0
    for sample in samples:
        key_list = []
        for path in key_paths:
            v_str = _extract_key_value(sample, path)
            key_list.append(v_str)
        
        if tuple(key_list) not in target_key_set:
            yield_count += 1
            yield sample
        else:
            duplicate_count += 1