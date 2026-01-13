from flask import Flask, request, jsonify
import cloudscraper
import uuid
import time

app = Flask(__name__)
scraper = cloudscraper.create_scraper()

@app.route('/fetch')
def fetch_all():
    topic = request.args.get('topic')
    if not topic:
        return jsonify({"error": "No topic"}), 400

    anon_id = str(uuid.uuid4())
    headers = {
        'User-Agent': "Mozilla/5.0 (Linux; Android 12)",
        'Origin': 'https://notegpt.io',
        'Referer': 'https://notegpt.io/explainer-video-maker'
    }
    cookies = {'anonymous_user_id': anon_id}

    try:
        # Step 1: Start Script Generation
        init = scraper.post("https://notegpt.io/api/v2/pdf-to-video", json={
            "source_url": "", "source_type": "text", "input_prompt": topic,
            "setting": {"frame_size": "16:9", "duration": 1, "lang": "en", "gen_flow": "edit_script"}
        }, headers=headers, cookies=cookies).json()
        
        cid = init.get("data", {}).get("conversation_id")
        if not cid: return jsonify({"error": "Failed to start"}), 500

        # Step 2: Fetch Script/Scenes
        time.sleep(6)
        script_res = scraper.get(f"https://notegpt.io/api/v2/pdf-to-video/script/get?conversation_id={cid}", headers=headers, cookies=cookies).json()
        script_data = script_res.get("data", {})
        scenes = script_data.get("scenes", [])

        # Step 3: Trigger Video Synthesis (Confirm Script)
        scraper.post("https://notegpt.io/api/v2/pdf-to-video/script/edit", json={
            "conversation_id": cid, "script_data": str(script_data).replace("'", '"')
        }, headers=headers, cookies=cookies)

        # Step 4: Final Status Check
        status_res = scraper.get(f"https://notegpt.io/api/v2/pdf-to-video/status?conversation_id={cid}", headers=headers, cookies=cookies).json()
        video_info = status_res.get("data", {})

        return jsonify({
            "scenes": scenes,
            "video_url": video_info.get("cdn_video_url") or video_info.get("video_url"),
            "status": video_info.get("status"),
            "cid": cid
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
