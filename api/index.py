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

# =====================================
# STEP 1 — FETCH SCENES (FAST, SAFE)
# =====================================
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
                "gen_flow": "edit_script",
                "watermark": False   # ✅ NO WATERMARK
            }
        }

        init = scraper.post(
            f"{BASE}/api/v2/pdf-to-video",
            json=payload,
            headers=headers,
            cookies=cookies,
            timeout=30
        ).json()

        data = init.get("data")
        if not data or "conversation_id" not in data:
            return jsonify({
                "error": "INIT_FAILED",
                "raw": init
            }), 500

        cid = data["conversation_id"]

        # ---- Fetch scenes safely
        scene_res = scraper.get(
            f"{BASE}/api/v2/pdf-to-video/script/get?conversation_id={cid}",
            headers=headers,
            cookies=cookies,
            timeout=30
        ).json()

        scene_data = scene_res.get("data") or {}
        scenes = scene_data.get("scenes", [])

        return jsonify({
            "conversation_id": cid,
            "scenes": scenes
        })

    except Exception as e:
        return jsonify({
            "error": "FETCH_FAILED",
            "details": str(e)
        }), 500


# =====================================
# STEP 2 — VIDEO STATUS (POLL SAFE)
# =====================================
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
        ).json()

        if r.get("code") != 100000:
            return jsonify({
                "error": "NOTEGPT_ERROR",
                "raw": r
            })

        data = r.get("data")
        if not data:
            return jsonify({
                "status": "processing",
                "step": "initializing"
            })

        if data.get("status") != "success":
            return jsonify({
                "status": data.get("status"),
                "step": data.get("step")
            })

        return jsonify({
            "status": "success",
            "video": {
                "title": data.get("title"),
                "video_url": data.get("cdn_video_url") or data.get("video_url"),
                "cover": data.get("cdn_cover_url") or data.get("cover_url")
            }
        })

    except Exception as e:
        return jsonify({
            "error": "STATUS_FAILED",
            "details": str(e)
        }), 500
