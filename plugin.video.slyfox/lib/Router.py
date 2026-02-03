import sys
import urllib.parse
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from . import scraper
from . import debrid
from . import tmdb
from . import player
from . import nextup_preloader
from . import utils

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
HANDLE = int(sys.argv[1])


# ---------------------------------------------------------
# Utility: Parse plugin parameters
# ---------------------------------------------------------
def get_params():
    if len(sys.argv) < 3:
        return {}
    query = sys.argv[2][1:]
    return dict(urllib.parse.parse_qsl(query))


# ---------------------------------------------------------
# Main Router
# ---------------------------------------------------------
def router():
    params = get_params()
    action = params.get("action")

    if action is None:
        xbmcgui.Dialog().notification("SlyFox", "No action provided", xbmcgui.NOTIFICATION_INFO)
        return

    # TMDBHelper Player Endpoints
    if action == "play":
        return play_item(params)

    if action == "preload":
        return preload_next(params)

    if action == "next":
        return play_next(params)

    if action == "source_select":
        return source_select(params)

    if action == "resolve":
        return resolve_rd(params)

    # Real-Debrid Actions
    if action == "rd_auth":
        return rd_auth()

    if action == "rd_account":
        return rd_account()

    if action == "rd_history":
        return rd_history()

    # Debug / Maintenance
    if action == "clear_cache":
        return clear_cache()

    xbmcgui.Dialog().notification("SlyFox", f"Unknown action: {action}", xbmcgui.NOTIFICATION_ERROR)


# ---------------------------------------------------------
# /play — TMDBHelper calls this to play a movie/episode
# ---------------------------------------------------------
def play_item(params):
    tmdb_id = params.get("tmdb")
    media_type = params.get("type")

    if not tmdb_id or not media_type:
        xbmcgui.Dialog().notification("SlyFox", "Missing TMDB parameters", xbmcgui.NOTIFICATION_ERROR)
        return

    # Convert TMDB → metadata
    info = tmdb.get_info(tmdb_id, media_type)

    # Scrape sources
    sources = scraper.scrape(info)

    # Filter RD sources
    rd_sources = scraper.filter_rd(sources)

    if not rd_sources:
        xbmcgui.Dialog().notification("SlyFox", "No Real-Debrid sources found", xbmcgui.NOTIFICATION_ERROR)
        return

    # Sort by quality
    rd_sources = scraper.sort_by_quality(rd_sources)

    # Show rich picker
    choice = utils.pick_source(rd_sources)
    if choice is None:
        return

    # Resolve via RD
    stream_url = debrid.resolve(choice["url"])
    if not stream_url:
        xbmcgui.Dialog().notification("SlyFox", "Failed to resolve RD link", xbmcgui.NOTIFICATION_ERROR)
        return

    # Play
    player.play_url(stream_url, info)


# ---------------------------------------------------------
# /preload — TMDBHelper calls this when playback starts
# ---------------------------------------------------------
def preload_next(params):
    tmdb_id = params.get("tmdb")
    media_type = params.get("type")

    if media_type != "episode":
        return  # Only preload episodes

    info = tmdb.get_info(tmdb_id, media_type)
    nextup_preloader.start(info)
    xbmc.log("[SlyFox] Preloading thread started", xbmc.LOGINFO)


# ---------------------------------------------------------
# /next — TMDBHelper or Next Up calls this for next episode
# ---------------------------------------------------------
def play_next(params):
    cached = nextup_preloader.load_cache()
    if not cached:
        xbmcgui.Dialog().notification("SlyFox", "No preloaded sources", xbmcgui.NOTIFICATION_ERROR)
        return

    # Show picker
    choice = utils.pick_source(cached)
    if choice is None:
        return

    # Resolve
    stream_url = debrid.resolve(choice["url"])
    if not stream_url:
        xbmcgui.Dialog().notification("SlyFox", "Failed to resolve RD link", xbmcgui.NOTIFICATION_ERROR)
        return

    # Play
    info = cached[0].get("info", {})
    player.play_url(stream_url, info)


# ---------------------------------------------------------
# /source_select — TMDBHelper wants SlyFox to pick a source
# ---------------------------------------------------------
def source_select(params):
    sources = utils.decode_sources(params.get("sources"))
    if not sources:
        xbmcgui.Dialog().notification("SlyFox", "No sources provided", xbmcgui.NOTIFICATION_ERROR)
        return

    sources = scraper.sort_by_quality(sources)
    choice = utils.pick_source(sources)

    if choice is None:
        return

    xbmcplugin.setResolvedUrl(HANDLE, True, player.build_listitem(choice["url"]))


# ---------------------------------------------------------
# /resolve — TMDBHelper wants RD to resolve a URL/magnet
# ---------------------------------------------------------
def resolve_rd(params):
    url = params.get("url")
    if not url:
        xbmcgui.Dialog().notification("SlyFox", "No URL provided", xbmcgui.NOTIFICATION_ERROR)
        return

    stream_url = debrid.resolve(url)
    if not stream_url:
        xbmcgui.Dialog().notification("SlyFox", "RD resolve failed", xbmcgui.NOTIFICATION_ERROR)
        return

    xbmcplugin.setResolvedUrl(HANDLE, True, player.build_listitem(stream_url))


# ---------------------------------------------------------
# Real-Debrid Actions
# ---------------------------------------------------------
def rd_auth():
    debrid.authenticate()


def rd_account():
    info = debrid.get_account_info()
    xbmcgui.Dialog().textviewer("Real-Debrid Account", info)


def rd_history():
    history = debrid.get_torrent_history()
    xbmcgui.Dialog().textviewer("RD Torrent History", history)


# ---------------------------------------------------------
# Debug / Maintenance
# ---------------------------------------------------------
def clear_cache():
    nextup_preloader.clear_cache()
    xbmcgui.Dialog().notification("SlyFox", "Cache cleared", xbmcgui.NOTIFICATION_INFO)


# ---------------------------------------------------------
# Entry Point
# ---------------------------------------------------------
if __name__ == "__main__":
    router()
