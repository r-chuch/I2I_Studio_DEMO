# app/routes.py
# LangGraph 驅動的路由控制器
#
# 核心變化（對比舊版）：
#   舊：Cookie stage + user_session_{uuid}.json 手動讀寫
#   新：thread_id（Cookie）+ graph.invoke() / Command(resume=) + SqliteSaver 自動持久化
#
# 使用者表單提交流程：
#   /api/analyze_video    → graph.invoke({video_url: ...})          → runs until wait_why_answers
#   /api/confirm_painpoints → graph.invoke(Command(resume=answers))  → runs until wait_solution
#   /api/generate_scamper → graph.invoke(Command(resume={sol_id, sol_name})) → wait_scamper
#   /api/generate_concept → graph.invoke(Command(resume={scamper_answers, prelim_concept})) → wait_hat_inputs
#   /api/optimize_proposal → graph.invoke(Command(resume=hat_inputs)) → graph completes

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
import uuid

from langgraph.types import Command

from app.graph.workflow import get_workflow

main_bp = Blueprint('main', __name__)


# ════════════════════════════════════════════════
#  Session / State 工具函式
# ════════════════════════════════════════════════

def get_thread_config() -> dict:
    """
    取得（或建立）此使用者的 LangGraph thread config。
    thread_id 儲存在 Cookie，取代舊的 uid + JSON 檔案。
    """
    if 'thread_id' not in session:
        session['thread_id'] = str(uuid.uuid4())
        session.permanent = True
    return {"configurable": {"thread_id": session['thread_id']}}


def get_graph_state() -> dict:
    """從 LangGraph Checkpointer 讀取目前使用者的 State（取代 load_workflow_data）"""
    config = get_thread_config()
    workflow = get_workflow()
    try:
        state = workflow.get_state(config)
        return state.values if state and state.values else {}
    except Exception as e:
        print(f"[routes] get_graph_state 失敗：{e}")
        return {}


# ════════════════════════════════════════════════
#  主頁面路由
# ════════════════════════════════════════════════

@main_bp.route('/', methods=['GET'])
def index():
    get_thread_config()  # 確保 thread_id 存在

    workflow_data = get_graph_state()
    current_stage = workflow_data.get('current_stage', 1)
    max_stage     = workflow_data.get('max_stage', 1)

    # 支援 ?stage=N 導覽（只允許在已解鎖的範圍內跳轉）
    target_stage = request.args.get('stage', type=int)
    if target_stage:
        if 1 <= target_stage <= max_stage:
            current_stage = target_stage
        else:
            flash(f"請先完成當前步驟才能進入階段 {target_stage}。", "warning")
            return redirect(url_for('main.index', stage=max_stage))

    return render_template('index.html',
                           current_stage=current_stage,
                           max_stage=max_stage,
                           data=workflow_data)


# ════════════════════════════════════════════════
#  API 路由：各階段表單提交
# ════════════════════════════════════════════════

@main_bp.route('/api/analyze_video', methods=['POST'])
def analyze_video():
    """Stage 1 → 2：輸入 YouTube URL，啟動圖，跑到 wait_why_answers interrupt"""
    config   = get_thread_config()
    workflow = get_workflow()
    youtube_url = request.form.get('youtube_url', '')

    try:
        workflow.invoke(
            {
                "video_url":     youtube_url,
                "retry_count":   0,
                "current_stage": 1,
                "max_stage":     1,
            },
            config=config,
        )
        flash("字幕讀取成功，已生成 3 Whys 問題。", "success")
    except Exception as e:
        print(f"[analyze_video] 錯誤：{e}")
        flash("影片分析失敗，請確認連結是否正確或影片是否有字幕。", "error")

    return redirect(url_for('main.index'))


@main_bp.route('/api/confirm_painpoints', methods=['POST'])
def confirm_painpoints():
    """Stage 2 → 3：使用者提交 Why 答案，Resume 圖到 wait_solution interrupt"""
    config   = get_thread_config()
    workflow = get_workflow()

    answers = [
        request.form.get('q1_answer', ''),
        request.form.get('q2_answer', ''),
        request.form.get('q3_answer', ''),
    ]

    try:
        # Resume wait_why_answers_node：傳入使用者的三個答案
        workflow.invoke(Command(resume=answers), config=config)
        flash("痛點與建議解方已生成，請選擇一個解方以進行延伸發想。", "success")
    except Exception as e:
        print(f"[confirm_painpoints] 錯誤：{e}")
        flash("Agent 2 生成痛點時發生錯誤", "error")

    return redirect(url_for('main.index'))


