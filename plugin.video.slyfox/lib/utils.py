import xbmc
import xbmcgui
import json
import base64


# ---------------------------------------------------------
# Logging Helpers
# ---------------------------------------------------------
def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[SlyFox] {msg}", level)


# ---------------------------------------------------------
# Decode TMDBHelper Source Payload
# ---------------------------------------------------------
def decode_sources(encoded):
    """
    TMDBHelper passes sources as a base64-encoded JSON string.
    """
    if not encoded:
        return None

    try:
        raw = base64.b64decode(encoded).decode("utf-8")
        return json.loads(raw)
    except Exception as e:
        log(f"Failed to decode sources: {e}", xbmc.LOGERROR)
        return None


# ---------------------------------------------------------
# Format Helpers
# ---------------------------------------------------------
def fmt_quality(q):
    q = str(q).lower()
    if "2160" in q or "4k" in q:
        return "4K"
    if "1080" in q:
        return "1080p"
    if "720" in q:
        return "720p"
    if "480" in q or "sd" in q:
        return "SD"
    return "Unknown"


def fmt_size(size):
    if not size:
        return ""
    return size


def fmt_provider(p):
    if not p:
        return "Unknown"
    return p.title()


# ---------------------------------------------------------
# Rich Source Picker
# ---------------------------------------------------------
def pick_source(sources):
    """
    Shows a dialog with quality, size, seeds, provider.
    Returns the selected source dict.
    """
    if not sources:
        xbmcgui.Dialog().notification("SlyFox", "No sources available", xbmcgui.NOTIFICATION_ERROR)
        return None

    items = []
    for s in sources:
        quality = fmt_quality(s.get("quality"))
        size = fmt_size(s.get("size"))
        seeds = s.get("seeds", 0)
        provider = fmt_provider(s.get("provider"))

        label = f"[B]{quality}[/B]  |  {size}  |  Seeds: {seeds}  |  {provider}"
        items.append(label)
