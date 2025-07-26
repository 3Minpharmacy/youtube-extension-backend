from flask import Flask, request, jsonify
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

# --- Helpers ---
def get_headers(token):
    return {"Authorization": f"Bearer {token}"}

def get_date(days):
    return (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')

# --- Routes ---

@app.route('/api/meta', methods=['POST'])
def fetch_meta():
    data = request.json
    path = data.get('path')
    token = data.get('token')
    url = f"https://www.googleapis.com/youtube/v3/{path}"
    res = requests.get(url, headers=get_headers(token))
    return jsonify(res.json())

@app.route('/api/analytics', methods=['POST'])
def fetch_analytics():
    data = request.json
    token = data.get('token')
    params = data.get('params')
    url = "https://youtubeanalytics.googleapis.com/v2/reports"
    res = requests.get(url, headers=get_headers(token), params=params)
    return jsonify(res.json())

@app.route('/api/update-title', methods=['POST'])
def update_title():
    data = request.json
    token = data.get('token')
    video_id = data.get('videoId')
    new_title = data.get('newTitle')

    # Fetch current snippet
    meta_url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}"
    meta_res = requests.get(meta_url, headers=get_headers(token)).json()
    snippet = meta_res['items'][0]['snippet']
    snippet['title'] = new_title

    # Update title
    update_url = "https://www.googleapis.com/youtube/v3/videos?part=snippet"
    payload = {"id": video_id, "snippet": snippet}
    update_res = requests.put(update_url, headers={**get_headers(token), "Content-Type": "application/json"}, json=payload)
    return jsonify(update_res.json())

@app.route('/api/suggest-titles', methods=['POST'])
def suggest_titles():
    data = request.json
    token = data.get('token')
    start = get_date(30)
    end = get_date(0)

    ch_resp = requests.get("https://www.googleapis.com/youtube/v3/channels?part=contentDetails&mine=true",
                            headers=get_headers(token)).json()
    uploads_id = ch_resp['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    video_ids = []
    next_page = ''
    while True:
        pl_url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&maxResults=50&playlistId={uploads_id}"
        if next_page:
            pl_url += f"&pageToken={next_page}"
        pl_resp = requests.get(pl_url, headers=get_headers(token)).json()
        for item in pl_resp.get('items', []):
            video_ids.append(item['contentDetails']['videoId'])
        next_page = pl_resp.get('nextPageToken')
        if not next_page:
            break

    result = []
    for vid in video_ids:
        try:
            params = {
                "ids": "channel==MINE",
                "metrics": "views",
                "filters": f"video=={vid}",
                "startDate": start,
                "endDate": end,
                "maxResults": "1",
                "dimensions": "video"
            }
            res = requests.get("https://youtubeanalytics.googleapis.com/v2/reports", headers=get_headers(token), params=params).json()
            views = res.get('rows', [[None, 0]])[0][1]
            result.append({"id": vid, "views": views})
        except:
            continue

    filtered = [r for r in result if 50 <= r['views'] <= 1000]
    return jsonify({"videos": filtered})

@app.route('/api/zero-view-titles', methods=['POST'])
def zero_view_titles():
    data = request.json
    token = data.get('token')
    start = get_date(30)
    end = get_date(0)

    ch_resp = requests.get("https://www.googleapis.com/youtube/v3/channels?part=contentDetails&mine=true",
                            headers=get_headers(token)).json()
    uploads_id = ch_resp['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    video_ids = []
    next_page = ''
    while True:
        pl_url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&maxResults=50&playlistId={uploads_id}"
        if next_page:
            pl_url += f"&pageToken={next_page}"
        pl_resp = requests.get(pl_url, headers=get_headers(token)).json()
        for item in pl_resp.get('items', []):
            video_ids.append(item['contentDetails']['videoId'])
        next_page = pl_resp.get('nextPageToken')
        if not next_page:
            break

    result = []
    for vid in video_ids:
        try:
            params = {
                "ids": "channel==MINE",
                "metrics": "views",
                "filters": f"video=={vid}",
                "startDate": start,
                "endDate": end,
                "maxResults": "1",
                "dimensions": "video"
            }
            res = requests.get("https://youtubeanalytics.googleapis.com/v2/reports", headers=get_headers(token), params=params).json()
            views = res.get('rows', [[None, 0]])[0][1]
            if views <= 50:
                result.append({"id": vid, "views": views})
        except:
            continue

    return jsonify({"videos": result})

@app.route('/')
def index():
    return "YouTube Extension Backend is running."

if __name__ == '__main__':
    app.run(debug=True)
