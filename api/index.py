from flask import Flask, request, jsonify
import cloudscraper
import uuid
import time

app = Flask(__name__)
scraper = cloudscraper.create_scraper()

BASE = "https://notegpt.io"

def ghost_headers():
    fake_ip = ".".join(str(uuid.uuid4().int % 255) for _ in range(4))
    return {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13)",
        "Origin": "https://notegpt.io",
        "Referer": "https://notegpt.io/explainer-video-maker",
        "X-Forwarded-For": fake_ip,
        "Accept": "application/json"
    }

def ghost_cookies():
    return {
        "anonymous_user_id": uuid.uuid4().hex,
        "is_first_visit": "true"
    }

@app.route("/")
def home():
    return "SnapStudy Engine LIVE 🚀"

# ===============================
# STEP 1 — START JOB (FAST)
# ===============================
@app.route("/fetch")
def fetch():
    topic = request.args.get("topic")
    if not topic:
        return jsonify({"error": "Topic missing"}), 400

    headers = ghost_headers()
    cookies = ghost_cookies()

    try:
        payload = {
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

        r = scraper.post(
            f"{BASE}/api/v2/pdf-to-video",
            json=payload,
            headers=headers,
            cookies=cookies,
            timeout=30
        )

        data = r.json()
        cid = data.get("data", {}).get("conversation_id")
        if not cid:
            return jsonify({"error": "CID not received", "raw": data}), 500

        # fetch scenes (text + images)
        s = scraper.get(
            f"{BASE}/api/v2/pdf-to-video/script/get?conversation_id={cid}",
            headers=headers,
            cookies=cookies,
            timeout=30
        ).json()

        return jsonify({
            "conversation_id": cid,
            "scenes": s.get("data", {}).get("scenes", [])
        })

    except Exception as e:
        return jsonify({"error": "FETCH_FAILED", "details": str(e)}), 500


# ===============================
# STEP 2 — VIDEO STATUS (POLL)
# ===============================
@app.route("/video-status")
def video_status():
    cid = request.args.get("cid")
    if not cid:
        return jsonify({"error": "conversation_id missing"}), 400

    headers = ghost_headers()
    cookies = ghost_cookies()

    try:
        r = scraper.get(
            f"{BASE}/api/v2/pdf-to-video/status?conversation_id={cid}",
            headers=headers,
            cookies=cookies,
            timeout=30
        )
        data = r.json()

        if data.get("code") != 100000:
            return jsonify({"error": "NoteGPT error", "raw": data})

        d = data.get("data", {})
        if d.get("status") != "success":
            return jsonify({
                "status": d.get("status"),
                "step": d.get("step")
            })

        return jsonify({
            "status": "success",
            "video": {
                "title": d.get("title"),
                "video_url": d.get("video_url"),
                "cover": d.get("cover_url")
            }
        })

    except Exception as e:
        return jsonify({"error": "STATUS_FAILED", "details": str(e)}), 500
