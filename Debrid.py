import time
import json
import xbmc
import xbmcgui
import xbmcaddon
import requests

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")

API_BASE = "https://api.real-debrid.com/rest/1.0"
OAUTH_DEVICE = "https://api.real-debrid.com/oauth/v2/device/code"
OAUTH_TOKEN = "https://api.real-debrid.com/oauth/v2/token"

CLIENT_ID = "X245A4XAIBGVM"  # Official RD client ID for device auth


# ---------------------------------------------------------
# Token Storage Helpers
# ---------------------------------------------------------
def _get_token():
    token = ADDON.getSettingString("rd.token")
    if not token:
        return None
    try:
        return json.loads(token)
    except:
        return None


def _save_token(data):
    ADDON.setSettingString("rd.token", json.dumps(data))


def _clear_token():
    ADDON.setSettingString("rd.token", "")


# ---------------------------------------------------------
# OAuth Login
# ---------------------------------------------------------
def authenticate():
    # Step 1: Request device code
    r = requests.post(OAUTH_DEVICE, data={"client_id": CLIENT_ID, "new_credentials": "yes"})
    if r.status_code != 200:
        xbmcgui.Dialog().notification("SlyFox", "Failed to contact Real-Debrid", xbmcgui.NOTIFICATION_ERROR)
        return

    data = r.json()
    user_code = data["user_code"]
    device_code = data["device_code"]
    interval = data["interval"]
    verify_url = data["verification_url"]

    # Show instructions
    xbmcgui.Dialog().ok(
        "Real-Debrid Login",
        f"1. Visit: [B]{verify_url}[/B]\n"
        f"2. Enter the code: [B]{user_code}[/B]\n\n"
        "Waiting for authorization…"
    )

    # Step 2: Poll for authorization
    while True:
        time.sleep(interval)

        poll = requests.post(OAUTH_TOKEN, data={
            "client_id": CLIENT_ID,
            "code": device_code,
            "grant_type": "http://oauth.net/grant_type/device/1.0"
        })

        if poll.status_code == 200:
            token_data = poll.json()
            _save_token(token_data)
            xbmcgui.Dialog().notification("SlyFox", "Real-Debrid login successful", xbmcgui.NOTIFICATION_INFO)
            return

        err = poll.json().get("error")
        if err == "authorization_pending":
            continue
        if err == "expired_token":
            xbmcgui.Dialog().notification("SlyFox", "Login expired, try again", xbmcgui.NOTIFICATION_ERROR)
            return
        else:
            xbmcgui.Dialog().notification("SlyFox", "Login failed", xbmcgui.NOTIFICATION_ERROR)
            return


# ---------------------------------------------------------
# Token Refresh
# ---------------------------------------------------------
def _refresh_token():
    token = _get_token()
    if not token or "refresh_token" not in token:
        return False

    r = requests.post(OAUTH_TOKEN, data={
        "client_id": CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": token["refresh_token"]
    })

    if r.status_code != 200:
        return False

    new_token = r.json()
    _save_token(new_token)
    return True


# ---------------------------------------------------------
# Authorized Request Helper
# ---------------------------------------------------------
def _request(method, endpoint, **kwargs):
    token = _get_token()
    if not token:
        xbmcgui.Dialog().notification("SlyFox", "Real-Debrid not logged in", xbmcgui.NOTIFICATION_ERROR)
        return None

    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token['access_token']}"

    url = f"{API_BASE}/{endpoint}"

    r = requests.request(method, url, headers=headers, **kwargs)

    # Token expired → refresh and retry
    if r.status_code == 401:
        if _refresh_token():
            token = _get_token()
            headers["Authorization"] = f"Bearer {token['access_token']}"
            r = requests.request(method, url, headers=headers, **kwargs)

    if r.status_code not in (200, 201):
        xbmc.log(f"[SlyFox] RD API error {r.status_code}: {r.text}", xbmc.LOGERROR)
        return None

    return r.json()


# ---------------------------------------------------------
# Resolve URL / Magnet
# ---------------------------------------------------------
def resolve(url):
    # Step 1: Unrestrict link
    result = _request("POST", "unrestrict/link", data={"link": url})
    if not result:
        return None

    return result.get("download")


# ---------------------------------------------------------
# Account Info
# ---------------------------------------------------------
def get_account_info():
    info = _request("GET", "user")
    if not info:
        return "Unable to retrieve account info."

    out = [
        f"Username: {info.get('username')}",
        f"Email: {info.get('email')}",
        f"Points: {info.get('points')}",
        f"Premium: {info.get('premium')}",
        f"Expiration: {info.get('expiration')}",
    ]
    return "\n".join(out)


# ---------------------------------------------------------
# Torrent History
# ---------------------------------------------------------
def get_torrent_history():
    history = _request("GET", "torrents")
    if not history:
        return "Unable to retrieve torrent history."

    lines = []
    for item in history:
        lines.append(f"{item.get('filename')}  —  {item.get('status')}")

    return "\n".join(lines)
