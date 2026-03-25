# app/graph/workflow.py
# LangGraph StateGraph 定義與編譯（含 SqliteSaver 持久化）

import sqlite3
from pathlib import Path

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from .state import WorkflowState
from .nodes import (
    extract_transcript_node,
    agent1_compute_node,
    wait_why_answers_node,
    agent2_pain_compute_node,
    wait_solution_node,
    agent2_scamper_compute_node,
    wait_scamper_node,
    agent3_sixhats_compute_node,
    wait_hat_inputs_node,
    agent3_final_compute_node,
    critic_evaluate_node,
)
from .conditions import should_retry

# ── 全域單例 ──────────────────────────────────────
_workflow = None


def get_workflow():
    """
    取得已編譯的 LangGraph 工作流程（懶初始化單例）。
    使用 SqliteSaver 取代舊的 user_session_{uuid}.json 檔案。
    """
    global _workflow
    if _workflow is None:
        _workflow = _compile_workflow()
    return _workflow


def _compile_workflow():
    """建立並編譯 StateGraph"""
    # ── SQLite Checkpointer（取代手動 JSON Session 管理）──
    DB_PATH = Path.cwd() / "app" / "output_data" / "sessions.db"
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # check_same_thread=False：Flask 可能在不同執行緒存取同一連線
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    # ── 建立圖 ────────────────────────────────────
    builder = StateGraph(WorkflowState)

    # 加入所有節點
    builder.add_node("extract_transcript",      extract_transcript_node)
    builder.add_node("agent1_compute",          agent1_compute_node)
    builder.add_node("wait_why_answers",        wait_why_answers_node)
    builder.add_node("agent2_pain_compute",     agent2_pain_compute_node)
    builder.add_node("wait_solution",           wait_solution_node)
    builder.add_node("agent2_scamper_compute",  agent2_scamper_compute_node)
    builder.add_node("wait_scamper",            wait_scamper_node)
    builder.add_node("agent3_sixhats_compute",  agent3_sixhats_compute_node)
    builder.add_node("wait_hat_inputs",         wait_hat_inputs_node)
    builder.add_node("agent3_final_compute",    agent3_final_compute_node)
    builder.add_node("critic_evaluate",         critic_evaluate_node)

    # 定義固定邊（線性流程）
    builder.add_edge(START,                     "extract_transcript")
    builder.add_edge("extract_transcript",      "agent1_compute")
    builder.add_edge("agent1_compute",          "wait_why_answers")
    builder.add_edge("wait_why_answers",        "agent2_pain_compute")
    builder.add_edge("agent2_pain_compute",     "wait_solution")
    builder.add_edge("wait_solution",           "agent2_scamper_compute")
    builder.add_edge("agent2_scamper_compute",  "wait_scamper")
    builder.add_edge("wait_scamper",            "agent3_sixhats_compute")
    builder.add_edge("agent3_sixhats_compute",  "wait_hat_inputs")
    builder.add_edge("wait_hat_inputs",         "agent3_final_compute")
    builder.add_edge("agent3_final_compute",    "critic_evaluate")

    # 條件邊：Critic 評審後決定重試或完成
    builder.add_conditional_edges(
        "critic_evaluate",
        should_retry,
        {"retry": "agent3_final_compute", "done": END}
    )

    return builder.compile(checkpointer=checkpointer)
