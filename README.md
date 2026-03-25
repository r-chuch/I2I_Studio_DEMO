# I2I Studio (Insight-to-Idea)

> 建構於創造力理論的 AI 多代理議題洞察與創意激發平台

這是一個基於 Flask + **LangGraph** 開發的生成式 AI 應用程式，協助產品經理、行銷人員與創作者從 YouTube 影片中快速提煉洞察，並透過系統化的創新框架（Three Whys、SCAMPER、六頂思考帽）將痛點轉化為具體的商業企劃書。

---

## 專案特色

採用 **LangGraph StateGraph** 驅動的 Multi-Agent 協作流程，整合 Human-in-the-Loop 互動機制與 LLM-as-Judge 品質把關：

### Agent 1 — 深度洞察 (Insight)
- 自動抓取 YouTube 影片字幕
- 生成影片摘要與結構化重點
- 運用 **Three Whys（三個為什麼）** 挖掘痛點根本原因

### Agent 2 — 創意發散 (Creativity)
- 根據痛點推薦解決方案類型
- 引導使用者進行 **SCAMPER（奔馳法）** 創意改良
- 提供**強制關聯單詞（Random Words）** 激發跳躍性思考

### Agent 3 — 策略優化 (Optimize)
- 運用 **六頂思考帽（Six Thinking Hats）** 全方位檢視概念
- 整合所有分析數據，自動生成專業的**一頁式企劃書（One-Page Proposal）**

### Critic Agent — LLM-as-Judge 品質把關
- 自動評審企劃書的具體性、連貫性、說服力（0-10 分）
- 分數低於 7 分時透過 **LangGraph 條件邊**觸發重試（最多 3 次）

---

## 技術架構

| 層級 | 技術 |
|------|------|
| Backend | Flask 2.3 (Python 3.10+) |
| Agent 流程編排 | **LangGraph 1.1**（StateGraph + interrupt/resume） |
| Session 持久化 | **SQLite**（透過 `langgraph-checkpoint-sqlite`，取代手動 JSON 檔案） |
| LLM 介面 | **aisuite 0.1**（統一封裝，支援 Groq / OpenAI / Gemini 等） |
| 預設模型 | Groq `openai/gpt-oss-120b` |
| 字幕來源 | YouTube Transcript API |
| 部署 | Gunicorn（適用於 Render / Heroku 等 PaaS） |

---

## 五階段工作流程

```
[YouTube URL 輸入]
       │
       ▼
 extract_transcript  ← 擷取 YouTube 字幕
       │
       ▼
  agent1_compute     ← Agent1：Three Whys 分析
       │
   [INTERRUPT]       ← 使用者：填寫三層 Why 答案
       │
       ▼
 agent2_pain_compute ← Agent2：生成痛點 + 三個解方
       │
   [INTERRUPT]       ← 使用者：選擇解方
       │
       ▼
agent2_scamper_compute ← Agent2：生成 SCAMPER 問題
       │
   [INTERRUPT]       ← 使用者：填寫 SCAMPER + 初步概念
       │
       ▼
agent3_sixhats_compute ← Agent3：六頂思考帽分析
       │
   [INTERRUPT]       ← 使用者：填寫六帽回饋
       │
       ▼
agent3_final_compute ← Agent3：生成最終企劃書
       │
       ▼
  critic_evaluate    ← Critic：LLM-as-Judge 品質評審
       │
       ├── score < 7 且 retry < 3 ──→ agent3_final_compute（重試）
       │
       └── 品質達標 ──────────────→ END
```

---

## 系統需求

- Python 3.10+
- LLM Provider API Key（預設使用 Groq；亦支援 OpenAI、Gemini）

---

## 安裝與設定

### 1. 取得專案程式碼

```bash
git clone <repository_url>
cd final_project
```

### 2. 建立虛擬環境

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. 安裝依賴套件

```bash
pip install -r requirements.txt
pip install langgraph>=1.0.0 langgraph-checkpoint-sqlite>=1.0.0
```

### 4. 設定環境變數

在專案根目錄建立 `.env` 檔案：

```ini
# Flask
SECRET_KEY=your_secret_key_here

# LLM API Keys（依使用的 provider 填寫）
GROQ_API_KEY=your_groq_api_key

# 選用（切換其他 provider 時填寫）
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_google_api_key
```

### 5. 啟動應用程式

**開發模式：**

```bash
python run.py
```

瀏覽器開啟：`http://localhost:5000`

**生產環境：**

```bash
gunicorn run:app
```

---

## 專案結構

```
final_project/
├── app/
│   ├── graph/                        # LangGraph 圖定義（新架構核心）
│   │   ├── __init__.py
│   │   ├── state.py                  # WorkflowState TypedDict（共享狀態）
│   │   ├── workflow.py               # StateGraph 編譯 + SqliteSaver
│   │   ├── nodes.py                  # 所有 Compute / Wait 節點函式
│   │   └── conditions.py             # 條件邊路由（should_retry）
│   ├── services/
│   │   ├── agents/
│   │   │   ├── base_agent.py         # aisuite LLM 介面封裝
│   │   │   ├── agent1_insight.py     # Agent1：Three Whys 洞察分析
│   │   │   ├── agent2_creativity.py  # Agent2：SCAMPER 創意發散
│   │   │   ├── agent3_optimize.py    # Agent3：六帽分析 + 企劃書生成
│   │   │   └── agent_critic.py       # Critic Agent：LLM-as-Judge 評審
│   │   ├── prompt_templates.py       # 所有 Agent 提示詞集中管理
│   │   └── youtube_service.py        # YouTube 字幕抓取服務
│   ├── templates/                    # 前端 HTML 模板（Jinja2）
│   ├── output_data/
│   │   └── sessions.db               # SQLite Session 持久化（自動生成）
│   └── routes.py                     # Flask 路由（LangGraph 驅動）
├── run.py                            # 程式進入點
├── requirements.txt
└── .env                              # 環境變數（需自行建立）
```

---

## API 路由說明

| 路由 | 方法 | 說明 |
|------|------|------|
| `/` | GET | 主頁面，讀取目前 Graph State 渲染對應階段 |
| `/api/analyze_video` | POST | Stage 1→2：啟動圖，擷取字幕並分析 |
| `/api/confirm_painpoints` | POST | Stage 2→3：提交 Why 答案，生成痛點與解方 |
| `/api/generate_scamper` | POST | Stage 3a→3b：選定解方，生成 SCAMPER 問題 |
| `/api/generate_concept` | POST | Stage 3b→4：提交 SCAMPER，生成六帽建議 |
| `/api/optimize_proposal` | POST | Stage 4→5：提交六帽回饋，生成最終企劃書 |
| `/api/generate_ai_concept` | POST | AJAX：即時 AI 優化概念（不經過圖流程） |
| `/api/reset` | POST/GET | 重置 Session，開始新的流程 |

---

## 注意事項

- **Session 管理：** 使用 LangGraph `SqliteSaver` 將每位使用者的狀態儲存於 `app/output_data/sessions.db`，以 Cookie 中的 `thread_id` 識別。在雲端部署時若磁碟不持久（如 Render 免費版），重啟後 Session 會遺失。
- **LLM 模型切換：** 可在 [app/services/agents/base_agent.py](app/services/agents/base_agent.py) 中修改 `provider` 與 `model` 參數切換使用的模型。
- **提示詞管理：** 所有 Agent 提示詞集中在 [app/services/prompt_templates.py](app/services/prompt_templates.py)，方便統一調整。

---

## License

[MIT License](LICENSE)
