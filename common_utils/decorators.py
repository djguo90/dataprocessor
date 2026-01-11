from functools import wraps
from typing import Callable, Iterable, Any, Optional, Generator
from pathlib import Path
from .io import read_jsonl, save_jsonl
import logging

logger = logging.getLogger(__name__)

def checkpoint_to_file(func: Callable[..., Iterable[Any]]):
    """
    装饰器：将生成器函数的结果保存到文件，实现断点续传或缓存。
    
    参数:
      save_path (str): 保存路径
      mode (str): 
        - "read":  强制只读。文件不存在则报错。
        - "write": 强制执行函数并写入文件。完成后返回文件内容的生成器。
        - None:    不涉及文件操作，直接执行函数并消耗完生成器（通常用于调试或纯执行）。
      overwrite (bool): 
        - 仅在 mode="write" 时有效。
        - True:  强制重新执行函数并覆盖文件。
        - False: 如果文件已存在，则跳过执行，直接读取文件；如果文件不存在，则执行并写入。
    
    修复说明:
      原版使用了 deque 缓存所有数据，会导致大数据量下内存溢出 (OOM)。
      新版采用 "Write-then-Read" 策略：先将数据流写入磁盘，完成后重新打开文件进行流式读取。
      虽然增加了磁盘 I/O，但保证了内存占用的恒定和安全。
    """

    @wraps(func)
    def decorator_args(save_path: str, mode: Optional[str] = None, overwrite: bool = False):
        mode_norm = None if mode is None else str(mode).strip().lower()
        if mode_norm not in (None, "write", "read"):
            raise ValueError(f'checkpoint mode 必须是 "write" / "read" / None，当前是: {mode!r}')

        path = Path(save_path)

        @wraps(func)
        def wrapper(*args, **kwargs):
            # ==================== READ 模式 ====================
            if mode_norm == "read":
                if not path.exists():
                    logger.error(f"[Checkpoint] 读取模式失败，文件不存在: {path}")
                    raise FileNotFoundError(f"文件不存在: {path}")
                logger.info(f"[Checkpoint] 模式=READ，直接读取: {path}")
                yield from read_jsonl(path.as_posix())
                return

            # ==================== WRITE 模式 ====================
            if mode_norm == "write":
                path.parent.mkdir(parents=True, exist_ok=True)

                # 判定是否需要执行函数并写入
                should_run_and_write = False
                
                if overwrite:
                    should_run_and_write = True
                elif not path.exists():
                    should_run_and_write = True
                else:
                    # 文件存在且 overwrite=False -> 直接使用现有文件
                    # [建议补充] 明确告知用户命中缓存
                    logger.info(f"[Checkpoint] 缓存命中 (overwrite=False)。跳过执行，直接读取: {path}")
                    pass

                if should_run_and_write:
                    # [建议补充] 明确告知用户开始执行
                    reason = "overwrite=True" if overwrite else "文件不存在"
                    logger.info(f"[Checkpoint] 开始执行 ({reason})。结果将写入: {path}")
                    # 1. 获取原始生成器
                    src_gen = func(*args, **kwargs)
                    # 2. 消费生成器并写入文件 (save_jsonl 内部会迭代 src_gen)
                    #    此时数据流过内存直接入盘，不会积压
                    save_jsonl(src_gen, path.as_posix(), overwrite=True)

                # 3. 无论刚才是否写入，现在都从文件流式读取返回给下游
                #    保证下游拿到的永远是来自磁盘的数据流，内存安全
                if not path.exists():
                    # 极少数情况：函数执行了但没产生数据导致文件没生成？
                    # 或者 func 报错中断了。这里做个防御。
                    return 
                    
                yield from read_jsonl(path.as_posix())
                return

            # ==================== NONE 模式 ====================
            # 仅消耗生成器，不返回数据，不存文件
            # 这种模式通常用于只需要副作用（side-effects）的场景
            for _ in func(*args, **kwargs):
                pass
            return None

        return wrapper

    return decorator_args