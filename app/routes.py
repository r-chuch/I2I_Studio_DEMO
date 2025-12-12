# routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from pathlib import Path
import json
import re
import uuid  # 新增: 用於生成唯一的 Session ID

# 引入 Agent 類別
from app.services.agents.agent1_insight import Agent1Insight
from app.services.agents.agent2_creativity import Agent2Creativity
from app.services.agents.agent3_optimize import Agent3Optimize 
from app.services.youtube_service import get_video_transcript

# 定義藍圖名稱為 'main'
main_bp = Blueprint('main', __name__)

OUTPUT_DIR = Path.cwd() / "app" / "output_data"

# --- [Session 資料管理工具 - 解決 Cookie 過大問題] ---

def get_session_id():
    """取得或建立目前使用者的 Session ID"""
    if 'uid' not in session:
        session['uid'] = str(uuid.uuid4())
        session.permanent = True # 讓 session 保持較長時間
    return session['uid']

def get_session_file_path():
    """取得對應目前 Session 的資料檔案路徑"""
    uid = get_session_id()
    # 確保目錄存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR / f"user_session_{uid}.json"

def load_workflow_data():
    """從伺服器檔案讀取大型資料"""
    file_path = get_session_file_path()
    if file_path.exists():
        try:
            with file_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading session file: {e}")
            return {}
    return {}

