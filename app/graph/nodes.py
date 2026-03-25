# app/graph/nodes.py
# LangGraph 節點函式
#
# 設計原則（Compute / Wait 分離）：
#   *_compute 節點 → 呼叫 LLM，回傳 dict 更新 State（無 interrupt）
#   wait_*    節點 → 呼叫 interrupt() 暫停，等使用者輸入後回傳 dict 更新 State
#
# 好處：interrupt() 呼叫前，State 已被 compute 節點更新，
#       前端 get_state() 能正確讀取 AI 輸出再渲染給使用者。

import json
from pathlib import Path
from langgraph.types import interrupt
from .state import WorkflowState

OUTPUT_DIR = Path.cwd() / "app" / "output_data"


# ════════════════════════════════════════════════
#  Stage 1：擷取字幕
# ════════════════════════════════════════════════

def extract_transcript_node(state: WorkflowState) -> dict:
    """擷取 YouTube 字幕，存入 State"""
    from app.services.youtube_service import get_video_transcript

    video_url = state.get("video_url", "")
    result = get_video_transcript(video_url)

    if not result:
        print("[extract_transcript] 無法取得字幕")
        return {"current_stage": 1, "max_stage": 1}

    video_id, transcript = result
    return {
        "video_id":     video_id,
        "transcript":   transcript,
        "current_stage": 1,
        "max_stage":    1,
    }


# ════════════════════════════════════════════════
#  Stage 2：Agent1 Three Whys 分析
# ════════════════════════════════════════════════

def agent1_compute_node(state: WorkflowState) -> dict:
    """Agent1：分析字幕，生成痛點與三層 Why 問題"""
    from app.services.agents.agent1_insight import Agent1Insight

    ag1 = Agent1Insight()
    result = ag1.process({"subtitle": state.get("transcript", "")})

    if not result.get("ok"):
        print(f"[agent1_compute] 失敗：{result.get('errors')}")
        return {"whys": [], "pain_points": [], "video_title": "", "summary": "",
                "current_stage": 2, "max_stage": 2}

    data = result["data"]
    return {
        "video_title":  data.get("video_title", ""),
        "summary":      data.get("summary", ""),
        "pain_points":  data.get("pain_points", []),
        "whys":         data.get("three_whys", []),  # 模板使用 'whys' 鍵
        "current_stage": 2,
        "max_stage":    2,
    }


def wait_why_answers_node(state: WorkflowState) -> dict:
    """[interrupt] 暫停，等待使用者回答三層 Why 問題"""
    # 前端已能從 state['whys'] 讀取問題來渲染
    why_answers = interrupt({"action": "fill_why_answers"})
    # why_answers = ["答案1", "答案2", "答案3"]
    return {"why_answers": why_answers}


# ════════════════════════════════════════════════
#  Stage 3a：Agent2 生成痛點與解方
# ════════════════════════════════════════════════

def agent2_pain_compute_node(state: WorkflowState) -> dict:
    """Agent2：整合 Why 答案，生成痛點描述與三個解方"""
    from app.services.agents.agent2_creativity import Agent2Creativity

    ag2 = Agent2Creativity()
    whys_list  = state.get("whys", [])
    why_answers = state.get("why_answers", [])

    response_text, file_path = ag2.gen_pain_point(whys_list, why_answers)

    pain_point_data = {}
    if file_path and Path(str(file_path)).exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                pain_point_data = json.load(f)
        except Exception as e:
            print(f"[agent2_pain_compute] 讀取輸出檔失敗：{e}")

    pain_point   = pain_point_data.get("pain_point", "")
    solutions_raw = pain_point_data.get("solutions", [])
    solutions    = [
        {"id": f"sol{i+1}", "name": sol, "desc": ""}
        for i, sol in enumerate(solutions_raw)
    ]

    return {
        "pain_point":    pain_point,
        "solutions":     solutions,
        "current_stage": 3,
        "max_stage":     3,
    }


def wait_solution_node(state: WorkflowState) -> dict:
    """[interrupt] 暫停，等待使用者從解方清單中選擇一個"""
    selected = interrupt({"action": "select_solution"})
    # selected = {"solution_id": "sol1", "solution_name": "解方名稱"}
    return {
        "selected_solution_id":   selected.get("solution_id", ""),
        "selected_solution_name": selected.get("solution_name", ""),
    }


