# app/services/agents/agent1_insight.py
import json
import app.services.agents.base_agent as ba
from pathlib import Path
from typing import List
import math
import time
import random

OUTPUT_DIR = Path.cwd() / "app" / "output_data"

AGENT1_THREE_WHYS = """
你是洞察分析師（Content Insight Analyst），任務是從影片字幕摘錄中擷取痛點並對第一個痛點執行「三個為什麼」(Three Whys) 深層推演。請嚴格遵守下列規則並僅輸出最後的 JSON（請勿輸出任何額外文字或說明）。

輸入：
三引號包起來的字幕摘錄如下：
\"\"\"{subtitle_excerpt}\"\"\"

任務規則：
1) 先透過字幕內容，整理一份摘要概述這部影片的重點內容與議題等。將該摘要放到JSON格式中的summary
2) 擷取痛點（pain_points）：
   - 從字幕中擷取 3 個「明確且可行動的痛點」。
   - 每個痛點用一句話描述（繁體中文），長度不超過 30 個中文字符。
   - 若字幕中無明確痛點，請產生最多 3 個合理推論的痛點，所有此類推論之 evidence 欄位需標註 "推論（字幕未明確提及）"。
3) Three Whys（針對每一個 pain_point）：
   - 依據每個痛點想出一個有關該痛點的問題，用 為甚麼 作為問題的發想，例如:問為甚麼會出現這個問題?
   - 依序列出三個「為什麼」的問題（why_1、why_2、why_3），每層皆包含：
     a) question:一句短描述（繁體中文，長度不超過 50 個中文字符）說明該層問題；
     b) hint:針對該問題提供回答者想法方向，可以往哪方面思考問題的答案。
     c) suggestion:對於該問題給予可能的回答提示。
     d) evidence：若能直接從字幕引用，請提供字幕原句（可截短並加省略號）；若無則填 "字幕未直接提及" 或 "推論（字幕未明確提及）"。
4) 輸出格式（嚴格 JSON，且僅輸出 JSON）：
   - JSON 結構如下（欄位順序需一致）：

{{
    "video_title": "<由字幕推測的標題或空字串>",
    "summary": "<由字幕推測的影片重點概述>",
    "pain_points": [
        {{"id": "p1", "text": "<痛點一句話>", "evidence": "<字幕原句或 '推論（字幕未明確提及）'>"}},
        {{"id": "p2", "text": "<痛點一句話>", "evidence": "<...>"}},
        {{"id": "p3", "text": "<痛點一句話>", "evidence": "<...>"}}
    ],
    "three_whys": [
        {{"id": 1, "question": "<為什麼 1 的問題>","hint": "<回答問題的提示>","suggestion": "<建議回覆>", "evidence": "<字幕原句或推論>"}},
        {{"id": 2, "question": "<為什麼 2 的問題>","hint": "<回答問題的提示>","suggestion": "<建議回覆>", "evidence": "<...>"}},
        {{"id": 3, "question": "<為什麼 3 的問題>","hint": "<回答問題的提示>","suggestion": "<建議回覆>", "evidence": "<...>"}}
    ]
}}

   - 若實際擷取不到 3 個痛點，pain_points 陣列請只包含可取得的項目（至少 0 項），但 three_whys 必須仍然存在且針對第一個 pain_point 執行；若沒有任何 pain_point，three_whys 中的 level 0 與後續層級皆填空字串或 "無"（依情況填 "無"）。
   - 所有文字使用繁體中文 UTF-8。
4) 輸出檢核（LLM 必須在輸出前自我檢核）：
   - 確認輸出為有效 JSON（可被 JSON.parse 解析）。
   - 確認欄位名稱、型別與順序符合範本。
   - **嚴重警告：絕對不要使用 Markdown 格式（不要使用 ```json 或 ``` 包裹內容）。**
   - **嚴重警告：輸出內容必須是純文字（Raw Text）。**

注意：
- 若能推測影片標題，請將 video_title 填入推測標題（不超過 60 個中文字）。若不能推測，填空字串 。
- 請盡量以字幕原句作為 evidence（若需截短引用，請以「...」表示刪節）。
- 切勿包含任何指令性或元資料文字在最終輸出之外。

現在開始處理。
**輸出指引：**
1. 不需要任何問候語或結尾。
2. 不需要 Markdown 程式碼區塊。
3. 輸出的第一個字元必須是 {{，最後一個字元必須是 }}。
4. 確保輸出是純 JSON 字串。
"""



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
