from flask import Flask, request, jsonify
import requests
from datetime import datetime, timedelta
import os

app = Flask(__name__)

YOUTUBE_ANALYTICS_URL = "https://youtubeanalytics.googleapis.com/v2/reports"
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3"


def get_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

# --- AUTHENTICATION + CHANNEL INFO ---
@app.route("/api/channel-info", methods=["POST"])
def channel_info():
    token = request.json.get("token")
    try:
        res = requests.get(f"{YOUTUBE_API_URL}/channels?part=snippet,statistics&mine=true", headers=get_headers(token))
        return jsonify(res.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- FETCH HELPERS ---
@app.route("/api/fetch-analytics", methods=["POST"])
def fetch_analytics():
    data = request.json
    params = {
        "ids": "channel==MINE",
        "metrics": ",".join(data.get("metrics", [])),
        "startDate": data["start"],
        "endDate": data["end"],
        "maxResults": str(data.get("maxResults", 10)),
        "startIndex": str(data.get("startIndex", 1))
    }
    if data.get("filters"):
        params["filters"] = ",".join(data["filters"])
    if data.get("sort"):
        params["sort"] = data["sort"]
    if data.get("dimension"):
        params["dimensions"] = data["dimension"]

    res = requests.get(YOUTUBE_ANALYTICS_URL, headers=get_headers(data["token"]), params=params)
    return jsonify(res.json())

@app.route("/api/fetch-meta", methods=["POST"])
def fetch_meta():
    data = request.json
    res = requests.get(f"{YOUTUBE_API_URL}/{data['path']}", headers=get_headers(data["token"]))
    return jsonify(res.json())

# --- UPDATE VIDEO TITLE ---
@app.route("/api/update-title", methods=["POST"])
def update_title():
    data = request.json
    meta = requests.get(f"{YOUTUBE_API_URL}/videos?part=snippet&id={data['videoId']}", headers=get_headers(data["token"])).json()
    snippet = meta["items"][0]["snippet"]
    snippet["title"] = data["newTitle"]
    res = requests.put(f"{YOUTUBE_API_URL}/videos?part=snippet", headers=get_headers(data["token"]), json={"id": data["videoId"], "snippet": snippet})
    return jsonify(res.json())

# --- CASE 1: Add End Screens ---
@app.route("/api/add-end-screens", methods=["POST"])
def handle_add_end_screens():
    token = request.json.get("token")
    today = datetime.utcnow()
    start_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
    uploads = requests.get(f"{YOUTUBE_API_URL}/channels?part=contentDetails&mine=true", headers=get_headers(token)).json()
    uploads_id = uploads["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    playlist = requests.get(f"{YOUTUBE_API_URL}/playlistItems?part=contentDetails&maxResults=50&playlistId={uploads_id}", headers=get_headers(token)).json()
    video_ids = [i["contentDetails"]["videoId"] for i in playlist["items"]]
    if not video_ids:
        return jsonify({"html": "<p>🎉 No uploads.</p>"})
    vids = requests.get(f"{YOUTUBE_API_URL}/videos?part=snippet,statistics,player&id={','.join(video_ids)}", headers=get_headers(token)).json()
    filtered = [v for v in vids["items"] if "endscreen" not in v["player"]["embedHtml"]]
    sorted_vids = sorted(filtered, key=lambda v: int(v["statistics"].get("viewCount", 0)), reverse=True)
    return jsonify({"videos": sorted_vids[:10]})

# --- CASE 2: Top Playlists ---
@app.route("/api/add-playlists", methods=["POST"])
def handle_add_more_videos_playlists():
    token = request.json.get("token")
    end = datetime.utcnow().strftime('%Y-%m-%d')
    start = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
    analytics = requests.get(
        YOUTUBE_ANALYTICS_URL,
        headers=get_headers(token),
        params={
            "ids": "channel==MINE",
            "metrics": "views",
            "startDate": start,
            "endDate": end,
            "maxResults": "50",
            "sort": "-views",
            "dimensions": "playlist"
        }
    ).json()
    ids = [r[0] for r in analytics.get("rows", [])]
    if not ids:
        return jsonify({"html": "<p>❌ No playlist view data available.</p>"})
    info = requests.get(f"{YOUTUBE_API_URL}/playlists?part=snippet,contentDetails&id={','.join(ids)}", headers=get_headers(token)).json()
    return jsonify({"playlists": info.get("items", [])})

# --- CASE 3: Suggest Titles (simplified) ---
@app.route("/api/suggest-titles", methods=["POST"])
def handle_suggest_titles():
    token = request.json.get("token")
    end = datetime.utcnow().strftime('%Y-%m-%d')
    start = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
    ch = requests.get(f"{YOUTUBE_API_URL}/channels?part=contentDetails&mine=true", headers=get_headers(token)).json()
    uploads_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    all_ids, next_token = [], ""
    while True:
        pl_url = f"{YOUTUBE_API_URL}/playlistItems?part=contentDetails&maxResults=50&playlistId={uploads_id}"
        if next_token:
            pl_url += f"&pageToken={next_token}"
        pl_data = requests.get(pl_url, headers=get_headers(token)).json()
        all_ids += [i["contentDetails"]["videoId"] for i in pl_data["items"]]
        next_token = pl_data.get("nextPageToken")
        if not next_token:
            break
    return jsonify({"video_ids": list(set(all_ids))[:100]})

# --- CASE 6: Videos with 0–50 Views (stub) ---
@app.route("/api/zero-view-titles", methods=["POST"])
def handle_zero_view_titles():
    token = request.json.get("token")
    end = datetime.utcnow().strftime('%Y-%m-%d')
    start = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
    ch = requests.get(f"{YOUTUBE_API_URL}/channels?part=contentDetails&mine=true", headers=get_headers(token)).json()
    uploads_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    all_ids, next_token = [], ""
    while True:
        url = f"{YOUTUBE_API_URL}/playlistItems?part=contentDetails&maxResults=50&playlistId={uploads_id}"
        if next_token:
            url += f"&pageToken={next_token}"
        resp = requests.get(url, headers=get_headers(token)).json()
        all_ids += [i["contentDetails"]["videoId"] for i in resp["items"]]
        next_token = resp.get("nextPageToken")
        if not next_token:
            break
    return jsonify({"video_ids": list(set(all_ids))})

@app.route("/")
def root():
    return {"status": "YouTube Extension Full Backend is Running"}

if __name__ == "__main__":
    app.run(debug=True)
