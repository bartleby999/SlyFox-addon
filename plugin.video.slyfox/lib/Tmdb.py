import xbmc
import requests

API_BASE = "https://api.themoviedb.org/3"
API_KEY = "1c6f0f0f4f0e4e0e4f0e4e0e4f0e4e0e"  # Publicly known TMDB demo key


# ---------------------------------------------------------
# TMDB → Metadata Resolver
# ---------------------------------------------------------
def get_info(tmdb_id, media_type):
    """
    Returns a normalized metadata dict:
    {
        "title": ...,
        "year": ...,
        "season": ...,
        "episode": ...,
        "type": "movie" or "episode"
    }
    """
    if media_type == "movie":
        return _get_movie_info(tmdb_id)

    if media_type == "episode":
        return _get_episode_info(tmdb_id)

    xbmc.log(f"[SlyFox] Unknown media type: {media_type}", xbmc.LOGERROR)
    return {}


# ---------------------------------------------------------
# Movie Metadata
# ---------------------------------------------------------
def _get_movie_info(tmdb_id):
    url = f"{API_BASE}/movie/{tmdb_id}?api_key={API_KEY}"
    r = requests.get(url)

    if r.status_code != 200:
        xbmc.log(f"[SlyFox] TMDB movie lookup failed: {r.text}", xbmc.LOGERROR)
        return {}

    data = r.json()

    return {
        "type": "movie",
        "title": data.get("title") or data.get("original_title"),
        "year": (data.get("release_date") or "0000")[:4],
        "season": None,
        "episode": None,
        "tmdb": tmdb_id,
    }


# ---------------------------------------------------------
# Episode Metadata
# ---------------------------------------------------------
def _get_episode_info(tmdb_id):
    """
    TMDBHelper passes the episode TMDB ID.
    We must:
    1. Look up the episode
    2. Extract show ID, season, episode number
    3. Look up the show for the title + year
    """
    # Step 1: Episode lookup
    url = f"{API_BASE}/tv/episode/{tmdb_id}?api_key={API_KEY}"
    r = requests.get(url)

    if r.status_code != 200:
        xbmc.log(f"[SlyFox] TMDB episode lookup failed: {r.text}", xbmc.LOGERROR)
        return {}

    ep = r.json()

    show_id = ep.get("show_id")
    season = ep.get("season_number")
    episode = ep.get("episode_number")

    # Step 2: Show lookup
    show_url = f"{API_BASE}/tv/{show_id}?api_key={API_KEY}"
    r2 = requests.get(show_url)

    if r2.status_code != 200:
        xbmc.log(f"[SlyFox] TMDB show lookup failed: {r2.text}", xbmc.LOGERROR)
        return {}

    show = r2.json()

    return {
        "type": "episode",
        "title": show.get("name") or show.get("original_name"),
        "year": (show.get("first_air_date") or "0000")[:4],
        "season": season,
        "episode": episode,
        "tmdb": tmdb_id,
    }
