from youtube_transcript_api import YouTubeTranscriptApi
import re
import textwrap
import os


def get_video_id(url):
    match = re.search(r"v=([^&]+)", url)
    return match.group(1) if match else None


def clean_text(text):
    """
    清理字幕：移除多餘空白與奇怪符號，使其適合 RAG 檢索
    """
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text



def save_to_file(video_id, raw_text):
    """
    儲存文字到本地 .txt
    """
    output_dir = Path.cwd() / "app" / "output_data"
    output_dir.mkdir(parents=True, exist_ok=True)  # 若不存在則建立
    out_path = output_dir / f"{video_id}_raw.txt"
    out_path.write_text(raw_text, encoding="utf-8")
    
    print(f"💾 已儲存：{out_path}")


def get_youtube_transcript(url):
    video_id = get_video_id(url)
    if not video_id:
        print("❌ 無法解析影片 ID")
        return None, None

    print(f"🔍 影片 ID：{video_id}")

    try:
        transcript = YouTubeTranscriptApi().fetch(video_id,languages=['zh-Hant','zh-TW', 'zh', 'zh-CN','en-US'])
        print("✅ 成功取得字幕！")

        # 新版 API 回傳 snippet 物件
        raw_text = "\n".join([snippet.text for snippet in transcript])

        

        return video_id, raw_text
    except Exception as e:
        print(f"❌ 無法取得字幕：{type(e).__name__} - {e}")
        return None, None


# -----------------------------
# 主程式執行
# -----------------------------

# url = "https://www.youtube.com/watch?v=RXwQ7_hlL3g"
# url = "https://www.youtube.com/watch?v=d7DrbH0czwk"


# video_id, raw_text = get_youtube_transcript(url)

# if raw_text:
#     print("\n===== 原始字幕（raw）=====")
#     print(raw_text)

#     # 儲存原始字幕
#     save_to_file(f"{video_id}_raw.txt", raw_text)



import re
from urllib.parse import urlparse, parse_qs
from pathlib import Path

def get_video_transcript(url: str) -> str | None:
    """
    url = "https://www.youtube.com/watch?v=d7DrbH0czwk"
    """
    if not url:
        return None
    video_id, raw_text = get_youtube_transcript(url)
    if raw_text:
        print("\n===== 原始字幕（raw）=====")
        print(raw_text)
        
        # 儲存原始字幕
        save_to_file(video_id, raw_text)
        return video_id, raw_text
    return None

# get_video_transcript("https://www.youtube.com/watch?v=d7DrbH0czwk")