from flask import Flask, request, jsonify
import cloudscraper
import uuid
import time

app = Flask(__name__)
# Cloudscraper Cloudflare bypass ke liye
scraper = cloudscraper.create_scraper()

@app.route('/')
def home():
    return "SnapStudy Scraper Engine is Running! 🚀"

@app.route('/fetch')
def fetch_data():
    topic = request.args.get('topic')
    if not topic:
        return jsonify({"error": "Bhai topic toh do!"}), 400

    # Ghost Identity Generation
    anon_id = uuid.uuid4().hex
    fake_ip = f"{uuid.uuid4().int % 256}.{uuid.uuid4().int % 256}.{uuid.uuid4().int % 256}.1"
    
    headers = {
        'User-Agent': "Mozilla/5.0 (Linux; Android 13; SM-S918B)",
        'Referer': 'https://notegpt.io/ai-animation-maker',
        'X-Forwarded-For': fake_ip,
        'Origin': 'https://notegpt.io'
    }
    
    cookies = {'anonymous_user_id': anon_id}

    try:
        # Step 1: Initiate NoteGPT
        payload = {
            "source_url": "",
            "source_type": "text",
            "input_prompt": topic,
            "setting": {"frame_size": "16:9", "duration": 1, "lang": "en", "gen_flow": "edit_script"}
        }
        
        init_res = scraper.post("https://notegpt.io/api/v2/pdf-to-video", 
                                json=payload, headers=headers, cookies=cookies, timeout=10)
        
        data = init_res.json()
        cid = data.get("data", {}).get("conversation_id")

        if not cid:
            return jsonify({"error": "Failed to get CID", "raw": data}), 500

        # Step 2: Polling Loop (Max 8 seconds limit for Vercel Free)
        start_time = time.time()
        while time.time() - start_time < 8:
            status_res = scraper.get(f"https://notegpt.io/api/v2/pdf-to-video/status?conversation_id={cid}", 
                                     headers=headers, cookies=cookies).json()
            
            step = status_res.get("data", {}).get("step")
            status = status_data = status_res.get("data", {}).get("status")

            if step in ["generating_voiceover", "completed"] or status == "pause":
                # Step 3: Fetch Final Scenes
                final_res = scraper.get(f"https://notegpt.io/api/v2/pdf-to-video/script/get?conversation_id={cid}", 
                                         headers=headers, cookies=cookies).json()
                return jsonify(final_res.get("data", {}).get("scenes", []))
            
            time.sleep(2)

        return jsonify({"status": "processing", "cid": cid}), 202

    except Exception as e:
        return jsonify({"error": str(e)}), 500
