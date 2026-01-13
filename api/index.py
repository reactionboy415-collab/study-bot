from flask import Flask, request, jsonify
import cloudscraper
import uuid
import time

app = Flask(__name__)
scraper = cloudscraper.create_scraper()

@app.route('/')
def home():
    return "SnapStudy Scraper Engine is Running! 🚀"

@app.route('/fetch')
def fetch_data():
    topic = request.args.get('topic')
    if not topic:
        return jsonify({"error": "Topic required"}), 400

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

    # STEP 1: INIT PDF → VIDEO
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
        return jsonify({"error": "CID not generated"}), 500

    # STEP 2: POLL STATUS (SHORT – VERCEL SAFE)
    start = time.time()
    scenes = None

    while time.time() - start < 8:
        s = scraper.get(
            f"https://notegpt.io/api/v2/pdf-to-video/status?conversation_id={cid}",
            headers=headers,
            cookies=cookies,
            timeout=10
        ).json()

        data = s.get("data", {})
        if data.get("step") in ["generating_voiceover", "completed"]:
            script = scraper.get(
                f"https://notegpt.io/api/v2/pdf-to-video/script/get?conversation_id={cid}",
                headers=headers,
                cookies=cookies,
                timeout=10
            ).json()
            scenes = script.get("data", {}).get("scenes", [])
            break

        time.sleep(2)

    # RETURN SCENES + CID (IMPORTANT)
    return jsonify({
        "conversation_id": cid,
        "scenes": scenes or [],
        "status": "processing"
    })

@app.route("/video-status")
def video_status():
    cid = request.args.get("cid")
    if not cid:
        return jsonify({"error": "cid required"}), 400

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13)",
        "Referer": "https://notegpt.io/explainer-video-maker"
    }

    s = scraper.get(
        f"https://notegpt.io/api/v2/pdf-to-video/status?conversation_id={cid}",
        headers=headers,
        timeout=15
    ).json()

    data = s.get("data", {})

    if data.get("status") == "success":
        return jsonify({
            "status": "success",
            "video": data.get("cdn_video_url") or data.get("video_url"),
            "cover": data.get("cdn_cover_url"),
            "title": data.get("title")
        })

    return jsonify({
        "status": data.get("status"),
        "step": data.get("step")
    })
