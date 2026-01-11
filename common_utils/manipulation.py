from typing import Any, List, Union
from .paths import parse_path, compile_key_path, M_DICT, M_ALL, M_IND

_MISSING = object()

# ==================== 删除逻辑 (保持不变) ====================
def delete_field_by_path(data: Any, path: str) -> None:
    steps = parse_path(path)
    if not steps: return

    def _delete(cur: Any, idx: int) -> None:
        if idx >= len(steps): return
        step = steps[idx]
        is_last = (idx == len(steps) - 1)

        if step.mode == "dict":
            if not isinstance(cur, dict): return
            if step.key not in cur: return
            if is_last:
                cur.pop(step.key, None)
                return
            nxt = cur.get(step.key)
            if isinstance(nxt, list):
                raise ValueError(f"路径 {path!r} 在 '.{step.key}' 处遇到 list，需显式写 [] 或 [idx]。")
            if isinstance(nxt, dict):
                _delete(nxt, idx + 1)
        elif step.mode == "all":
            if not isinstance(cur, dict): return
            if step.key not in cur: return
            lst = cur.get(step.key)
            if not isinstance(lst, list): return
            if is_last:
                cur[step.key] = []
                return
            for item in lst:
                _delete(item, idx + 1)
        elif step.mode == "indices":
            if not isinstance(cur, dict): return
            if step.key not in cur: return
            lst = cur.get(step.key)
            if not isinstance(lst, list): return
            raw_indices = step.indices or []
            n = len(lst)
            real_indices = [n + i if i < 0 else i for i in raw_indices]
            real_indices = [j for j in real_indices if 0 <= j < n]
            if not real_indices: return
            if is_last:
                for i in sorted(set(real_indices), reverse=True):
                    del lst[i]
                return
            for i in set(real_indices):
                _delete(lst[i], idx + 1)
    _delete(data, 0)

def delete_fields(samples, paths: Union[str, List[str]]) -> Any:
    if isinstance(paths, str): paths = [paths]
    for sample in samples:
        for p in paths:
            delete_field_by_path(sample, p)
        yield sample

# ==================== 重命名逻辑 (保持不变) ====================
def rename_field_by_path(data: Any, path: str, new_key: str) -> None:
    steps = parse_path(path)
    if not steps: return
    last = steps[-1]
    if last.mode != "dict":
        raise ValueError("重命名路径最后一段必须是普通字段名")
    if new_key == last.key: return

    def _rename(cur: Any, idx: int) -> None:
        if idx >= len(steps): return
        step = steps[idx]
        is_last = (idx == len(steps) - 1)
        if step.mode == "dict":
            if not isinstance(cur, dict): return
            if step.key not in cur: return
            if is_last:
                cur[new_key] = cur.pop(step.key)
                return
            nxt = cur.get(step.key)
            if isinstance(nxt, list):
                raise ValueError(f"路径 {path!r} 在遇到 list 时需显式写 []")
            if isinstance(nxt, dict):
                _rename(nxt, idx + 1)
        elif step.mode == "all":
            if not isinstance(cur, dict) or step.key not in cur: return
            lst = cur.get(step.key)
            if isinstance(lst, list):
                for item in lst:
                    _rename(item, idx + 1)
        elif step.mode == "indices":
            if not isinstance(cur, dict) or step.key not in cur: return
            lst = cur.get(step.key)
            if isinstance(lst, list):
                raw_indices = step.indices or []
                n = len(lst)
                for i in raw_indices:
                    j = n + i if i < 0 else i
                    if 0 <= j < n:
                        _rename(lst[j], idx + 1)
    _rename(data, 0)

def rename_fields(samples, mapping: dict[str, str]):
    for sample in samples:
        for path, new_key in mapping.items():
            rename_field_by_path(sample, path, new_key)
        yield sample

# ==================== 查询/获取逻辑 (更新) ====================

# [已删除] get_value_by_path_simple

def get_values_by_key_path(item: Any, key_path: str) -> List[Any]:
    steps = compile_key_path(key_path)
    if not steps: return [item]

    # Fast-path for simple dict access
    if all(m == M_DICT for (m, _, __) in steps):
        cur = item
        try:
            for (_, k, __) in steps:
                cur = cur[k]
        except (TypeError, KeyError):
            return []
        return [cur]

    out: List[Any] = []
    stack: List[tuple] = [(item, 0)]
    nsteps = len(steps)

    while stack:
        node, i = stack.pop()
        if i == nsteps:
            out.append(node)
            continue

        mode, key, idxs = steps[i]
        next_i = i + 1
        is_last = (next_i == nsteps)

        if mode == M_DICT:
            if isinstance(node, dict):
                nxt = node.get(key, _MISSING)
                if nxt is not _MISSING:
                    stack.append((nxt, next_i))
        elif mode == M_ALL:
            if isinstance(node, dict):
                lst = node.get(key, _MISSING)
                if isinstance(lst, list):
                    if is_last:
                        out.extend(lst)
                    else:
                        for elem in reversed(lst):
                            stack.append((elem, next_i))
        else: # M_IND
            if isinstance(node, dict):
                lst = node.get(key, _MISSING)
                if isinstance(lst, list) and idxs:
                    n = len(lst)
                    picked = []
                    for raw in idxs:
                        j = raw if raw >= 0 else n + raw
                        if 0 <= j < n:
                            picked.append(lst[j])
                    if is_last:
                        out.extend(picked)
                    else:
                        for elem in reversed(picked):
                            stack.append((elem, next_i))
    return out

def has_key_path(item: Any, key_path: str) -> bool:
    # 逻辑保持不变...
    steps = parse_path(key_path)
    if not steps: return True

    def _exists(cur: Any, idx: int) -> bool:
        if idx >= len(steps): return True
        step = steps[idx]
        is_last = (idx == len(steps) - 1)

        if step.mode == "dict":
            if not isinstance(cur, dict) or step.key not in cur: return False
            return _exists(cur[step.key], idx + 1)
        
        elif step.mode == "all":
            if not isinstance(cur, dict) or step.key not in cur: return False
            lst = cur[step.key]
            if not isinstance(lst, list): return False
            if is_last: return len(lst) > 0
            if not lst: return False
            return all(_exists(elem, idx + 1) for elem in lst)
            
        elif step.mode == "indices":
            if not isinstance(cur, dict) or step.key not in cur: return False
            lst = cur[step.key]
            if not isinstance(lst, list): return False
            raw = step.indices or []
            if not raw: return False
            n = len(lst)
            elems = []
            for r in raw:
                j = r if r >= 0 else n + r
                if 0 <= j < n: elems.append(lst[j])
                else: return False
            if is_last: return len(elems) > 0
            return all(_exists(e, idx + 1) for e in elems)
        return False

    return _exists(item, 0)