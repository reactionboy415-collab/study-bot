from flask import Flask, request, jsonify
import cloudscraper
import uuid
import time
import json

app = Flask(__name__)
scraper = cloudscraper.create_scraper()

# =========================
# HOME
# =========================
@app.route("/")
def home():
    return "SnapStudy Engine with Video is LIVE 🚀"

# =========================
# MAIN FETCH API
# =========================
@app.route("/fetch")
def fetch():
    topic = request.args.get("topic")
    if not topic:
        return jsonify({"error": "Topic missing"}), 400

    anon_id = uuid.uuid4().hex
    fake_ip = f"{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}.1"

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13)",
        "Origin": "https://notegpt.io",
        "Referer": "https://notegpt.io/explainer-video-maker",
        "X-Forwarded-For": fake_ip
    }

    cookies = {
        "anonymous_user_id": anon_id,
        "is_first_visit": "true"
    }

    try:
        # =========================
        # STEP 1: INIT
        # =========================
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

        init = scraper.post(
            "https://notegpt.io/api/v2/pdf-to-video",
            json=init_payload,
            headers=headers,
            cookies=cookies,
            timeout=15
        ).json()

        cid = init.get("data", {}).get("conversation_id")
        if not cid:
            return jsonify({"error": "CID not generated", "raw": init}), 500

        # =========================
        # STEP 2: WAIT FOR SCRIPT
        # =========================
        for _ in range(12):
            status = scraper.get(
                f"https://notegpt.io/api/v2/pdf-to-video/status?conversation_id={cid}",
                headers=headers,
                cookies=cookies,
                timeout=10
            ).json()

            step = status.get("data", {}).get("step")
            if step in ["generating_voiceover", "generating_visuals", "completed"]:
                break
            time.sleep(2)

        # =========================
        # STEP 3: GET SCENES (TEXT + IMAGES)
        # =========================
        script = scraper.get(
            f"https://notegpt.io/api/v2/pdf-to-video/script/get?conversation_id={cid}",
            headers=headers,
            cookies=cookies,
            timeout=15
        ).json()

        scenes = script.get("data", {}).get("scenes")
        if not scenes:
            return jsonify({"error": "Scenes not found", "raw": script}), 500

        # =========================
        # STEP 4: EDIT SCRIPT (REQUIRED)
        # =========================
        edit_payload = {
            "conversation_id": cid,
            "script_data": json.dumps(script.get("data"))
        }

        edit = scraper.post(
            "https://notegpt.io/api/v2/pdf-to-video/script/edit",
            json=edit_payload,
            headers=headers,
            cookies=cookies,
            timeout=20
        ).json()

        if edit.get("code") != 100000:
            return jsonify({"error": "Script edit failed", "raw": edit}), 500

        # =========================
        # STEP 5: POLL VIDEO
        # =========================
        video_data = None
        for _ in range(60):  # ~5 minutes
            check = scraper.get(
                f"https://notegpt.io/api/v2/pdf-to-video/status?conversation_id={cid}",
                headers=headers,
                cookies=cookies,
                timeout=15
            ).json()

            data = check.get("data", {})
            if data.get("status") == "success":
                video_data = data
                break

            time.sleep(5)

        if not video_data:
            return jsonify({
                "error": "Video generation timeout",
                "conversation_id": cid
            }), 504

        # =========================
        # FINAL RESPONSE
        # =========================
        return jsonify({
            "conversation_id": cid,
            "scenes": scenes,              # ✅ TEXT + IMAGES FIRST
            "video": {
                "title": video_data.get("title"),
                "video_url": video_data.get("video_url"),  # ✅ DIRECT MP4
                "cover": video_data.get("cover_url")
            }
        })

    except Exception as e:
        return jsonify({
            "error": "Internal Exception",
            "message": str(e)
        }), 500