@main_bp.route('/api/generate_scamper', methods=['POST'])
def generate_scamper():
    """Stage 3a → 3b：使用者選擇解方，Resume 圖到 wait_scamper interrupt"""
    config        = get_thread_config()
    workflow      = get_workflow()
    workflow_data = get_graph_state()

    selected_solution_id = request.form.get('selected_solution', '')

    # 從 State 中找出選定解方的名稱
    selected_solution_name = ""
    for sol in workflow_data.get('solutions', []):
        if sol['id'] == selected_solution_id:
            selected_solution_name = sol['name']
            break

    if not selected_solution_name:
        flash("請選擇一個解決方案", "warning")
        return redirect(url_for('main.index'))

    try:
        # Resume wait_solution_node：傳入選定解方的 id 與名稱
        workflow.invoke(
            Command(resume={
                "solution_id":   selected_solution_id,
                "solution_name": selected_solution_name,
            }),
            config=config,
        )
        flash("創意引導已生成！請進行 SCAMPER 發想。", "success")
    except Exception as e:
        print(f"[generate_scamper] 錯誤：{e}")
        flash("生成創意引導時發生錯誤", "error")

    return redirect(url_for('main.index'))


@main_bp.route('/api/generate_concept', methods=['POST'])
def generate_concept():
    """Stage 3b → 4：使用者提交 SCAMPER + 初步概念，Resume 圖到 wait_hat_inputs interrupt"""
    config   = get_thread_config()
    workflow = get_workflow()

    scamper_answers = {
        k: v for k, v in request.form.items() if k.startswith('scamper_')
    }
    user_prelim_concept = request.form.get('user_prelim_concept', '')

    try:
        # Resume wait_scamper_node：傳入 SCAMPER 答案與初步概念
        workflow.invoke(
            Command(resume={
                "scamper_answers": scamper_answers,
                "prelim_concept":  user_prelim_concept,
            }),
            config=config,
        )
        flash("初步概念已建立，Agent 3 已為您生成優化建議！", "success")
    except Exception as e:
        print(f"[generate_concept] 錯誤：{e}")
        flash("生成六頂思考帽建議時發生錯誤，請稍後再試。", "error")

    return redirect(url_for('main.index'))


@main_bp.route('/api/optimize_proposal', methods=['POST'])
def optimize_proposal():
    """Stage 4 → 5：使用者提交六帽回饋，Resume 圖到完成（critic evaluate）"""
    config   = get_thread_config()
    workflow = get_workflow()

    hats_data = {
        'hat_white_hat':  request.form.get('hat_white_hat', ''),
        'hat_red_hat':    request.form.get('hat_red_hat', ''),
        'hat_black_hat':  request.form.get('hat_black_hat', ''),
        'hat_yellow_hat': request.form.get('hat_yellow_hat', ''),
        'hat_green_hat':  request.form.get('hat_green_hat', ''),
        'hat_blue_hat':   request.form.get('hat_blue_hat', ''),
    }

    try:
        # Resume wait_hat_inputs_node：傳入六帽回饋，圖跑完 agent3_final + critic
        workflow.invoke(Command(resume=hats_data), config=config)
        flash("最終企劃書已生成！", "success")
    except Exception as e:
        print(f"[optimize_proposal] 錯誤：{e}")
        flash("生成最終企劃書時發生錯誤，請稍後再試。", "error")

    return redirect(url_for('main.index'))


@main_bp.route('/api/generate_ai_concept', methods=['POST'])
def generate_ai_concept():
    """
    AJAX 端點（非圖流程）：使用者點擊「AI 幫我優化」時即時呼叫 Agent2。
    直接讀取 graph state 中的 pain_point / selected_solution_name，
    不需要透過 graph.invoke 驅動。
    """
    workflow_data    = get_graph_state()
    pain_point       = workflow_data.get('pain_point', '')
    selected_solution = workflow_data.get('selected_solution_name', '')

    req_data     = request.get_json()
    scamper_ideas = req_data.get('scamper_ideas', {})
    random_word   = req_data.get('random_word', '')
    user_draft    = req_data.get('user_draft', '')

    from app.services.agents.agent2_creativity import Agent2Creativity
    ag2 = Agent2Creativity()
    try:
        refined_concept = ag2.gen_refined_concept(
            pain_point=pain_point,
            selected_solution=selected_solution,
            scamper_ideas=scamper_ideas,
            random_word=random_word,
            user_draft=user_draft,
        )
        return jsonify({'success': True, 'concept': refined_concept})
    except Exception as e:
        print(f"[generate_ai_concept] 錯誤：{e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@main_bp.route('/api/reset', methods=['POST', 'GET'])
def reset():
    """重置：清除 Cookie（產生新 thread_id），舊的 graph state 自然失效"""
    session.clear()
    return redirect(url_for('main.index'))
