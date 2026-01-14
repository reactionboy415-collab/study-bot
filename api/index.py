from flask import Flask, request, jsonify
import cloudscraper
import uuid
import time
import random

app = Flask(__name__)
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'android',
        'desktop': False
    }
)

# --- ADVANCED AGENT ROTATION SYSTEM ---
def get_advanced_headers(aid, tid):
    # Rotating through different modern mobile browsers
    user_agents = [
        f"Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(110, 120)}.0.0.0 Mobile Safari/537.36",
        f"Mozilla/5.0 (Linux; Android 12; Pixel 6 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(110, 120)}.0.0.0 Mobile Safari/537.36",
        f"Mozilla/5.0 (Linux; Android 13; KB2003) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(110, 120)}.0.0.0 Mobile Safari/537.36",
        f"Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
    ]
    
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Origin': 'https://notegpt.io',
        'Referer': 'https://notegpt.io/explainer-video-maker',
        'Sec-Ch-Ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
        'Sec-Ch-Ua-Mobile': '?1',
        'Sec-Ch-Ua-Platform': '"Android"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'X-Requested-With': 'XMLHttpRequest',
        'Cookie': f'anonymous_user_id={aid}; _trackUserId={tid}; is_first_visit=true; _ga=GA1.1.{random.randint(100000000, 999999999)}.{int(time.time())}'
    }

@app.route('/fetch')
def fetch_logic():
    topic = request.args.get('topic')
    cid = request.args.get('cid') 
    
    # Persistent IDs for the same conversation, fresh for new ones
    aid = request.args.get('anon_id', uuid.uuid4().hex)
    tid = request.args.get('tid', f"G-{random.randint(10000000, 99999999)}")
    
    headers = get_advanced_headers(aid, tid)

    try:
        if cid:
            # Step: Advanced Polling
            response = scraper.get(
                f"https://notegpt.io/api/v2/pdf-to-video/status?conversation_id={cid}", 
                headers=headers
            )
            
            # Handle potential Cloudflare or Login issues
            if response.status_code != 200:
                return jsonify({"status": "retrying", "code": response.status_code}), 202
                
            data = response.json().get("data", {})
            return jsonify({
                "status": data.get("status"),
                "video_url": data.get("cdn_video_url") or data.get("video_url"),
                "step": data.get("step")
            })

        # Step 1: Initiate with Anti-Fingerprint payload
        init_payload = {
            "source_url": "",
            "source_type": "text",
            "input_prompt": topic,
            "setting": {
                "frame_size": "16:9",
                "duration": 1,
                "lang": "en",
                "gen_flow": "edit_script",
                "add_watermark": False
            }
        }
        
        init_res = scraper.post(
            "https://notegpt.io/api/v2/pdf-to-video", 
            json=init_payload, 
            headers=headers
        ).json()
        
        new_cid = init_res.get("data", {}).get("conversation_id")
        if not new_cid:
            return jsonify({"error": "Init Failed", "details": init_res}), 500

        # Wait for AI Scripting
        time.sleep(9)
        
        script_res = scraper.get(
            f"https://notegpt.io/api/v2/pdf-to-video/script/get?conversation_id={new_cid}", 
            headers=headers
        ).json()
        
        script_data = script_res.get("data", {})
        
        # Step 2: Push to Video Synthesis
        # Convert script_data to clean JSON string to avoid formatting errors
        scraper.post(
            "https://notegpt.io/api/v2/pdf-to-video/script/edit", 
            json={
                "conversation_id": new_cid, 
                "script_data": str(script_data).replace("'", '"')
            }, 
            headers=headers
        )

        return jsonify({
            "scenes": script_data.get("scenes", []),
            "cid": new_cid,
            "anon_id": aid,
            "tid": tid
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
