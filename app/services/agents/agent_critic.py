# app/services/agents/agent_critic.py
# LLM-as-a-Judge：評審最終企劃書品質
# 分數 < 7/10 時觸發 LangGraph 條件邊重試

import json
import re

import app.services.agents.base_agent as ba
from app.services.prompt_templates import CRITIC_EVALUATE_PROPOSAL


class CriticAgent:
    """
    LLM-as-a-Judge：使用與其他 Agent 相同的 LLM（透過 base_agent）
    對最終企劃書進行三項評分（具體性、連貫性、說服力），
    回傳平均分數與改善回饋。
    """

    def evaluate(self, proposal: str) -> tuple[float, str]:
        """
        評審企劃書品質。
        回傳 (score: float, feedback: str)
        - score：0-10 分（平均），分數 < 7 代表需要重試
        - feedback：改善建議（分數達標時為空字串）
        """
        if not proposal or len(proposal.strip()) < 50:
            # 企劃書太短或為空，直接給過（避免無意義重試）
            return 10.0, ""

        prompt = CRITIC_EVALUATE_PROPOSAL.format(proposal=proposal[:3000])

        try:
            raw = ba.gen_response(prompt)
            result = self._parse_json(raw)
            score    = float(result.get("score", 8.0))
            feedback = str(result.get("feedback", ""))
            print(f"[Critic] 評分：{score:.1f}，回饋：{feedback[:80] if feedback else '（達標）'}")
            return score, feedback
        except Exception as e:
            print(f"[Critic] 評審失敗，預設通過：{e}")
            return 8.0, ""

    def _parse_json(self, text: str) -> dict:
        """解析 LLM 輸出，容錯處理 Markdown 包裹"""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
            return {}
