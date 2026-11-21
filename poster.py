"""Prarabdha autopost: publishes due posts from schedule.json to Instagram.

Runs inside GitHub Actions (free for public repos). Uses the official Instagram Graph API
(Facebook Login version, graph.facebook.com), which also allows attaching trending audio
from Instagram's licensed library. Media is served from this repo through jsDelivr, so no
Netlify or other hosting is needed.

Secrets (set in GitHub > Settings > Secrets and variables > Actions):
  IG_TOKEN    long-lived Instagram user access token
  IG_USER_ID  Instagram professional account id
"""
import json, os, sys, time, datetime as dt
import urllib.request, urllib.parse, urllib.error

# Instagram Login tokens use graph.instagram.com (default); Facebook Login tokens use graph.facebook.com.
HOST = os.environ.get("IG_API_HOST") or "graph.instagram.com"
API = f"https://{HOST}/v22.0"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
WINDOW_MIN = int(os.environ.get("WINDOW_MIN", "180"))      # post items due within the last N minutes
REPO = os.environ.get("GITHUB_REPOSITORY", "")             # owner/name, set by Actions
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
DRY = os.environ.get("DRY_RUN") == "1"

def media_url(path):
    return f"https://cdn.jsdelivr.net/gh/{REPO}@{BRANCH}/{path}"

def raw_url(path):
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{path}"

def call(method, endpoint, **params):
    params["access_token"] = os.environ["IG_TOKEN"]
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{endpoint}"
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {endpoint} -> {e.code}: {e.read().decode()[:500]}")

def wait_ready(container_id, minutes=8):
    for _ in range(minutes * 6):
        st = call("GET", container_id, fields="status_code,status").get("status_code")
        if st == "FINISHED": return
        if st in ("ERROR", "EXPIRED"): raise RuntimeError(f"container {container_id} status {st}")
        time.sleep(10)
    raise RuntimeError(f"container {container_id} not ready in time")

def publish(container_id):
    return call("POST", f"{os.environ['IG_USER_ID']}/media_publish", creation_id=container_id)["id"]

def pick_audio(item):
    """Return an audio_configuration JSON string, or None.
    item["audio"]: "trending" picks the top trending licensed track; or a specific audio id."""
    a = item.get("audio")
    if not a or HOST != "graph.facebook.com": return None   # licensed audio needs a Facebook Login token
    try:
        if a == "trending":
            res = call("GET", "ig_audio", audio_type="music", user_id=os.environ["IG_USER_ID"])
            lst = res.get("data", [])
            if not lst: return None
            a = str(lst[0]["id"]); print("  trending audio:", lst[0].get("title", a))
        return json.dumps({"audio_id": str(a), "audio_volume": item.get("audio_volume", 60),
                           "video_volume": item.get("video_volume", 25)})
    except Exception as e:
        print("  audio lookup failed, posting with own music:", e); return None

def post_reel(item):
    uid = os.environ["IG_USER_ID"]
    last = None; audio = pick_audio(item)
    for url in (media_url(item["files"][0]), raw_url(item["files"][0])):
        try:
            extra = {"audio_configuration": audio} if audio else {}
            c = call("POST", f"{uid}/media", media_type="REELS", video_url=url, caption=item["caption"],
                     share_to_feed="true", thumb_offset=str(item.get("thumb_offset", 1500)), **extra)["id"]
            wait_ready(c); return publish(c)
        except Exception as e:
            last = e; print("  retrying with next URL:", e)
    raise last

def post_carousel(item):
    uid = os.environ["IG_USER_ID"]; kids = []
    for f in item["files"]:
        cid = call("POST", f"{uid}/media", image_url=raw_url(f), is_carousel_item="true")["id"]
        wait_ready(cid, 3); kids.append(cid)
    c = call("POST", f"{uid}/media", media_type="CAROUSEL", children=",".join(kids), caption=item["caption"])["id"]
    wait_ready(c, 3); return publish(c)

def post_image(item):
    uid = os.environ["IG_USER_ID"]
    c = call("POST", f"{uid}/media", image_url=raw_url(item["files"][0]), caption=item["caption"])["id"]
    wait_ready(c, 3); return publish(c)

def due(item, now):
    when = dt.datetime.fromisoformat(item["when_ist"]).replace(tzinfo=IST)
    return when <= now and (now - when).total_seconds() <= WINDOW_MIN * 60 or item.get("post_now")

def main():
    if not os.environ.get("IG_TOKEN"):
        print("IG_TOKEN not set yet: nothing to do. Add it in Settings > Secrets."); return
    if not os.environ.get("IG_USER_ID"):
        os.environ["IG_USER_ID"] = "me"
    sched = json.load(open("schedule.json"))
    done = json.load(open("posted.json")) if os.path.exists("posted.json") else {}
    now = dt.datetime.now(IST); changed = False
    if "--force" in sys.argv:   # manual run: post one specific id
        ids = sys.argv[sys.argv.index("--force") + 1:]
    else:
        ids = [i["id"] for i in sched if i["id"] not in done and due(i, now)]
    for it in [i for i in sched if i["id"] in ids]:
        if it["id"] in done: print("already posted", it["id"]); continue
        print("posting", it["id"], it["type"], it["when_ist"])
        if DRY: continue
        try:
            mid = {"reel": post_reel, "carousel": post_carousel, "image": post_image}[it["type"]](it)
            done[it["id"]] = {"media_id": mid, "posted_at": dt.datetime.now(IST).isoformat(timespec="seconds")}
            changed = True; print("  live, media id", mid)
        except Exception as e:
            print("  FAILED", it["id"], e)
    if changed:
        json.dump(done, open("posted.json", "w"), indent=1)
    print(f"{now:%Y-%m-%d %H:%M} IST · checked {len(sched)} items · posted {sum(1 for i in ids if i in done)}")

if __name__ == "__main__":
    main()
