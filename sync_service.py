import logging
from datetime import datetime
from models import db, Artist, Release, Track, UpdateLog, Wantlist
from discogs_client import DiscogsClient

logger = logging.getLogger(__name__)


def _update_images(obj, data):
    """Update thumb_url and cover_image_url from Discogs data. Works for Release and Wantlist."""
    obj.thumb_url = data.get('thumb')
    images = data.get('images', [])
    if images:
        for img in images:
            if img.get('type') == 'primary':
                obj.cover_image_url = img.get('uri')
                break
        if not obj.cover_image_url:
            obj.cover_image_url = images[0].get('uri')
    if not obj.cover_image_url and obj.thumb_url:
        obj.cover_image_url = obj.thumb_url


def _update_format(obj, data):
    """Update format and format_details from Discogs formats array."""
    formats = data.get('formats', [])
    if formats:
        obj.format = ', '.join(f.get('name', '') for f in formats)
        descriptions = []
        for f in formats:
            desc = f.get('descriptions', [])
            if desc:
                descriptions.extend(desc)
            qty = f.get('qty', '')
            if qty:
                descriptions.append(f'Qty: {qty}')
        obj.format_details = ', '.join(descriptions) if descriptions else None


class SyncService:
    def __init__(self, token, username):
        self.client = DiscogsClient(token, username)
        self.username = username
    
    def sync_collection(self, triggered_by='manual', fetch_details=False, fetch_country=False):
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
            new_releases = []
            
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
                            if fetch_country:
                                basic = item.get('basic_information', {})
                                release_id = basic.get('id')
                                release = Release.query.filter_by(discogs_id=release_id).first()
                                if release:
                                    new_releases.append(release)
                        elif result == 'updated':
                            total_updated += 1
                    
                    pagination = data.get('pagination', {})
                    if page >= pagination.get('pages', 1):
                        break
                    page += 1
                    db.session.commit()
            
            if fetch_country and new_releases:
                logger.info(f"Fetching country for {len(new_releases)} new releases")
                for release in new_releases:
                    try:
                        self._fetch_release_country(release)
                        db.session.commit()
                    except Exception as e:
                        logger.error(f"Failed to fetch country for {release.discogs_id}: {e}")
                        db.session.rollback()
            
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
            artist = Artist(discogs_id=artist_id, name=artist_name)
            db.session.add(artist)
            db.session.flush()
        
        # Get or create release
        release = Release.query.filter_by(discogs_id=release_id).first()
        if not release:
            release = Release(discogs_id=release_id, title=title, artist_id=artist.id, folder_id=folder_id)
            db.session.add(release)
            is_new = True
        else:
            is_new = False
        
        # Update release fields
        release.title = title
        release.artist_id = artist.id
        release.year = basic.get('year')
        _update_format(release, basic)
        release.style = ', '.join(basic.get('styles', [])) if basic.get('styles') else None
        
        labels = basic.get('labels', [])
        if labels:
            release.label = labels[0].get('name')
            release.catalog_number = labels[0].get('catno')
        
        release.country = basic.get('country')
        _update_images(release, basic)
        
        if date_added:
            try:
                release.date_added = datetime.fromisoformat(date_added.replace('Z', '+00:00'))
            except:
                pass
        
        if fetch_details:
            self._fetch_release_details(release)
        
        return 'added' if is_new else 'updated'
    
    def sync_wantlist(self, triggered_by='manual'):
        """Sync wantlist from Discogs"""
        log = UpdateLog(sync_type='wantlist', status='running', triggered_by=triggered_by)
        db.session.add(log)
        db.session.commit()
        
        try:
            total_added = 0
            total_updated = 0
            new_entries = []
            
            page = 1
            while True:
                data = self.client.get_wantlist(page=page)
                if not data:
                    break
                
                wants = data.get('wants', [])
                if not wants:
                    break
                
                for item in wants:
                    result = self._process_wantlist_item(item)
                    if result == 'added':
                        total_added += 1
                        basic = item.get('basic_information', {})
                        release_id = basic.get('id')
                        entry = Wantlist.query.filter_by(discogs_id=release_id).first()
                        if entry:
                            new_entries.append(entry)
                    elif result == 'updated':
                        total_updated += 1
                
                pagination = data.get('pagination', {})
                if page >= pagination.get('pages', 1):
                    break
                page += 1
                db.session.commit()
            
            if new_entries:
                logger.info(f"Fetching country for {len(new_entries)} new wantlist entries")
                for entry in new_entries:
                    try:
                        self._fetch_release_country(entry)
                        db.session.commit()
                    except Exception as e:
                        logger.error(f"Failed to fetch country for wantlist {entry.discogs_id}: {e}")
                        db.session.rollback()
            
            log.status = 'success'
            log.releases_added = total_added
            log.releases_updated = total_updated
            log.finished_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"Wantlist sync complete: {total_added} added, {total_updated} updated")
            return {'status': 'success', 'added': total_added, 'updated': total_updated}
            
        except Exception as e:
            logger.error(f"Wantlist sync failed: {e}")
            log.status = 'error'
            log.error_message = str(e)
            log.finished_at = datetime.utcnow()
            db.session.commit()
            raise
    
    def _process_wantlist_item(self, item):
        """Process a single wantlist item"""
        basic = item.get('basic_information', {})
        release_id = basic.get('id')
        
        artists_data = basic.get('artists', [])
        artist_name = artists_data[0].get('name', 'Unknown Artist') if artists_data else 'Unknown Artist'
        artist_id = artists_data[0].get('id') if artists_data else None
        date_added = item.get('date_added')
        
        entry = Wantlist.query.filter_by(discogs_id=release_id).first()
        if not entry:
            entry = Wantlist(discogs_id=release_id, title=basic.get('title', 'Unknown'),
                             artist_name=artist_name, artist_id=artist_id)
            db.session.add(entry)
            is_new = True
        else:
            is_new = False
        
        entry.title = basic.get('title', entry.title)
        entry.artist_name = artist_name
        entry.artist_id = artist_id
        entry.year = basic.get('year')
        _update_format(entry, basic)
        entry.style = ', '.join(basic.get('styles', [])) if basic.get('styles') else None
        
        labels = basic.get('labels', [])
        if labels:
            entry.label = labels[0].get('name')
            entry.catalog_number = labels[0].get('catno')
        
        entry.country = basic.get('country')
        _update_images(entry, basic)
        
        if date_added:
            try:
                entry.date_added = datetime.fromisoformat(date_added.replace('Z', '+00:00'))
            except:
                pass
        
        entry.notes = item.get('notes')
        entry.rating = item.get('rating')
        
        return 'added' if is_new else 'updated'
    
    def _fetch_release_country(self, release):
        """Fetch country for a release (lightweight, no tracklist)"""
        data = self.client.get_release(release.discogs_id)
        if data:
            country = data.get('country')
            if country:
                release.country = country
            if not release.cover_image_url:
                _update_images(release, data)
    
    def _fetch_release_details(self, release):
        """Fetch full release details including tracklist"""
        data = self.client.get_release(release.discogs_id)
        if not data:
            return
        
        release.title = data.get('title', release.title)
        
        tracklist = data.get('tracklist', [])
        if tracklist:
            Track.query.filter_by(release_id=release.id).delete()
            for t in tracklist:
                track = Track(release_id=release.id, position=t.get('position', ''),
                              title=t.get('title', ''), duration=t.get('duration', ''))
                db.session.add(track)
        
        _update_images(release, data)
