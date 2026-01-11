import typing
from typing import List, Optional, Tuple, Union
from dataclasses import dataclass
from functools import lru_cache

# mode 常量
M_DICT = 0
M_ALL = 1
M_IND = 2

@dataclass
class PathStep:
    key: str
    mode: str  # "dict", "all", "indices"
    indices: Optional[List[int]] = None

@lru_cache(maxsize=1024)
def parse_path(path: str) -> List[PathStep]:
    """
    将路径字符串解析为 PathStep 列表。
    支持：.key, .key[], .key[0,1]
    """
    path = path.strip()
    while path.startswith("."):
        path = path[1:]

    if not path:
        return []

    raw_parts = [p.strip() for p in path.split(".") if p.strip()]
    steps: List[PathStep] = []

    for part in raw_parts:
        part = part.strip()
        if part.endswith("[]"):
            key = part[:-2].strip()
            steps.append(PathStep(key=key, mode="all"))
            continue

        if "[" in part and part.endswith("]"):
            key, idx_part = part.split("[", 1)
            key = key.strip()
            idx_str = idx_part[:-1].strip()
            indices: List[int] = []
            if idx_str:
                for tok in idx_str.split(","):
                    tok = tok.strip()
                    if not tok: continue
                    try:
                        indices.append(int(tok))
                    except ValueError:
                        pass
            steps.append(PathStep(key=key, mode="indices", indices=indices))
            continue

        steps.append(PathStep(key=part, mode="dict"))

    return steps

@lru_cache(maxsize=1024)
def compile_key_path(path: str) -> Tuple[Tuple[int, str, Optional[Tuple[int, ...]]], ...]:
    """
    将路径编译为更高效的元组形式，供 get_values 等高频函数使用
    """
    steps = parse_path(path)
    compiled = []
    for s in steps:
        if s.mode == "dict":
            compiled.append((M_DICT, s.key, None))
        elif s.mode == "all":
            compiled.append((M_ALL, s.key, None))
        elif s.mode == "indices":
            compiled.append((M_IND, s.key, tuple(s.indices or ())))
        else:
            raise ValueError(f"unknown mode: {s.mode}")
    return tuple(compiled)