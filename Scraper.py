import xbmc
import xbmcaddon
import re

ADDON = xbmcaddon.Addon()

# CocoScrapers import
try:
    from cocoscrapers import sources as coco_sources
except:
    coco_sources = None
    xbmc.log("[SlyFox] CocoScrapers not installed", xbmc.LOGERROR)


# ---------------------------------------------------------
# Scrape using CocoScrapers
# ---------------------------------------------------------
def scrape(info):
    """
    info = {
        "title": ...,
        "year": ...,
        "season": ...,
        "episode": ...,
        "type": "movie" or "episode"
    }
    """
    if coco_sources is None:
        xbmc.log("[SlyFox] CocoScrapers unavailable", xbmc.LOGERROR)
        return []

    try:
        if info["type"] == "movie":
            results = coco_sources().get_movie_sources(info["title"], info["year"])
        else:
            results = coco_sources().get_episode_sources(
                info["title"], info["year"], info["season"], info["episode"]
            )
    except Exception as e:
        xbmc.log(f"[SlyFox] Scraper error: {e}", xbmc.LOGERROR)
        return []

    xbmc.log(f"[SlyFox] Scraped {len(results)} sources", xbmc.LOGINFO)
    return results


# ---------------------------------------------------------
# Filter Real-Debrid compatible sources
# ---------------------------------------------------------
def filter_rd(sources):
    rd_only = ADDON.getSettingBool("scrape.filter_rd")
    if not rd_only:
        return sources

    rd_sources = []
    for s in sources:
        if s.get("debrid") == "real-debrid" or s.get("source") == "torrent":
            rd_sources.append(s)

    xbmc.log(f"[SlyFox] RD-filtered: {len(rd_sources)} sources", xbmc.LOGINFO)
    return rd_sources


# ---------------------------------------------------------
# Quality Parsing
# ---------------------------------------------------------
def parse_quality(name):
    """
    Extracts quality from filename or label.
    """
    name = name.lower()

    if "2160" in name or "4k" in name:
        return 4
    if "1080" in name:
        return 3
    if "720" in name:
        return 2
    if "480" in name or "sd" in name:
        return 1
    return 0


# ---------------------------------------------------------
# Size Parsing
# ---------------------------------------------------------
def parse_size(size_str):
    """
    Converts size like '4.7 GB' or '1200 MB' into a float in GB.
    """
    if not size_str:
        return 0.0

    match = re.match(r"([\d\.]+)\s*(GB|MB)", size_str, re.I)
    if not match:
        return 0.0

    value = float(match.group(1))
    unit = match.group(2).upper()

    if unit == "GB":
        return value
    if unit == "MB":
        return value / 1024.0

    return 0.0


# ---------------------------------------------------------
# Sort by quality (highest → lowest)
# ---------------------------------------------------------
def sort_by_quality(sources):
    def sort_key(s):
        quality = parse_quality(s.get("quality", "") or s.get("name", ""))
        size = parse_size(s.get("size", ""))
        seeds = int(s.get("seeds", 0))
        return (quality, size, seeds)

    sorted_list = sorted(sources, key=sort_key, reverse=True)
    xbmc.log(f"[SlyFox] Sorted {len(sorted_list)} sources by quality", xbmc.LOGINFO)
    return sorted_list


# ---------------------------------------------------------
# Normalize source for picker
# ---------------------------------------------------------
def normalize_source(s):
    """
    Converts a CocoScrapers source into a clean dict for the picker.
    """
    return {
        "name": s.get("name") or s.get("provider") or "Unknown",
        "quality": s.get("quality") or "",
        "size": s.get("size") or "",
        "seeds": s.get("seeds") or 0,
        "url": s.get("url") or s.get("magnet") or "",
        "provider": s.get("provider") or "Unknown",
    }
