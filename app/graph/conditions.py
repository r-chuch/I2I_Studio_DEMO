# app/graph/conditions.py
# LangGraph 條件邊路由函式

from .state import WorkflowState


def should_retry(state: WorkflowState) -> str:
    """
    Critic 評審後的路由：
    - 分數 < 7 且重試次數 < 3 → 重試 agent3_final_compute
    - 否則 → 結束
    """
    score = state.get("critic_score", 10.0)
    retries = state.get("retry_count", 0)

    if score < 7.0 and retries < 3:
        print(f"[Critic] 分數 {score:.1f} < 7，觸發第 {retries} 次重試...")
        return "retry"

    print(f"[Critic] 分數 {score:.1f}，品質達標，完成。")
    return "done"