def save_workflow_data(data):
    """將大型資料寫入伺服器檔案"""
    file_path = get_session_file_path()
    try:
        with file_path.open('w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving session file: {e}")

# --- [工具函式] ---

def get_video_id(url):
    if not url: return None
    match = re.search(r"v=([^&]+)", url)
    if match: return match.group(1)
    match = re.search(r"youtu\.be/([^?]+)", url)
    if match: return match.group(1)
    return None

def ai_generate_stage2_whys(video_id):
    ag1 = Agent1Insight()
    ag1.text_gen(video_id)
    try:
        # 注意: agent1 輸出若為共用檔名可能會被覆蓋，建議未來也改為動態檔名
        file_path = OUTPUT_DIR / "agent1_output.json"
        if not file_path.exists():
             return {}
        with file_path.open('r', encoding='utf-8') as f:
            agent1_output = json.load(f)
    except Exception as e:
        print("讀取agent1_output時發生例外：", type(e).__name__, e)
        return {}
    return agent1_output

# --- [主頁面路由] ---

@main_bp.route('/', methods=['GET'])
def index():
    # 確保有 Session ID
    get_session_id()
    
    # 從檔案載入資料，而非從 Cookie
    workflow_data = load_workflow_data()

    # 初始化邏輯：如果沒有資料，則視為新的一局
    if not workflow_data:
        workflow_data = {}
        save_workflow_data(workflow_data)
        # Session cookie 只存輕量的狀態控制
        session['stage'] = 1
        session['max_stage'] = 1

    target_stage = request.args.get('stage', type=int)
    max_reached = session.get('max_stage', 1)

    if target_stage:
        if 1 <= target_stage <= max_reached:
            session['stage'] = target_stage
        else:
            flash(f"請先完成當前步驟才能進入階段 {target_stage}。", "warning")
            return redirect(url_for('main.index', stage=max_reached))
    
    current_stage = session.get('stage', 1)

    return render_template('index.html', 
                           current_stage=current_stage, 
                           max_stage=max_reached,
                           data=workflow_data)

# --- [API 路由] ---

@main_bp.route('/api/analyze_video', methods=['POST'])
def analyze_video():
    workflow_data = load_workflow_data()
    youtube_url = request.form.get('youtube_url')
    
    video_id, transcript_text = get_video_transcript(youtube_url)
    
    if not video_id:
        video_id = "mock_video_id"
    
    if video_id:
        workflow_data['video_url'] = youtube_url
        workflow_data['video_id'] = video_id
        
        # 呼叫 Agent 1
        ai_result = ai_generate_stage2_whys(video_id)
        
        if ai_result:
            workflow_data['whys'] = ai_result.get('three_whys', [])
            workflow_data['video_title'] = ai_result.get('video_title', 'Unknown Title')
            workflow_data['summary'] = ai_result.get('summary', '')
        
        # 儲存回檔案
        save_workflow_data(workflow_data)
        
        # 更新 Cookie 中的狀態
        session['max_stage'] = max(session.get('max_stage', 1), 2)
        session['stage'] = 2
        flash("字幕讀取成功，已生成 3 Whys 問題。", "success")
    else:
        flash("無效的 YouTube 連結或無字幕。", "error")
        return redirect(url_for('main.index')) 

    return redirect(url_for('main.index'))

@main_bp.route('/api/confirm_painpoints', methods=['POST'])
def confirm_painpoints():
    workflow_data = load_workflow_data()
    
    answers = [
        request.form.get('q1_answer', ''),
        request.form.get('q2_answer', ''),
        request.form.get('q3_answer', '')
    ]
    workflow_data['why_answers'] = answers
    whys_list = workflow_data.get('whys', [])
    
    ag2 = Agent2Creativity()
    try:
        # Agent 2 第一階段：生成痛點與解方
        _, file_path = ag2.gen_pain_point(whys_list, answers)
        
        if file_path and file_path.exists():
            with file_path.open('r', encoding='utf-8') as f:
                pain_point_data = json.load(f)
                
            workflow_data['pain_point'] = pain_point_data.get('pain_point', '無法生成痛點')
            
            solutions_raw = pain_point_data.get('solutions', [])
            solutions_formatted = []
            for idx, sol in enumerate(solutions_raw):
                solutions_formatted.append({
                    "id": f"sol{idx+1}",
                    "name": sol,
                    "desc": "" 
                })
            workflow_data['solutions'] = solutions_formatted
            
            # 清除舊的 Stage 3 資料
            workflow_data.pop('scamper_questions', None)
            workflow_data.pop('random_words', None)
            workflow_data.pop('selected_solution_id', None)
            workflow_data.pop('selected_solution_name', None)
            
    except Exception as e:
        print(f"Agent 2 Pain Point Error: {e}")
        flash("Agent 2 生成痛點時發生錯誤", "error")
        return redirect(url_for('main.index'))

    save_workflow_data(workflow_data)
    session['max_stage'] = max(session.get('max_stage', 1), 3)
    session['stage'] = 3
    flash("痛點與建議解方已生成，請選擇一個解方以進行延伸發想。", "success")
    
    return redirect(url_for('main.index'))

@main_bp.route('/api/generate_scamper', methods=['POST'])
def generate_scamper():
    workflow_data = load_workflow_data()
    
    selected_solution_id = request.form.get('selected_solution')
    workflow_data['selected_solution_id'] = selected_solution_id
    
    selected_solution_name = ""
    for sol in workflow_data.get('solutions', []):
        if sol['id'] == selected_solution_id:
            selected_solution_name = sol['name']
            break
    
    if not selected_solution_name:
        flash("請選擇一個解決方案", "warning")
        return redirect(url_for('main.index'))

    workflow_data['selected_solution_name'] = selected_solution_name
    pain_point = workflow_data.get('pain_point', '')

    ag2 = Agent2Creativity()
    try:
        # Agent 2 第二階段：生成 SCAMPER
        scamper_data, _ = ag2.gen_scamper_prompts(pain_point, selected_solution_name)
        
        if scamper_data:
            workflow_data['scamper_questions'] = scamper_data.get('scamper_questions', {})
            workflow_data['random_words'] = scamper_data.get('random_words', [])
            
    except Exception as e:
        print(f"Agent 2 SCAMPER Error: {e}")
        flash("生成創意引導時發生錯誤", "error")
        return redirect(url_for('main.index'))

    save_workflow_data(workflow_data)
    session['stage'] = 3
    flash("創意引導已生成！請進行 SCAMPER 發想。", "success")
    
    return redirect(url_for('main.index'))

@main_bp.route('/api/generate_concept', methods=['POST'])
def generate_concept():
    workflow_data = load_workflow_data()
    
    # 1. 儲存 SCAMPER 答案
    scamper_answers = {}
    for key in request.form:
        if key.startswith('scamper_'):
            scamper_answers[key] = request.form[key]
    workflow_data['scamper_answers'] = scamper_answers
    
    # 2. 儲存初步概念
    user_prelim_concept = request.form.get('user_prelim_concept')
    workflow_data['user_prelim_concept'] = user_prelim_concept
    
    # 3. 呼叫 Agent 3 生成六頂思考帽分析
    ag3 = Agent3Optimize()
    try:
        res, fp = ag3.gen_six_hats(user_prelim_concept)
        
        if res:
            workflow_data['refined_concept'] = res.get('concept', user_prelim_concept)
            workflow_data['six_hats_suggestions'] = res.get('hats', [])
        else:
            flash("Agent 3 生成回應為空，使用原始概念。", "warning")

    except Exception as e:
        print(f"Agent 3 Error: {e}")
        flash("生成六頂思考帽建議時發生錯誤，請稍後再試。", "error")
        workflow_data['refined_concept'] = user_prelim_concept
        workflow_data['six_hats_suggestions'] = []
    
    save_workflow_data(workflow_data)
    session['max_stage'] = max(session.get('max_stage', 1), 4)
    session['stage'] = 4
    flash("初步概念已建立，Agent 3 已為您生成優化建議！", "success")
    
    return redirect(url_for('main.index'))

@main_bp.route('/api/optimize_proposal', methods=['POST'])
def optimize_proposal():
    workflow_data = load_workflow_data()
    
    # 收集使用者在六頂思考帽階段填寫的內容
    hats_data = {
        'hat_white_hat': request.form.get('hat_white_hat'),
        'hat_red_hat': request.form.get('hat_red_hat'),
        'hat_black_hat': request.form.get('hat_black_hat'),
        'hat_yellow_hat': request.form.get('hat_yellow_hat'),
        'hat_green_hat': request.form.get('hat_green_hat'),
        'hat_blue_hat': request.form.get('hat_blue_hat'),
    }
    workflow_data['hat_inputs'] = hats_data
    
    # 取得要優化的概念（優先使用 Stage 4 AI 優化過的，若無則用最初的）
    concept = workflow_data.get('refined_concept', workflow_data.get('user_prelim_concept', ''))
    
    # 呼叫 Agent 3 生成最終企劃書 (回傳 tuple: final_concept, final_proposal)
    ag3 = Agent3Optimize()
    try:
        # 注意這裡接收兩個回傳值
        final_concept_text, final_proposal_md = ag3.gen_final_proposal(concept, hats_data)
        
        # 分開儲存
        workflow_data['final_concept_text'] = final_concept_text
        workflow_data['final_proposal'] = final_proposal_md
        
    except Exception as e:
        print(f"Agent 3 Final Proposal Error: {e}")
        flash("生成最終企劃書時發生錯誤，請稍後再試。", "error")
        workflow_data['final_proposal'] = "生成失敗，請重試。"
        workflow_data['final_concept_text'] = concept # Fallback
    
    save_workflow_data(workflow_data)
    session['max_stage'] = max(session.get('max_stage', 1), 5)
    session['stage'] = 5
    flash("最終企劃書已生成！", "success")
    
    return redirect(url_for('main.index'))

@main_bp.route('/api/generate_ai_concept', methods=['POST'])
def generate_ai_concept():
    # 讀取檔案中的資料
    workflow_data = load_workflow_data()
    pain_point = workflow_data.get('pain_point', '')
    selected_solution = workflow_data.get('selected_solution_name', '')
    
    req_data = request.get_json()
    scamper_ideas = req_data.get('scamper_ideas', {}) 
    random_word = req_data.get('random_word', '')
    user_draft = req_data.get('user_draft', '')
    
    ag2 = Agent2Creativity()
    try:
        refined_concept = ag2.gen_refined_concept(
            pain_point=pain_point,
            selected_solution=selected_solution,
            scamper_ideas=scamper_ideas,
            random_word=random_word,
            user_draft=user_draft
        )
        return jsonify({'success': True, 'concept': refined_concept})
        
    except Exception as e:
        print(f"Agent 2 Concept Gen Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@main_bp.route('/api/reset', methods=['POST', 'GET'])
def reset():
    # 重置時刪除對應的 Session 檔案
    try:
        file_path = get_session_file_path()
        if file_path.exists():
            file_path.unlink() # 刪除檔案
    except Exception as e:
        print(f"Error deleting session file: {e}")

    session.clear()
    return redirect(url_for('main.index'))