from pathlib import Path
from manim import logger
from manim_voiceover.helper import prompt_ask_missing_extras, remove_bookmarks

import requests
import json
import os
from urllib.parse import urlparse

import edge_tts

from manim_voiceover.services.base import SpeechService

class EdgeTTSService(SpeechService):
    """SpeechService class for edge tts."""

    def __init__(self, voice="zh-CN-XiaoxiaoNeural", **kwargs):
        SpeechService.__init__(self, **kwargs)
        self.voice = voice

    def generate_from_text(
        self, text: str, cache_dir: str = None, path: str = None, retries: int = 1, **kwargs
    ) -> dict:
        """"""
        if cache_dir is None:
            cache_dir = self.cache_dir

        input_text = remove_bookmarks(text)
        input_data = {"input_text": input_text, "service": "edge-tts"}

        cached_result = self.get_cached_result(input_data, cache_dir)
        if cached_result is not None:
            return cached_result

        if path is None:
            audio_path = self.get_audio_basename(input_data) + ".mp3"
        else:
            audio_path = path

        last_err = None
        for attempt in range(retries + 1):  # 总尝试次数 = 1 + retries（retries=1 即最多2次）
            try:
                # 调用接口
                communicate = edge_tts.Communicate(input_text, self.voice)
                communicate.save_sync(str(Path(cache_dir) / audio_path))
                last_err = None
                break
            except Exception as e:
                last_err = e
                logger.error(e)
                if attempt >= retries:
                    raise Exception("tts接口调用失败") from last_err

        json_dict = {
            "input_text": text,
            "input_data": input_data,
            "original_audio": audio_path,
        }

        return json_dict
