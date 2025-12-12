import json
from pathlib import Path
from typing import List, Dict, Any
import re
from datetime import datetime
import time

# import base_agent as ba
import app.services.agents.base_agent as ba


OUTPUT_DIR = Path.cwd() / "app" / "output_data"

# --- PROMPT 1: 痛點分析 ---
AGENT2_GEN_PAIN_POINT = """
你是資深產品洞察分析師（Product Insight Analyst）。以下輸入內容是影片相關的問答資料陣列，每筆包含 
-id:問題順序 
-question:對影片內容的痛點洞察所以提出的問題
-hint:關於該問題的提示
-suggestion:關於該問題的建議回覆
-evidence:資料來源
-answer:使用者針對問題進行發想後的回答

任務規則：
從這些資料整合出「使用者發現關於這部影片內容所隱含的痛點」，並針對該痛點提出 3 個可能的現有解決方案或產品（名詞），最後以嚴格的 JSON 格式輸出。

處理步驟（請在內部依序執行，但輸出僅為最後的 JSON）：
1) 痛點分析：
   - 逐筆閱讀每個物件，擷取關鍵片段：使用者答案(answer)、question 與 evidence。
   - 找出資料中出現頻率最高或最有一致性的議題，整合為單一「痛點主題」。
   - 痛點描述需為繁體中文，介於 30 到 80 個中文字，採中性、可被引用的表述。
2) 解決方案發想：
   - 針對上述歸納的痛點，聯想 3 個「現有的解決方案、產品類別或具體工具」。
   - 解決方案必須是「名詞」或「短詞」（例如：「番茄鐘App」、「降噪耳機」、「專案管理軟體」）。
3) 格式化輸出：
   - 將結果封裝為 JSON。

輸入資料：
{qa_list}

輸出規格（嚴格遵守）：
1. 僅輸出一個標準 JSON 字串。
2. 絕對不要使用 Markdown 格式（禁止使用 ```json 或 ``` 包裹）。
3. 輸出的第一個字元必須是 "{"，最後一個字元必須是 "}"。
4. JSON 結構必須如下：
{{
    "pain_point": "<痛點主題的詳細描述>",
    "solutions": [
        "<解決方案名詞1>",
        "<解決方案名詞2>",
        "<解決方案名詞3>"
    ]
}}

若輸入資料為空或無法判斷，請輸出：
{{
    "pain_point": "無足夠資料判斷痛點",
    "solutions": []
}}

現在開始處理，請直接輸出 JSON 字串：
"""

# --- PROMPT 2: SCAMPER 與 強力組合單詞生成 ---
AGENT2_GEN_SCAMPER = """
你是資深創意引導師（Creative Facilitator）。
目前的使用者痛點是：「{pain_point}」
使用者選擇作為參考的現有解決方案是：「{selected_solution}」

你的任務包含兩部分：

任務一：生成 SCAMPER 引導提問與建議回覆
針對該「現有解決方案」，提出 SCAMPER 七個維度的引導提問，並針對每個提問提供一個「建議回覆」（參考點子）。
目的是激發使用者改良此方案以解決痛點。
提問必須「具體」且「針對性強」，請不要只給通用的定義，而是要結合解方的情境。
建議回覆則提供一個具體的創意範例，引導使用者思考。

   - Substitute (替代): 有什麼成分、規則、受眾或技術可以被替代？
   - Combine (合併): 能與什麼功能、外部服務或異業合併？
   - Adapt (調整): 有什麼其他領域（如自然界、其他產業）的點子可以借用？
   - Modify (修改): 改變形狀、屬性、大小或體驗流程會如何？
   - Put to other uses (其他用途): 這個解方還能用在什麼完全不同的場景或對象？
   - Eliminate (消除): 有什麼非核心的功能、成本或步驟可以剔除以簡化體驗？
   - Reverse (重組/反向): 如果把流程倒過來做，或重新安排因果順序會怎樣？

任務二：生成 15 個強力組合（Forced Connection）單詞
請提供 15 個「完全不相關」、「具象」且「隨機」的名詞（Random Nouns）。
   - 這些詞將用於強迫使用者進行創意的「強制關聯」，所以越跳躍、越具體越好。
   - 範例：火山、仙人掌、保險箱、外星人、薩克斯風、水母、積木...
   - 避免使用抽象名詞（如：愛、和平、效率），請給予視覺化強的物件。

輸出規格（嚴格遵守）：
1. 僅輸出一個標準 JSON 字串。
2. 絕對不要使用 Markdown 格式（禁止使用 ```json 或 ``` 包裹）。
3. JSON 結構必須如下：
{{
    "scamper_questions": {{
        "S": {{
            "question": "針對{selected_solution}的替代性提問...",
            "suggestion": "針對該提問的一個建議回覆範例..."
        }},
        "C": {{
            "question": "針對{selected_solution}的合併性提問...",
            "suggestion": "針對該提問的一個建議回覆範例..."
        }},
        "A": {{
            "question": "針對{selected_solution}的調整性提問...",
            "suggestion": "針對該提問的一個建議回覆範例..."
        }},
        "M": {{
            "question": "針對{selected_solution}的修改性提問...",
            "suggestion": "針對該提問的一個建議回覆範例..."
        }},
        "P": {{
            "question": "針對{selected_solution}的其他用途提問...",
            "suggestion": "針對該提問的一個建議回覆範例..."
        }},
        "E": {{
            "question": "針對{selected_solution}的消除性提問...",
            "suggestion": "針對該提問的一個建議回覆範例..."
        }},
        "R": {{
            "question": "針對{selected_solution}的反向性提問...",
            "suggestion": "針對該提問的一個建議回覆範例..."
        }}
    }},
    "random_words": [
        "名詞1", "名詞2", "名詞3", "名詞4", "名詞5", 
        "名詞6", "名詞7", "名詞8", "名詞9", "名詞10", 
        "名詞11", "名詞12", "名詞13", "名詞14", "名詞15"
    ]
}}

現在開始處理，請直接輸出 JSON 字串：
"""

