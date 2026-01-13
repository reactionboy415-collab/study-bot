from flask import Flask, request, jsonify
import cloudscraper
import uuid
import time

app = Flask(__name__)
scraper = cloudscraper.create_scraper()

@app.route('/fetch')
def fetch_logic():
    topic = request.args.get('topic')
    if not topic:
        return jsonify({"error": "No topic provided"}), 400

    # Generate unique session data
    anon_id = uuid.uuid4().hex
    headers = {
        'User-Agent': "Mozilla/5.0 (Linux; Android 12; LAVA Blaze)",
        'Origin': 'https://notegpt.io',
        'Referer': 'https://notegpt.io/explainer-video-maker'
    }
    cookies = {'anonymous_user_id': anon_id}

    try:
        # Step 1: Initialize the request
        payload = {
            "source_url": "",
            "source_type": "text",
            "input_prompt": topic,
            "setting": {"frame_size": "16:9", "duration": 1, "lang": "en", "gen_flow": "edit_script"}
        }
        init_res = scraper.post("https://notegpt.io/api/v2/pdf-to-video", json=payload, headers=headers, cookies=cookies).json()
        cid = init_res.get("data", {}).get("conversation_id")
        
        if not cid:
            return jsonify({"error": "Failed to initialize engine"}), 500

        # Step 2: Retrieve and Auto-Confirm Script (Simulation of user clicking 'Next')
        time.sleep(6) # Wait for script generation
        script_res = scraper.get(f"https://notegpt.io/api/v2/pdf-to-video/script/get?conversation_id={cid}", headers=headers, cookies=cookies).json()
        script_data = script_res.get("data")

        # Confirm script to trigger video synthesis
        scraper.post("https://notegpt.io/api/v2/pdf-to-video/script/edit", json={
            "conversation_id": cid, 
            "script_data": str(script_data).replace("'", '"')
        }, headers=headers, cookies=cookies)

        # Step 3: Polling for Video Success
        for attempt in range(20): # Poll for 200 seconds max
            status_res = scraper.get(f"https://notegpt.io/api/v2/pdf-to-video/status?conversation_id={cid}", headers=headers, cookies=cookies).json()
            status_data = status_res.get("data", {})

            if status_data.get("status") == "success":
                return jsonify({
                    "title": status_data.get("title"),
                    "video_url": status_data.get("cdn_video_url"),
                    "transcript": [t['text'] for t in status_data.get("transcript_list", [])]
                })
            
            time.sleep(10)

        return jsonify({"status": "processing", "message": "Video is still generating"}), 202

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
