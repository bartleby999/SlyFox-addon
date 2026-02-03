import xbmc
import xbmcaddon
import json
import os
import time

from . import scraper
from . import tmdb

ADDON = xbmcaddon.Addon()
PROFILE = xbmc.translatePath(ADDON.getAddonInfo("profile"))
CACHE_FILE = os.path.join(PROFILE, "nextup_cache.json")

# Ensure profile folder exists
if not os.path.exists(PROFILE):
    os.makedirs(PROFILE)


# ---------------------------------------------------------
# Save / Load Cache
# ---------------------------------------------------------
def save_cache(data):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except:
        xbmc.log("[SlyFox] Failed to save nextup cache", xbmc.LOGERROR)


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return None

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        xbmc.log("[SlyFox] Failed to load nextup cache", xbmc.LOGERROR)
        return None


def clear_cache():
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
        xbmc.log("[SlyFox] Nextup cache cleared", xbmc.LOGINFO)


# ---------------------------------------------------------
# Preloader Thread
# ---------------------------------------------------------
class Preloader(xbmc.Monitor):
    def __init__(self, info):
        super().__init__()
        self.info = info
        self.threshold = ADDON.getSettingInt("preload.threshold")  # default 80
        self.running = True

    def run(self):
        xbmc.log("[SlyFox] Preloader started", xbmc.LOGINFO)

        # Wait for playback to start
        while not xbmc.Player().isPlayingVideo() and not self.abortRequested():
            time.sleep(1)

        if self.abortRequested():
            return

        # Monitor playback progress
        while not self.abortRequested() and xbmc.Player().isPlayingVideo():
            try:
                player = xbmc.Player()
                total = player.getTotalTime()
                pos = player.getTime()

                if total > 0:
                    percent = (pos / total) * 100

                    if percent >= self.threshold:
                        xbmc.log(f"[SlyFox] Threshold reached ({percent:.1f}%) — preloading next episode", xbmc.LOGINFO)
                        self.preload_next_episode()
                        return

            except Exception as e:
                xbmc.log(f"[SlyFox] Preloader error: {e}", xbmc.LOGERROR)

            time.sleep(1)

    # -----------------------------------------------------
    # Scrape next episode early
    # -----------------------------------------------------
    def preload_next_episode(self):
        season = self.info.get("season")
        episode = self.info.get("episode")

        if season is None or episode is None:
            xbmc.log("[SlyFox] Not an episode — skipping preload", xbmc.LOGINFO)
            return

        next_ep = episode + 1

        # Look up next episode TMDB ID
        next_info = tmdb.get_info(self.info["tmdb"], "episode")
        next_info["episode"] = next_ep

        xbmc.log(f"[SlyFox] Preloading S{season}E{next_ep}", xbmc.LOGINFO)

        # Scrape
        sources = scraper.scrape(next_info)
        sources = scraper.filter_rd(sources)
        sources = scraper.sort_by_quality(sources)

        # Normalize for picker
        normalized = [scraper.normalize_source(s) for s in sources]

        # Save to cache
        save_cache(normalized)
        xbmc.log(f"[SlyFox] Cached {len(normalized)} sources for next episode", xbmc.LOGINFO)


# ---------------------------------------------------------
# Start Preloader
# ---------------------------------------------------------
def start(info):
    clear_cache()  # Always clear old data
    preloader = Preloader(info)
    xbmc.spawn_thread(preloader.run)
