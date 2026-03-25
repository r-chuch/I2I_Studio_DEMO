# app/graph/state.py
# LangGraph 共享狀態定義，取代舊的 user_session_{uuid}.json 檔案

from typing import TypedDict, Optional


class WorkflowState(TypedDict, total=False):
    # ── 影片資訊 ──────────────────────────────────────
    video_url:    str
    video_id:     str
    transcript:   str
    video_title:  str
    summary:      str

    # ── Stage 2：Three Whys ───────────────────────────
    pain_points:  list          # Agent1 擷取的痛點清單
    whys:         list          # Agent1 生成的三層 Why 問題（對應舊 workflow_data['whys']）
    why_answers:  list          # [interrupt] 使用者填答的三個 Why 答案

    # ── Stage 3：痛點 + SCAMPER ───────────────────────
    pain_point:              str    # Agent2 整合後的痛點描述
    solutions:               list   # Agent2 生成的解方清單 [{id, name, desc}]
    selected_solution_id:    str    # [interrupt] 使用者選擇的解方 id
    selected_solution_name:  str    # [interrupt] 使用者選擇的解方名稱
    scamper_questions:       dict   # Agent2 生成的 SCAMPER 問題 {S/C/A/M/P/E/R: {question, suggestion}}
    random_words:            list   # Agent2 生成的強迫聯想詞彙清單
    scamper_answers:         dict   # [interrupt] 使用者填寫的 SCAMPER 答案
    user_prelim_concept:     str    # [interrupt] 使用者撰寫的初步概念

    # ── Stage 3/4 橋接：精煉概念 ─────────────────────
    refined_concept:  str       # Agent3 六帽分析前的概念整合

    # ── Stage 4：六頂思考帽 ───────────────────────────
    six_hats_suggestions: list  # Agent3 為每頂帽子生成的建議 [{id, name, q, suggestion}]
    hat_inputs:           dict  # [interrupt] 使用者填寫的六帽回饋 {hat_white_hat, hat_red_hat, ...}

    # ── Stage 5：最終企劃書 ───────────────────────────
    final_concept_text: str     # Agent3 整合後的最終概念文字
    final_proposal:     str     # Agent3 生成的一頁式 Markdown 企劃書

    # ── 品質控制（Critic Agent）────────────────────────
    critic_score:    float      # Critic 評分 0-10
    critic_feedback: str        # Critic 改善回饋文字
    retry_count:     int        # 重試次數（最多 3 次）

    # ── UI 導覽狀態 ───────────────────────────────────
    current_stage: int          # 目前顯示的階段（1-5）
    max_stage:     int          # 使用者已解鎖的最高階段