# ════════════════════════════════════════════════
#  Stage 3b：Agent2 SCAMPER 生成
# ════════════════════════════════════════════════

def agent2_scamper_compute_node(state: WorkflowState) -> dict:
    """Agent2：依據選定解方，生成 SCAMPER 問題與強迫聯想詞"""
    from app.services.agents.agent2_creativity import Agent2Creativity

    ag2 = Agent2Creativity()
    pain_point        = state.get("pain_point", "")
    selected_solution = state.get("selected_solution_name", "")

    scamper_data, _ = ag2.gen_scamper_prompts(pain_point, selected_solution)

    return {
        "scamper_questions": scamper_data.get("scamper_questions", {}),
        "random_words":      scamper_data.get("random_words", []),
    }


def wait_scamper_node(state: WorkflowState) -> dict:
    """[interrupt] 暫停，等待使用者完成 SCAMPER 發想並撰寫初步概念"""
    user_input = interrupt({"action": "fill_scamper"})
    # user_input = {"scamper_answers": {...}, "prelim_concept": "..."}
    return {
        "scamper_answers":     user_input.get("scamper_answers", {}),
        "user_prelim_concept": user_input.get("prelim_concept", ""),
    }


# ════════════════════════════════════════════════
#  Stage 4：Agent3 六頂思考帽分析
# ════════════════════════════════════════════════

def agent3_sixhats_compute_node(state: WorkflowState) -> dict:
    """Agent3：對初步概念進行六頂思考帽分析"""
    from app.services.agents.agent3_optimize import Agent3Optimize

    ag3 = Agent3Optimize()
    concept = state.get("user_prelim_concept", "")

    result, _ = ag3.gen_six_hats(concept)

    if not result:
        return {
            "refined_concept":      concept,
            "six_hats_suggestions": [],
            "current_stage":        4,
            "max_stage":            4,
        }

    return {
        "refined_concept":      result.get("concept", concept),
        "six_hats_suggestions": result.get("hats", []),
        "current_stage":        4,
        "max_stage":            4,
    }


def wait_hat_inputs_node(state: WorkflowState) -> dict:
    """[interrupt] 暫停，等待使用者填寫六頂思考帽回饋"""
    hat_inputs = interrupt({"action": "fill_hat_inputs"})
    # hat_inputs = {"hat_white_hat": "...", "hat_red_hat": "...", ...}
    return {"hat_inputs": hat_inputs}


# ════════════════════════════════════════════════
#  Stage 5：Agent3 最終企劃書生成
# ════════════════════════════════════════════════

def agent3_final_compute_node(state: WorkflowState) -> dict:
    """Agent3：整合六帽回饋，生成最終一頁式企劃書"""
    from app.services.agents.agent3_optimize import Agent3Optimize

    ag3 = Agent3Optimize()
    concept    = state.get("refined_concept") or state.get("user_prelim_concept", "")
    hats_data  = state.get("hat_inputs", {})

    # 若是重試，將 Critic 回饋附加到概念中提升品質
    critic_feedback = state.get("critic_feedback", "")
    if critic_feedback and state.get("retry_count", 0) > 0:
        concept = f"{concept}\n\n【前次品質改善建議】{critic_feedback}"

    final_concept_text, final_proposal = ag3.gen_final_proposal(concept, hats_data)

    return {
        "final_concept_text": final_concept_text,
        "final_proposal":     final_proposal,
        "current_stage":      5,
        "max_stage":          5,
    }


# ════════════════════════════════════════════════
#  Critic：LLM-as-Judge 品質評審
# ════════════════════════════════════════════════

def critic_evaluate_node(state: WorkflowState) -> dict:
    """Critic Agent：評審企劃書品質，分數 < 7 時觸發重試"""
    from app.services.agents.agent_critic import CriticAgent

    critic = CriticAgent()
    score, feedback = critic.evaluate(state.get("final_proposal", ""))

    return {
        "critic_score":    score,
        "critic_feedback": feedback,
        "retry_count":     state.get("retry_count", 0) + 1,
    }
