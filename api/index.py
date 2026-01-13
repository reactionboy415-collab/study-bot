from flask import Flask, request, jsonify
import cloudscraper
import uuid
import time
import random
import json

app = Flask(__name__)

# Rotating User-Agents for different devices
USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.163 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def get_dynamic_session():
    return {
        "aid": uuid.uuid4().hex,
        "tid": f"G-{random.randint(100000000, 999999999)}",
        "ua": random.choice(USER_AGENTS)
    }

@app.route('/fetch')
def fetch_logic():
    topic = request.args.get('topic')
    cid = request.args.get('cid')
    
    # Session Management: Recover or Create
    aid = request.args.get('anon_id')
    tid = request.args.get('tid')
    ua = request.args.get('ua')

    if not aid or not tid:
        session = get_dynamic_session()
        aid, tid, ua = session['aid'], session['tid'], session['ua']

    scraper = cloudscraper.create_scraper()
    
    # Headers with Device Fingerprinting
    headers = {
        'User-Agent': ua,
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://notegpt.io/explainer-video-maker',
        'X-Requested-With': 'XMLHttpRequest',
        'Cookie': f'anonymous_user_id={aid}; _trackUserId={tid}; is_first_visit=true'
    }

    try:
        # Step: Status Polling
        if cid:
            res = scraper.get(f"https://notegpt.io/api/v2/pdf-to-video/status?conversation_id={cid}", headers=headers).json()
            data = res.get("data", {})
            return jsonify({
                "status": data.get("status"),
                "video_url": data.get("cdn_video_url") or data.get("video_url"),
                "step": data.get("step")
            })

        # Step 1: Unlimited Initiation
        init = scraper.post("https://notegpt.io/api/v2/pdf-to-video", json={
            "source_url": "", "source_type": "text", "input_prompt": topic,
            "setting": {
                "frame_size": "16:9", "duration": 1, "lang": "en", 
                "gen_flow": "edit_script", "add_watermark": False
            }
        }, headers=headers).json()

        new_cid = init.get("data", {}).get("conversation_id")
        if not new_cid: return jsonify({"error": "Bypass Failed", "resp": init}), 500

        # Wait for AI Brain
        time.sleep(8)
        script_res = scraper.get(f"https://notegpt.io/api/v2/pdf-to-video/script/get?conversation_id={new_cid}", headers=headers).json()
        script_data = script_res.get("data", {})

        # Step 2: Confirmation Trigger
        scraper.post("https://notegpt.io/api/v2/pdf-to-video/script/edit", json={
            "conversation_id": new_cid, "script_data": json.dumps(script_data)
        }, headers=headers)

        return jsonify({
            "scenes": script_data.get("scenes", []),
            "cid": new_cid, "anon_id": aid, "tid": tid, "ua": ua
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
