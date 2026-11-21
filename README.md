# Prarabdha autopost (free Instagram posting bot)

GitHub Actions checks `schedule.json` every 30 minutes and publishes anything that is due
(times are IST) through the official Instagram Graph API. Reels can carry trending licensed
Instagram audio (`"audio": "trending"` in a schedule row). Media in `media/` is served free through
jsDelivr. `posted.json` records what went out, so nothing posts twice. Free for public repos.

## One-time setup (about 20 minutes)
1. **Repo**: on GitHub create a new **public** repository called `prarabdha-autopost`.
   Upload everything in this folder (Add file > Upload files). If the `.github` folder does not
   upload, use Add file > Create new file, name it `.github/workflows/post.yml` and paste the file;
   repeat for `refresh-token.yml`.
2. **Instagram token** (free): developers.facebook.com > My Apps > Create app (type Business).
   Open Tools > Graph API Explorer, pick your app, add the permissions `instagram_basic`,
   `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`, `business_management`,
   click Generate Access Token and log in with the Facebook account that owns the Page linked
   to @prarabdhaaapke. Then in Access Token Debugger click "Extend Access Token" (60 days).
   Your Instagram user ID is 17841443448260782. The app can stay in development mode.
3. **Secrets**: repo Settings > Secrets and variables > Actions > New repository secret:
   - `IG_TOKEN`: the token from step 2
   - `IG_USER_ID`: 17841443448260782
   - `APP_ID` and `APP_SECRET`: from your app's Settings > Basic (used only to renew the token)
   - `GH_PAT`: a fine-grained GitHub token for this repo with **Secrets: read and write**
     (lets the bot renew the 60-day token by itself on the 1st and 15th).
   Never paste these into a chat.
4. **Turn it on**: open the Actions tab, enable workflows, and run **Post due Instagram content** once.

## Each week
New media goes in `media/wN/` and new rows in `schedule.json`:
```json
{"id": "w2_moolank_1", "when_ist": "2026-11-29T19:30", "type": "reel",
 "files": ["media/w2/moolank_1.mp4"], "caption": "..."}
```
`type` is `reel`, `carousel` (2 to 10 JPEG files) or `image`.
To post something immediately: Actions > Post due Instagram content > Run workflow, and enter its id.

Note: GitHub pauses scheduled workflows after 60 days with no commits; the weekly upload keeps it active.
