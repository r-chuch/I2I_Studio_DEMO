# app/services/agents/agent3_optimize.py
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

# import base_agent as ba
import app.services.agents.base_agent as ba  
OUTPUT_DIR = Path.cwd() / "app" / "output_data"



# 六頂思考帽的提示模板（LLM prompt）
AGENT3_SIX_HATS = """
你是創意優化專家（Creative Optimization Agent）。任務是針對使用者提供的一段初步構想（concept），以「六頂思考帽」(Six Thinking Hats) 的框架進行分析。

輸入構想：
\"\"\"{concept}\"\"\"

任務規則：
1) 使用繁體中文。
2) 針對每頂帽子產生 **exactly 1 個問題**（q，40字內）與 **exactly 1 個建議**（suggestion，10-80字）。
3) 嚴格遵守 JSON 格式輸出，**禁止使用 Markdown 語法**（不要輸出 ```json）。

六頂帽子定義（僅供參考）：
- 白帽：事實與數據。
- 紅帽：直覺與情感。
- 黑帽：風險與批判。
- 黃帽：利益與價值。
- 綠帽：創意與替代方案。
- 藍帽：流程與控制。

輸出格式範本（請嚴格遵守此 JSON 結構）：
{{
  "concept": "在此填入輸入的 concept 內容",
  "hats": [
    {{
      "id": "white",
      "name": "白帽（事實/資訊）",
      "q": "<問題短句>",
      "suggestion": "<範例回覆>"
    }},
    {{
      "id": "red",
      "name": "紅帽（情感/直覺）",
      "q": "<問題短句>",
      "suggestion": "<範例回覆>"
    }},
    {{
      "id": "black",
      "name": "黑帽（批判/風險）",
      "q": "<問題短句>",
      "suggestion": "<範例回覆>"
    }},
    {{
      "id": "yellow",
      "name": "黃帽（正面/價值）",
      "q": "<問題短句>",
      "suggestion": "<範例回覆>"
    }},
    {{
      "id": "green",
      "name": "綠帽（創意/替代）",
      "q": "<問題短句>",
      "suggestion": "<範例回覆>"
    }},
    {{
      "id": "blue",
      "name": "藍帽（流程/管理）",
      "q": "<問題短句>",
      "suggestion": "<範例回覆>"
    }}
  ]
}}

輸出檢核：
1. 僅回傳一個有效的 JSON 字串。
2. 輸出的第一個字元必須是 "{{"，最後一個字元必須是 "}}"。
3. **絕對不要**使用 ```json 或 ``` 包裹內容。
4. 確保 JSON 格式正確，無多餘逗號。

現在開始處理並輸出 JSON：
"""


# --- 新增 Prompt: 整合構想 ---
AGENT3_INTEGRATE_CONCEPT = """
你是資深產品經理與創新策略專家。
任務：將使用者的「初步構想」與使用者針對「六頂思考帽」的反思內容進行深度整合，產出一個邏輯嚴密、可行性高的「最終定案構想」。

輸入資訊：
1. 初步構想：
\"\"\"{concept}\"\"\"

2. 六頂思考帽回饋（使用者針對風險、創意、價值等觀點的考量）：
\"\"\"{hats_summary}\"\"\"

整合要求：
1. 請保留原構想的核心價值。
2. 具體納入六頂帽子的建議內容，特別是針對「黑帽（風險）」提出的解決對策，以及「綠帽（創意）」的延伸亮點。
3. 消除邏輯矛盾，使整體方案更加完整。
4. 輸出一段約 300-500 字的完整構想描述，語氣專業且具建設性。

請直接輸出最終構想內容（純文字），不要有特殊符號如*：
"""

# --- 新增 Prompt: 撰寫企畫書 ---
AGENT3_WRITE_PROPOSAL = """
你是頂尖的商業企劃撰寫專家。
任務：根據提供的「最終定案構想」，撰寫一份優秀、明瞭且具說服力的「一頁式企畫書」(One-Page Proposal)。

最終定案構想：
\"\"\"{final_concept}\"\"\"

企畫書結構要求（請使用 Markdown 格式）：
# [專案名稱] 一頁式企畫書

## 1. 價值主張 (Value Proposition)
- 用一句話打動人心的標語 (Slogan)。
- 核心價值說明。

## 2. 痛點與解決方案 (Problem & Solution)
- 目標客群面臨什麼問題？
- 我們的產品如何具體解決？

## 3. 產品特色與創新點 (Key Features & Innovation)
- 列出 3-5 個關鍵功能或創新機制。

## 4. 執行與市場策略 (Execution & Market)
- 獲利模式或推廣策略摘要。

## 5. 結論 (Conclusion)
- 結語，強化願景。

請確保語氣專業、熱情且精鍊，適合向投資人或決策者提案。
"""