AGENT2_GEN_REFINED_CONCEPT = """
你是資深產品經理與創新顧問。
請根據以下資訊，協助使用者將零散的創意收斂為一個具體、有吸引力的「新產品概念草案」。

【背景資訊】
1. 痛點: {pain_point}
2. 原型解方: {selected_solution}

【使用者發想素材】
3. SCAMPER 發想內容: 
{scamper_ideas}

4. 強制關聯詞 (Random Word): {random_word}
   (請思考如何將這個詞彙的「特性」、「意象」或「運作原理」融入產品概念中，作為創意的亮點)

5. 使用者目前的初步想法: 
{user_draft}

【任務】
請綜合上述所有素材，生成一段約 150~250 字的產品概念描述。
這個概念必須：
- 具體解決上述痛點。
- 巧妙融合「強制關聯詞」的元素（可以是功能上的、視覺上的或比喻上的）。
- 整合使用者的 SCAMPER 點子。
- 語氣需充滿熱情且具說服力。

【輸出格式】
請直接輸出一段純文字（不要 Markdown，不要 JSON），作為給使用者的建議。
"""

class Agent2Creativity():
    name = "agent2_creativity"

    merged_list = []
    pain_point = ''

    def merge_whys_with_answers(self, whys: List[Dict[str, Any]], answers: List[str]) -> List[Dict[str, Any]]:
        """
        將 whys（list of dict）與 answers（list of str）合併，假設順序對齊。
        """
        merged = []
        # 避免長度不一致導致 crash，取最小值
        min_len = min(len(whys), len(answers))
        for i in range(min_len):
            new_item = whys[i].copy()
            new_item["answer"] = answers[i]
            merged.append(new_item)
        return merged
    
    def _call_llm_with_retry(self, prompt: str, retries: int = 3, delay: int = 2) -> str:
        for i in range(retries):
            try:
                response = ba.gen_response(prompt)
                if response:
                    return response
                else:
                    print(f"[Agent2] Attempt {i+1} failed: Empty response.")
            except Exception as e:
                print(f"[Agent2] Attempt {i+1} exception: {e}")
                if "503" in str(e):
                    print("[Agent2] 503 Overloaded, retrying...")
                # 其他錯誤也稍作等待重試
            time.sleep(delay * (i + 1))
        return None

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        通用的 JSON 解析輔助函式，處理 LLM 可能回傳的 Markdown 標記或雜訊
        """
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # 嘗試用正則找到第一個 {...} 區塊
            m = re.search(r'\{.*\}', response_text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    return {"raw_text": response_text, "error": "JSON decode failed after regex"}
            else:
                return {"raw_text": response_text, "error": "No JSON block found"}

    def gen_pain_point(self, whys_list: List[Dict], whys_answers: List[str], filename: str = None):
      """
      階段一：生成痛點與現有解決方案（簡易的 try/except）
      """
      try:
          # 1. 準備合併資料與 prompt
          self.merged_list = self.merge_whys_with_answers(whys_list, whys_answers)

          # 檢查是否有資料，避免空資料送出
          if not self.merged_list:
              return "No data provided", None

          prompt = AGENT2_GEN_PAIN_POINT.replace("{qa_list}", json.dumps(self.merged_list, ensure_ascii=False))

          # 2. 呼叫 LLM
          response_text = ba.gen_response(prompt)

          # 3. 解析 JSON
          parsed = self._parse_json_response(response_text)

          # 暫存痛點供後續使用 (若有需要 stateful 操作)
          if "pain_point" in parsed:
              self.pain_point = parsed["pain_point"]

          # 4. 輸出檔案
          OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
          if filename is None:
              filename = "agent2_pain_point_output.json"
          file_path = OUTPUT_DIR / filename

          with file_path.open("w", encoding="utf-8") as f:
              json.dump(parsed, f, ensure_ascii=False, indent=2)

          return response_text, file_path

      except Exception as e:
          # 簡易錯誤處理：回傳錯誤訊息與 None
          return f"Error: {e}", None

    def gen_scamper_prompts(self, pain_point: str, selected_solution: str, filename: str = None):
        """
        階段二：生成 SCAMPER 思考引導與隨機單詞，並更新至現有 JSON 檔案中。
        Args:
            pain_point: 第一階段產生的痛點描述
            selected_solution: 使用者從第一階段建議中選出的一個現有解決方案
            filename: 要寫入的目標檔案名稱，預設為 "agent2_pain_point_output.json"
        """
        # 1. 準備 Prompt
        prompt = AGENT2_GEN_SCAMPER.format(
            pain_point=pain_point, 
            selected_solution=selected_solution
        )

        # 2. 呼叫 LLM
        response_text = ba.gen_response(prompt)

        # 3. 解析 JSON
        parsed = self._parse_json_response(response_text)

        # 4. 讀取並更新現有檔案
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        if filename is None:
            filename = "agent2_pain_point_output.json"
        
        file_path = OUTPUT_DIR / filename
        
        # 讀取既有資料 (若檔案存在)
        data_to_save = {}
        if file_path.exists():
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    data_to_save = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Existing file {filename} is corrupted. Overwriting.")
        
        # 合併新資料 (保留原本的痛點與解決方案，加入 scamper_questions 與 random_words)
        data_to_save.update(parsed)
        
        # 紀錄使用者這次選擇了哪個解決方案來做 SCAMPER，方便前端呈現
        data_to_save["selected_solution_for_scamper"] = selected_solution
        # 紀錄使用者選擇（或當下使用）的痛點，以防與原始生成不同
        data_to_save["selected_pain_point_for_scamper"] = pain_point

        # 寫回檔案
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            
        return data_to_save, file_path

    def gen_refined_concept(self, pain_point, selected_solution, scamper_ideas, random_word, user_draft):
      """
      綜合使用者的 SCAMPER 想法、強制關聯詞與初步草案，生成優化建議。
      """
      # 整理 SCAMPER 想法為字串
      scamper_text = ""
      for k, v in scamper_ideas.items():
          if v and v.strip():
              scamper_text += f"- {k}: {v}\n"
      if not scamper_text:
          scamper_text = "(使用者未填寫具體 SCAMPER 想法)"

      if not user_draft:
          user_draft = "(使用者尚未填寫初步想法)"

      prompt = AGENT2_GEN_REFINED_CONCEPT.format(
          pain_point=pain_point,
          selected_solution=selected_solution,
          scamper_ideas=scamper_text,
          random_word=random_word,
          user_draft=user_draft
      )

      # 呼叫 LLM
      response_text = self._call_llm_with_retry(prompt)
      
      # 這裡直接回傳文字，不需解析 JSON
      if not response_text:
          return "AI 暫時無法回應，請稍後再試。"
      
      return response_text
# whys_list=[
#     {
#       "id": 1,
#       "question": "為什麼年輕人想到進一步交往會感到有壓力，寧願維持現狀？",
#       "hint": "思考戀愛可能帶來的時間、精力、自由度損失與社會期望。",
#       "suggestion": "因為他們預期戀愛會帶來過多的考量與顧忌，需要花費大量時間溝通協商，被視為像是多一份工作，與追求個人自由、時間安排的慾望相衝突。",
#       "evidence": "有伴侶的時候需要考量跟顧忌的有點太多了...我想到我還要再去 做一個多的 很像是多一份工作的事情 我就覺得好累喔"
#     },
#     {
#       "id": 2,
#       "question": "為什麼戀愛會被年輕人視為是一種壓力與負擔，而非甜蜜的體驗？",
#       "hint": "探究個人主義的興起、對自我實現的重視以及對關係的潛在犧牲。",
#       "suggestion": "個人主義的崛起使年輕人更重視自我實現，不願為關係犧牲個人自由，導致戀愛中的妥協被視為對自我完整性的侵害，而非為愛付出。",
#       "evidence": "不願意犧牲個人的責任自由...個人自由度跟感情生活其實某種程度是對立的...當代社會很少鼓勵人們 要為了一段關係做出個人...犧牲"
#     },
#     {
#       "id": 3,
#       "question": "為什麼年輕人傾向追求個人自由，勝過建立深刻關係連結？",
#       "hint": "考慮經濟壓力、3C產品對社交的替代作用，以及人生規劃的不確定性。",
#       "suggestion": "現實社會中停滯的經濟和激烈競爭使年輕人將重心放回自我實踐，而3C產品滿足了部分情感需求。在人生規劃不確定的情況下，他們更傾向掌握自己的時間與步調，不願將戀愛視為必須投入的優先選項。",
#       "evidence": "停滯的經濟 激烈的競爭 讓很多年輕人認為 努力就有回報的時代已經過去了 開始把重心放在自己身上 更重視自我的實踐...情感需求被網路滿足 戀愛就變得不再那麼迫切 也沒有那麼值得投入了"
#     }
#   ]

# whys_answers= [
#   "因為他們預期戀愛會帶來過多的考量與顧忌，需要花費大量時間溝通協商，被視為像是多一份工作，與追求個人自由、時間安排的慾望相衝突。",
#   "個人主義的崛起使年輕人更重視自我實現，不願為關係犧牲個人自由，導致戀愛中的妥協被視為對自我完整性的侵害，而非為愛付出。",
#   "現實社會中停滯的經濟和激烈競爭使年輕人將重心放回自我實踐，而3C產品滿足了部分情感需求。在人生規劃不確定的情況下，他們更傾向掌握自己的時間與步調，不願將戀愛視為必須投入的優先選項。"
# ]
# ag2 = Agent2Creativity()
# # response_text, saved_path = ag2.gen_pain_point(whys_list=whys_list, whys_answers=whys_answers)
# # print("LLM 原始回應：", response_text)
# # print("已儲存至：", saved_path)

# try:
#     filename = "agent2_pain_point_output.json"
#     saved_path = OUTPUT_DIR / filename
#     with open(saved_path, 'r', encoding='utf-8') as f:
#         data = json.load(f)
#         pain_point = data.get("pain_point", "測試痛點")
#         # 假設使用者選了第一個解方，若無則用預設
#         solutions = data.get("solutions", [])
#         selected_sol = solutions[0] if solutions else "交友軟體"
# except Exception as e:
#     pain_point = "年輕人覺得戀愛麻煩"
#     selected_sol = "交友軟體"

# print(f"\n[模擬前端選擇]\n痛點: {pain_point}\n選擇解方: {selected_sol}")

# # 測試 2: 生成 SCAMPER 引導
# print("\n--- 測試階段 2: 生成 SCAMPER 與隨機單詞 ---")
# # 這裡我們傳入 saved_path.name，確保它更新同一個檔案
# scamper_data, scamper_path = ag2.gen_scamper_prompts(pain_point, selected_sol, filename=saved_path.name)
# print("SCAMPER JSON 結構:", list(scamper_data.keys()))
# print(f"隨機單詞範例: {scamper_data.get('random_words', [])[:5]}...")
# print(f"檔案已更新至: {scamper_path}")