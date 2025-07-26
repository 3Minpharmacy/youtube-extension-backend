
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
YT_ANALYTICS_API_BASE = "https://youtubeanalytics.googleapis.com/v2"

@app.route("/channel-info", methods=["POST"])
def channel_info():
    token = request.json.get("access_token")
    res = requests.get(
        f"{YOUTUBE_API_BASE}/channels?part=snippet,statistics&mine=true",
        headers={"Authorization": f"Bearer {token}"}
    )
    return jsonify(res.json())

@app.route("/analytics", methods=["POST"])
def analytics():
    data = request.json
    token = data.pop("access_token")
    res = requests.get(
        f"{YT_ANALYTICS_API_BASE}/reports",
        headers={"Authorization": f"Bearer {token}"},
        params=data
    )
    return jsonify(res.json())

@app.route("/update-title", methods=["POST"])
def update_title():
    token = request.json["access_token"]
    video_id = request.json["video_id"]
    new_title = request.json["new_title"]
    # Fetch snippet
    meta = requests.get(
        f"{YOUTUBE_API_BASE}/videos?part=snippet&id={video_id}",
        headers={"Authorization": f"Bearer {token}"}
    ).json()
    snippet = meta["items"][0]["snippet"]
    snippet["title"] = new_title
    # Patch title
    res = requests.put(
        f"{YOUTUBE_API_BASE}/videos?part=snippet",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={"id": video_id, "snippet": snippet}
    )
    return jsonify(res.json())