class Agent3Optimize():
    name = "agent3_optimize"

    
    # 片段：在 agent3_optimize.py 中使用
    def gen_six_hats(self, input_data: str) :
        concept = input_data

        concept_excerpt = concept if len(concept) <= 4000 else concept[:4000]
        prompt = AGENT3_SIX_HATS.format(concept=concept_excerpt)

        try:
            raw = ba.gen_response(prompt)
        except Exception as e:
            return {},None

        parsed = None
        errors: List[str] = []
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # 嘗試用正則擷取第一個 {...} JSON 區塊
            m = re.search(r'\{(?:[^{}]|(?R))*\}', raw, re.DOTALL)
            if m:
                try:
                    parsed = json.loads(m.group(0))
                except json.JSONDecodeError:
                    errors.append("LLM 回傳非標準 JSON，且擷取後仍解析失敗。")
                    parsed = {"raw_text": raw}
            else:
                errors.append("LLM 回傳不包含 JSON 物件。")
                parsed = {"raw_text": raw}

        # 檢查 hats 結構（輕量驗證：存在六頂帽子且為陣列）
        try:
            hats = parsed.get("hats", [])
            if not isinstance(hats, list) or len(hats) != 6:
                errors.append("輸出 hats 欄位格式異常（應為長度為6的陣列）。")
        except Exception:
            errors.append("檢查 hats 欄位時發生例外。")

        # 儲存結果
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"agent3_six_hats_output.json"
        file_path = OUTPUT_DIR / filename
        try:
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=2)
        except Exception as e:
            errors.append(f"儲存檔案失敗：{e}")

        return parsed, file_path
    def gen_final_proposal(self, concept: str, hats_input: Union[List[Dict[str, Any]], Dict[str, str]]) -> str:
        """
        將使用者的初步構想與六頂思考帽輸入整合，生成最終一頁式企畫書。
        支援傳入 List[Dict] (包含建議與問題的完整結構) 或 Dict[str, str] (僅包含使用者填寫內容的舊格式)。
        
        Step 1: 整合構想 -> 最終構想
        Step 2: 最終構想 -> 企畫書文案
        """
        hats_summary = ""

        # 處理新格式：List[Dict] (包含 id, name, q, suggestion 等)
        if isinstance(hats_input, list):
            for hat in hats_input:
                name = hat.get("name", "思考帽")
                q = hat.get("q", "")
                suggestion = hat.get("suggestion", "")
                # 嘗試讀取使用者可能填寫的回饋 (若資料結構有包含使用者的 answer 或 content)
                # 若無使用者填寫內容，則使用建議與問題作為上下文
                user_content = hat.get("answer") or hat.get("content") or hat.get("user_feedback") or ""
                
                hats_summary += f"【{name}】\n"
                if q:
                    hats_summary += f"  - 思考引導: {q}\n"
                if suggestion:
                    hats_summary += f"  - 參考建議: {suggestion}\n"
                if user_content:
                    hats_summary += f"  - 使用者想法: {user_content}\n"
                hats_summary += "\n"

        # 處理舊格式：Dict[str, str] (key 為欄位名稱, value 為使用者填寫內容)
        elif isinstance(hats_input, dict):
            hat_labels = {
                'hat_white_hat': '白帽（事實）',
                'hat_red_hat': '紅帽（情感）',
                'hat_black_hat': '黑帽（風險）',
                'hat_yellow_hat': '黃帽（價值）',
                'hat_green_hat': '綠帽（創意）',
                'hat_blue_hat': '藍帽（流程）'
            }
            for key, label in hat_labels.items():
                content = hats_input.get(key, "")
                if content and content.strip():
                    hats_summary += f"- {label}: {content}\n"
        
        if not hats_summary.strip():
            hats_summary = "(使用者未針對六頂思考帽提供具體回饋，將依據一般性原則進行優化)"

        # 2. Step 1: 整合構想
        print(f"[Agent3] Generating final concept... with hats summary length: {len(hats_summary)}")
        prompt_integrate = AGENT3_INTEGRATE_CONCEPT.format(
            concept=concept, 
            hats_summary=hats_summary
        )
        
        final_concept = ba.gen_response(prompt_integrate)
        if not final_concept:
            return "無法生成最終構想，請稍後再試。"
        # 儲存最終構想 (Final Concept) 到本地檔案
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        filename_concept = f"agent3_final_concept.txt"
        try:
            with (OUTPUT_DIR / filename_concept).open("w", encoding="utf-8") as f:
                f.write(final_concept)
        except Exception as e:
            print(f"Error saving final concept: {e}")


        # 3. Step 2: 生成企畫書
        print("[Agent3] Writing final proposal...")
        prompt_proposal = AGENT3_WRITE_PROPOSAL.format(
            final_concept=final_concept
        )
        
        proposal_text = ba.gen_response(prompt_proposal)
        if not proposal_text:
            return "無法生成企畫書，請稍後再試。"

        # 儲存結果 (Optional)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"agent3_final_proposal.md"
        try:
            with (OUTPUT_DIR / filename).open("w", encoding="utf-8") as f:
                f.write(proposal_text)
        except Exception as e:
            print(f"Error saving proposal: {e}")

        return final_concept,proposal_text

