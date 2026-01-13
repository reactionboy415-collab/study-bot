from flask import Flask, request, jsonify
import cloudscraper
import uuid
import time

app = Flask(__name__)
# Cloudscraper bypasses basic bot detection
scraper = cloudscraper.create_scraper()

@app.route('/fetch')
def fetch_all_data():
    topic = request.args.get('topic')
    if not topic:
        return jsonify({"error": "No topic provided"}), 400

    # Professional Configuration
    anon_id = str(uuid.uuid4())
    headers = {
        'User-Agent': "Mozilla/5.0 (Linux; Android 12; LAVA Blaze)",
        'Origin': 'https://notegpt.io',
        'Referer': 'https://notegpt.io/explainer-video-maker',
        'Accept': 'application/json'
    }
    cookies = {'anonymous_user_id': anon_id}

    try:
        # STEP 1: Initiate Script Generation
        init_payload = {
            "source_url": "",
            "source_type": "text",
            "input_prompt": topic,
            "setting": {
                "frame_size": "16:9",
                "duration": 1,
                "lang": "en",
                "gen_flow": "edit_script"
            }
        }
        
        init_res = scraper.post(
            "https://notegpt.io/api/v2/pdf-to-video", 
            json=init_payload, 
            headers=headers, 
            cookies=cookies
        ).json()
        
        cid = init_res.get("data", {}).get("conversation_id")
        if not cid:
            return jsonify({"error": "Failed to initiate engine"}), 500

        # STEP 2: Wait and Fetch the Script (The "Images & Text" part)
        # We retry a few times if the script isn't ready immediately
        script_data = None
        for _ in range(5):
            time.sleep(5)
            script_res = scraper.get(
                f"https://notegpt.io/api/v2/pdf-to-video/script/get?conversation_id={cid}", 
                headers=headers, 
                cookies=cookies
            ).json()
            
            if script_res.get("code") == 100000 and script_res.get("data"):
                script_data = script_res.get("data")
                break

        if not script_data:
            return jsonify({"status": "processing"}), 202

        # STEP 3: Confirm Script to Trigger Video Synthesis
        # This converts the "scenes" into the actual video queue
        scraper.post(
            "https://notegpt.io/api/v2/pdf-to-video/script/edit", 
            json={"conversation_id": cid, "script_data": str(script_data).replace("'", '"')}, 
            headers=headers, 
            cookies=cookies
        )

        # STEP 4: Final Polling for Video URL
        # The bot will continue to call this if we return 202
        status_res = scraper.get(
            f"https://notegpt.io/api/v2/pdf-to-video/status?conversation_id={cid}", 
            headers=headers, 
            cookies=cookies
        ).json()
        
        status_info = status_res.get("data", {})
        
        # Structure the final response for the Telegram Bot
        result = {
            "scenes": script_data.get("scenes", []),
            "video_url": status_info.get("cdn_video_url") or status_info.get("video_url"),
            "status": status_info.get("status", "processing")
        }

        # If video is ready, return 200, otherwise 202
        if result["video_url"]:
            return jsonify(result), 200
        else:
            # We still return the scenes so the bot can show images while video finishes
            return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
