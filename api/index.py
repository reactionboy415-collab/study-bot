from flask import Flask, request, jsonify
import cloudscraper
import uuid
import time

app = Flask(__name__)
scraper = cloudscraper.create_scraper()

def get_headers(anon_id):
    return {
        'User-Agent': "Mozilla/5.0 (Linux; Android 12)",
        'Origin': 'https://notegpt.io',
        'Referer': 'https://notegpt.io/explainer-video-maker',
        'Cookie': f'anonymous_user_id={anon_id}'
    }

@app.route('/fetch')
def fetch_logic():
    topic = request.args.get('topic')
    cid = request.args.get('cid') 
    aid = request.args.get('anon_id', str(uuid.uuid4()))
    headers = get_headers(aid)

    try:
        if cid:
            # Polling Live Steps from NoteGPT
            res = scraper.get(f"https://notegpt.io/api/v2/pdf-to-video/status?conversation_id={cid}", headers=headers).json()
            data = res.get("data", {})
            return jsonify({
                "status": data.get("status"),
                "video_url": data.get("cdn_video_url") or data.get("video_url"),
                "step": data.get("step") # Live process step
            })

        # Step 1: Start with Watermark False
        init = scraper.post("https://notegpt.io/api/v2/pdf-to-video", json={
            "source_url": "", "source_type": "text", "input_prompt": topic,
            "setting": {
                "frame_size": "16:9", "duration": 1, "lang": "en", 
                "gen_flow": "edit_script", "add_watermark": False # No Watermark
            }
        }, headers=headers).json()
        
        new_cid = init.get("data", {}).get("conversation_id")
        if not new_cid: return jsonify({"error": "Init Failed"}), 500

        time.sleep(6)
        script_res = scraper.get(f"https://notegpt.io/api/v2/pdf-to-video/script/get?conversation_id={new_cid}", headers=headers).json()
        script_data = script_res.get("data", {})
        
        # Step 2: Confirm Script
        scraper.post("https://notegpt.io/api/v2/pdf-to-video/script/edit", json={
            "conversation_id": new_cid, "script_data": str(script_data).replace("'", '"')
        }, headers=headers)

        return jsonify({
            "scenes": script_data.get("scenes", []),
            "cid": new_cid,
            "anon_id": aid
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
