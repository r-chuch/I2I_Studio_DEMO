# app/services/agents/agent2_creativity.py

import json
from pathlib import Path
from typing import List, Dict, Any
import re
from datetime import datetime
import time

# import base_agent as ba
import app.services.agents.base_agent as ba
from app.services.prompt_templates import AGENT2_GEN_PAIN_POINT, AGENT2_GEN_SCAMPER, AGENT2_GEN_REFINED_CONCEPT


OUTPUT_DIR = Path.cwd() / "app" / "output_data"


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