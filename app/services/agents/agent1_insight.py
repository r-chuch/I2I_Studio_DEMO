# app/services/agents/agent1_insight.py
import json
from pathlib import Path
from typing import List
import math
import time
import random

import app.services.agents.base_agent as ba
from app.services.prompt_templates import AGENT1_THREE_WHYS

OUTPUT_DIR = Path.cwd() / "app" / "output_data"



class Agent1Insight():
    name = "agent1_insight"

    def process(self, input_data: dict) -> dict:
        subtitle = input_data.get("subtitle", "") or ""
        # 取前 N 字或句做為 excerpt
        excerpt = subtitle[:5000]  # 適度截斷
        prompt = AGENT1_THREE_WHYS.format(subtitle_excerpt=excerpt)
        try:
            raw = ba.gen_response(prompt)
            parsed = json.loads(raw)
            return {"ok": True, "data": parsed, "errors": []}
        except Exception as e:
            return {"ok": False, "data": {}, "errors": [str(e)]}
        
    def text_gen(self,video_id):
        try:
            
            raw_path = OUTPUT_DIR / f"{video_id}_raw.txt"
            text = raw_path.read_text(encoding="utf-8")

            prompt = AGENT1_THREE_WHYS.format(subtitle_excerpt=text)
            raw = ba.gen_response(prompt)
            parsed = json.loads(raw)

            out_path = OUTPUT_DIR / "agent1_output.json"
            out_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"寫入完成：{out_path.resolve()}")
            return True

        except Exception as e:
            # 其他不可預期的例外
            print("執行 text_gen 時發生例外：", type(e).__name__, e)
            return False

# ag1 =Agent1Insight()
# ag1.test_gen("d7DrbH0czwk")
