import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
HANDLE = int(sys.argv[1])


# ---------------------------------------------------------
# Build ListItem for playback
# ---------------------------------------------------------
def build_listitem(url, info=None):
    li = xbmcgui.ListItem(path=url)

    if info:
        li.setInfo("video", {
            "title": info.get("title"),
            "year": int(info.get("year") or 0),
            "season": info.get("season"),
            "episode": info.get("episode"),
            "mediatype": info.get("type"),
        })

    # Basic artwork — TMDBHelper will override with full art
    li.setArt({
        "icon": "DefaultVideo.png",
        "thumb": "DefaultVideo.png",
        "poster": "DefaultVideo.png",
    })

    li.setProperty("IsPlayable", "true")
    return li


# ---------------------------------------------------------
# Play a URL directly
# ---------------------------------------------------------
def play_url(url, info):
    li = build_listitem(url, info)
    xbmcplugin.setResolvedUrl(HANDLE, True, li)
    xbmc.log(f"[SlyFox] Playing URL: {url}", xbmc.LOGINFO)
