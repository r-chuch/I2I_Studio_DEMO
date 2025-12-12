# app/services/prompt_templates.py




AGENT2_SCAMPER_FORCED = """
你是創意代理人，任務是根據下列痛點產生創意點子。
痛點（pain_point）：
\"\"\"{pain_point}\"\"\"

工具/流程：
1) 先依 SCAMPER（Substitute, Combine, Adapt, Modify, Put to another use, Eliminate, Reverse）每個角度產出 1-2 個具體點子。
2) 再執行 Forced Connection：系統會給一個隨機名詞（{random_noun}），請把該名詞與痛點做強制連結，產出至少 2 個跳脫性想法（說明其概念與可能風險/可行性）。
回傳格式（JSON）：
{
  "scamper": [
    {"angle":"Substitute","ideas":["...","..."]},
    {"angle":"Combine","ideas":["..."]},
    ...
  ],
  "forced_connections": [
    {"noun":"火山","ideas":["...","..."]},
    ...
  ]
}
"""

AGENT3_SIX_HATS = """
你是優化代理人（六頂思考帽）。請針對下列初步概念（idea_text）從六個帽子（白,紅,黑,黃,綠,藍）分別給出要點（每帽 2-3 點）。
初步概念：
\"\"\"{idea_text}\"\"\"

請回傳 JSON：
{
  "idea": "{idea_text}",
  "hats": {
    "white": ["事實1","事實2"],
    "red": ["感受1","直覺2"],
    "black": ["風險1","缺點2"],
    "yellow": ["優勢1","效益2"],
    "green": ["改良建議1","創意延伸2"],
    "blue": ["總結與下一步","執行建議"]
  }
}
"""
