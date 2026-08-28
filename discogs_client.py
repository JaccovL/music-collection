import requests
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DISCOGS_API = "https://api.discogs.com"

class DiscogsClient:
    def __init__(self, token, username):
        self.token = token
        self.username = username
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Discogs token={token}',
            'User-Agent': 'MusicCollectionApp/1.0'
        })
        self._last_request = 0
        self._min_interval = 1.0  # Discogs rate limit: 60 req/min for authenticated
    
    def _request(self, url, params=None):
        # Rate limiting
        elapsed = time.time() - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        
        try:
            resp = self.session.get(url, params=params, timeout=30)
            self._last_request = time.time()
            
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 404:
                logger.warning(f"Not found: {url}")
                return None
            elif resp.status_code == 429:
                # Rate limited - wait and retry
                retry_after = int(resp.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited, waiting {retry_after}s")
                time.sleep(retry_after)
                return self._request(url, params)
            else:
                logger.error(f"Discogs API error {resp.status_code}: {resp.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None
    
    def get_user_info(self):
        return self._request(f"{DISCOGS_API}/users/{self.username}")
    
    def get_collection_folders(self):
        return self._request(f"{DISCOGS_API}/users/{self.username}/collection/folders")
    
    def get_collection_items(self, folder_id=0, page=1, per_page=100):
        """folder_id=0 is 'All' folder"""
        return self._request(
            f"{DISCOGS_API}/users/{self.username}/collection/folders/{folder_id}/releases",
            params={'page': page, 'per_page': per_page}
        )
    
    def get_release(self, release_id):
        return self._request(f"{DISCOGS_API}/releases/{release_id}")
    
    def search(self, query, type_='release', page=1, per_page=50):
        return self._request(
            f"{DISCOGS_API}/database/search",
            params={'q': query, 'type': type_, 'page': page, 'per_page': per_page}
        )
    
    def get_artist(self, artist_id):
        return self._request(f"{DISCOGS_API}/artists/{artist_id}")
    
    def get_artist_releases(self, artist_id, page=1, per_page=50):
        return self._request(
            f"{DISCOGS_API}/artists/{artist_id}/releases",
            params={'page': page, 'per_page': per_page}
        )
    
    def get_wantlist(self, page=1, per_page=100):
        """Fetch wantlist items from Discogs"""
        return self._request(
            f"{DISCOGS_API}/users/{self.username}/wants",
            params={'page': page, 'per_page': per_page}
        )
