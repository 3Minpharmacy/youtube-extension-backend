
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
YT_ANALYTICS_API_BASE = "https://youtubeanalytics.googleapis.com/v2"

def fetch_meta(token, path):
    res = requests.get(f"{YOUTUBE_API_BASE}/{path}", headers={"Authorization": f"Bearer {token}"})
    return res.json()

def fetch_analytics(token, params):
    res = requests.get(f"{YT_ANALYTICS_API_BASE}/reports", headers={"Authorization": f"Bearer {token}"}, params=params)
    return res.json()

@app.route("/case1", methods=["POST"])
def case1():
    token = request.json.get("access_token")
    uploads = fetch_meta(token, "channels?part=contentDetails&mine=true")
    uploadsId = uploads["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    pl = fetch_meta(token, f"playlistItems?part=contentDetails&maxResults=50&playlistId={uploadsId}")
    ids = [i["contentDetails"]["videoId"] for i in pl["items"]]
    vids = fetch_meta(token, f"videos?part=snippet,statistics,player&id={','.join(ids)}")
    list_videos = [
        {
            "id": v["id"],
            "title": v["snippet"]["title"],
            "thumbnail": v["snippet"]["thumbnails"]["default"]["url"],
            "views": int(v["statistics"].get("viewCount", "0"))
        }
        for v in vids["items"]
        if "endscreen" not in v["player"]["embedHtml"]
    ]
    list_videos.sort(key=lambda x: -x["views"])
    html = ''.join([
        f'''
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
            <div style="display:flex;align-items:center;flex:1;">
                <img src="{v["thumbnail"]}" style="width:80px;height:45px;object-fit:cover;margin-right:8px;">
                <span style="font-weight:bold;">{v["title"]}</span>
            </div>
            <a href="https://studio.youtube.com/video/{v["id"]}/edit" target="_blank"
               style="background-color:#22c55e;color:#fff;padding:6px 12px;border-radius:4px;text-decoration:none;font-size:12px;">Edit</a>
        </div>
        '''
        for v in list_videos[:10]
    ])
    return jsonify({"html": html})

@app.route("/case2", methods=["POST"])
def case2():
    token = request.json.get("access_token")
    from datetime import datetime, timedelta
    today = datetime.now().date()
    end = today.isoformat()
    start = (today - timedelta(days=30)).isoformat()
    analyticsData = fetch_analytics(token, {
        "ids": "channel==MINE",
        "metrics": "views",
        "startDate": start,
        "endDate": end,
        "maxResults": 50,
        "sort": "-views",
        "dimensions": "playlist"
    })
    rows = analyticsData.get("rows", [])
    if not rows:
        return jsonify({"html": "<p>❌ No playlist view data available.</p>"})
    playlistIds = [r[0] for r in rows]
    info = fetch_meta(token, f"playlists?part=snippet,contentDetails&id={','.join(playlistIds)}")
    items = {i["id"]: i for i in info.get("items", [])}
    html = "".join([
        f'''
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
            <img src="{items[pid]["snippet"]["thumbnails"]["default"]["url"]}" style="width:80px;height:45px;object-fit:cover;margin-right:8px;">
            <span style="flex:1;font-weight:bold;">{items[pid]["snippet"]["title"]}</span>
            <a href="https://studio.youtube.com/playlist/{pid}/edit" target="_blank"
               class="text-xs font-semibold bg-green-600 text-white py-1 px-2 rounded">Edit</a>
        </div>
        ''' for pid in playlistIds if pid in items
    ])
    return jsonify({"html": html})

@app.route("/case3", methods=["POST"])
def case3():
    token = request.json.get("access_token")
    from datetime import datetime, timedelta
    end = datetime.now().date().isoformat()
    start = (datetime.now() - timedelta(days=30)).date().isoformat()

    ch = fetch_meta(token, "channels?part=contentDetails&mine=true")
    uploadsId = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    all_ids = []
    next_token = ""
    while True:
        url = f"playlistItems?part=contentDetails&maxResults=50&playlistId={uploadsId}"
        if next_token:
            url += f"&pageToken={next_token}"
        resp = fetch_meta(token, url)
        all_ids += [i["contentDetails"]["videoId"] for i in resp["items"]]
        next_token = resp.get("nextPageToken", "")
        if not next_token:
            break

    unique_ids = list(set(all_ids))
    view_data = []
    for vid in unique_ids[:100]:
        try:
            rep = fetch_analytics(token, {
                "ids": "channel==MINE",
                "metrics": "views",
                "startDate": start,
                "endDate": end,
                "filters": f"video=={vid}",
                "maxResults": 1
            })
            v = int(rep.get("rows", [[0]])[0][0])
            if 50 <= v <= 1000:
                view_data.append((vid, v))
        except:
            continue
    view_data.sort(key=lambda x: x[1])
    html = "<h4>Title Suggestions</h4>"
    for vid, views in view_data:
        meta = fetch_meta(token, f"videos?part=snippet&fields=items(id,snippet(title,thumbnails(default(url)),tags))&id={vid}")
        if not meta["items"]:
            continue
        item = meta["items"][0]["snippet"]
        title = item["title"]
        thumb = item["thumbnails"]["default"]["url"]
        tags = " | ".join(item.get("tags", [])[:3]) or "No tags"
        html += f'''
        <div style="margin-bottom:16px;border-bottom:1px solid #e2e8f0;padding-bottom:8px;">
            <div style="display:flex;align-items:center;margin-bottom:4px;">
                <img src="{thumb}" style="width:60px;height:60px;margin-right:8px;object-fit:cover;">
                <div style="font-weight:bold;flex:1;">{title}</div>
            </div>
            <div style="font-style:italic;background-color:#bfdbfe;color:#000;display:inline-block;padding:2px 6px;border-radius:4px;margin-bottom:4px;">
                Suggested Title: {tags}
            </div>
            <div style="display:flex;align-items:center;justify-content:space-between;">
                <span style="background:#fed7aa;padding:2px 6px;border-radius:4px;">{views} views</span>
                <a href="https://studio.youtube.com/video/{vid}/edit" target="_blank"
                   style="background:#22c55e;color:#fff;padding:4px 8px;border-radius:4px;text-decoration:none;">Edit</a>
            </div>
        </div>
        '''
    return jsonify({"html": html})
