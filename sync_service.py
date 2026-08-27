import logging
from datetime import datetime
from models import db, Artist, Release, Track, UpdateLog
from discogs_client import DiscogsClient

logger = logging.getLogger(__name__)

class SyncService:
    def __init__(self, token, username):
        self.client = DiscogsClient(token, username)
        self.username = username
    
    def sync_collection(self, triggered_by='manual', fetch_details=False):
        """Sync all collection items from Discogs"""
        log = UpdateLog(sync_type='collection', status='running', triggered_by=triggered_by)
        db.session.add(log)
        db.session.commit()
        
        try:
            folders_data = self.client.get_collection_folders()
            if not folders_data:
                raise Exception("Failed to fetch collection folders")
            
            folders = folders_data.get('folders', [])
            logger.info(f"Found {len(folders)} folders")
            
            total_added = 0
            total_updated = 0
            artists_added = 0
            
            for folder in folders:
                folder_id = folder['id']
                folder_name = folder['name']
                logger.info(f"Syncing folder: {folder_name} (id={folder_id})")
                
                page = 1
                while True:
                    data = self.client.get_collection_items(folder_id=folder_id, page=page)
                    if not data:
                        break
                    
                    releases = data.get('releases', [])
                    if not releases:
                        break
                    
                    for item in releases:
                        result = self._process_collection_item(item, folder_id, fetch_details=fetch_details)
                        if result == 'added':
                            total_added += 1
                        elif result == 'updated':
                            total_updated += 1
                    
                    pagination = data.get('pagination', {})
                    if page >= pagination.get('pages', 1):
                        break
                    page += 1
                    
                    db.session.commit()
            
            log.status = 'success'
            log.releases_added = total_added
            log.releases_updated = total_updated
            log.artists_added = artists_added
            log.finished_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"Sync complete: {total_added} added, {total_updated} updated")
            return {
                'status': 'success',
                'releases_added': total_added,
                'releases_updated': total_updated,
                'artists_added': artists_added
            }
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            log.status = 'error'
            log.error_message = str(e)
            log.finished_at = datetime.utcnow()
            db.session.commit()
            raise
    
    def _process_collection_item(self, item, folder_id, fetch_details=False):
        """Process a single collection item, return 'added', 'updated', or None"""
        instance_id = item.get('instance_id')
        date_added = item.get('date_added')
        basic = item.get('basic_information', {})
        
        release_id = basic.get('id')
        title = basic.get('title', 'Unknown')
        
        # Parse artist
        artists_data = basic.get('artists', [])
        if not artists_data:
            return None
        
        artist_data = artists_data[0]
        artist_id = artist_data.get('id')
        artist_name = artist_data.get('name', 'Unknown Artist')
        
        # Get or create artist
        artist = Artist.query.filter_by(discogs_id=artist_id).first()
        if not artist:
            artist = Artist(
                discogs_id=artist_id,
                name=artist_name
            )
            db.session.add(artist)
            db.session.flush()
        
        # Get or create release
        release = Release.query.filter_by(discogs_id=release_id).first()
        if not release:
            release = Release(
                discogs_id=release_id,
                title=title,
                artist_id=artist.id,
                folder_id=folder_id
            )
            db.session.add(release)
            is_new = True
        else:
            is_new = False
        
        # Update release fields
        release.title = title
        release.artist_id = artist.id
        release.year = basic.get('year')
        
        # Format info
        formats = basic.get('formats', [])
        if formats:
            release.format = ', '.join(f.get('name', '') for f in formats)
            descriptions = []
            for f in formats:
                desc = f.get('descriptions', [])
                if desc:
                    descriptions.extend(desc)
                qty = f.get('qty', '')
                if qty:
                    descriptions.append(f'Qty: {qty}')
            release.format_details = ', '.join(descriptions) if descriptions else None
        
        # Genre/Style
        release.genre = ', '.join(basic.get('genres', [])) if basic.get('genres') else None
        release.style = ', '.join(basic.get('styles', [])) if basic.get('styles') else None
        
        # Label
        labels = basic.get('labels', [])
        if labels:
            release.label = labels[0].get('name')
            release.catalog_number = labels[0].get('catno')
        
        # Country
        release.country = basic.get('country')
        
        # Images - thumb_url is always available from collection API
        release.thumb_url = basic.get('thumb')
        
        # cover_image_url from images array (may not exist in collection API)
        images = basic.get('images', [])
        if images:
            for img in images:
                if img.get('type') == 'primary':
                    release.cover_image_url = img.get('uri')
                    break
            if not release.cover_image_url:
                release.cover_image_url = images[0].get('uri')
        
        # Fallback: use thumb_url as cover_image_url if no full cover available
        if not release.cover_image_url and release.thumb_url:
            release.cover_image_url = release.thumb_url
        
        # Date added
        if date_added:
            try:
                release.date_added = datetime.fromisoformat(date_added.replace('Z', '+00:00'))
            except:
                pass
        
        # Fetch full release details for tracks (only if requested)
        if fetch_details:
            self._fetch_release_details(release)
        
        return 'added' if is_new else 'updated'
    
    def _fetch_release_details(self, release):
        """Fetch full release details including tracklist"""
        data = self.client.get_release(release.discogs_id)
        if not data:
            return
        
        # Update with full data
        release.title = data.get('title', release.title)
        
        # Tracklist
        tracklist = data.get('tracklist', [])
        if tracklist:
            # Clear existing tracks
            Track.query.filter_by(release_id=release.id).delete()
            
            for t in tracklist:
                track = Track(
                    release_id=release.id,
                    position=t.get('position', ''),
                    title=t.get('title', ''),
                    duration=t.get('duration', '')
                )
                db.session.add(track)
        
        # Update images if better quality available
        images = data.get('images', [])
        if images:
            for img in images:
                if img.get('type') == 'primary':
                    release.cover_image_url = img.get('uri')
                    break
