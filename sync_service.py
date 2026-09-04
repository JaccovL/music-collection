#!/usr/bin/env python3
"""sync_service.py — Collection, track, and wantlist sync logic"""

import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import current_app
from sqlalchemy import func

from models import db, Release, Track, Artist, UpdateLog, AppSettings, Wantlist
from discogs_client import DiscogsClient

AMSTERDAM_TZ = ZoneInfo('Europe/Amsterdam')

def _now():
    """Get current time in UTC for storage."""
    return datetime.utcnow()

def utc_to_amsterdam(dt):
    """Convert UTC datetime to Amsterdam timezone for display."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo('UTC'))
    return dt.astimezone(AMSTERDAM_TZ)


# ==================== HELPERS ====================

def _update_images(obj, data):
    """Update image URLs from Discogs data."""
    images = data.get('images', [])
    if images:
        obj.cover_image_url = images[0].get('uri', '')
        if len(images) > 1:
            obj.thumb_url = images[0].get('uri150', images[0].get('uri', ''))


def _update_format(obj, data):
    """Update format from Discogs data."""
    formats = data.get('formats', [])
    if formats:
        format_names = [f.get('name', '') for f in formats]
        obj.format = ', '.join(format_names) if format_names else None
        # Format details (descriptions)
        details = []
        for f in formats:
            desc = f.get('descriptions', [])
            if desc:
                details.extend(desc)
        obj.format_details = ', '.join(details) if details else None


def _sync_tracks_for_releases(releases, client, log_entry=None):
    """Sync tracks for a list of releases. Shared by sync_all, track sync, and cron."""
    total = len(releases)
    if total == 0:
        logger.info("No releases to sync tracks for")
        if log_entry:
            log_entry.status = 'success'
            log_entry.finished_at = _now()
            db.session.commit()
        return
    
    logger.info(f"Syncing tracks for {total} releases")
    for i, release in enumerate(releases):
        try:
            data = client.get_release(release.discogs_id)
            if data:
                tracklist = data.get('tracklist', [])
                if tracklist:
                    Track.query.filter_by(release_id=release.id).delete()
                    db.session.flush()
                    for t in tracklist:
                        track = Track(release_id=release.id, position=t.get('position', ''),
                                      title=t.get('title', ''), duration=t.get('duration', ''))
                        db.session.add(track)
                    db.session.commit()
            if (i+1) % 50 == 0:
                logger.info(f"Track sync: {i+1}/{total}")
        except Exception as e:
            logger.error(f"Failed to fetch tracks for release {release.discogs_id}: {e}")
            db.session.rollback()
    
    logger.info("Track sync complete")
    if log_entry:
        log_entry.status = 'success'
        log_entry.finished_at = _now()
        db.session.commit()


def _verify_sync(log_entry):
    """Verify sync completeness by checking for missing fields. Returns dict of missing counts."""
    from models import Release, Track
    
    missing = {}
    
    # Check country
    no_country = Release.query.filter(
        (Release.country.is_(None)) | (Release.country == '')
    ).count()
    if no_country > 0:
        missing['country'] = no_country
    
    # Check tracks
    no_tracks = Release.query.outerjoin(Track).filter(Track.id == None).count()
    if no_tracks > 0:
        missing['tracks'] = no_tracks
    
    # Check cover images
    no_cover = Release.query.filter(
        (Release.cover_image_url.is_(None)) | (Release.cover_image_url == '')
    ).count()
    if no_cover > 0:
        missing['cover_image'] = no_cover
    
    # Update log entry with verification status
    if missing:
        log_entry.verification_status = 'failed'
        import json
        log_entry.missing_fields = json.dumps(missing)
    else:
        log_entry.verification_status = 'passed'
        log_entry.missing_fields = None
    
    db.session.commit()
    return missing


def _fix_missing_fields(missing, token, username, log_entry=None, release_ids=None):
    """Fix missing fields by fetching from Discogs API."""
    from models import Release, Track
    
    client = DiscogsClient(token, username)
    
    if 'country' in missing:
        if release_ids:
            if not hasattr(_fix_missing_fields, '_duplicate_suppressed'):
                _fix_missing_fields._duplicate_suppressed = True
                logger.info(f"Fixing missing country for {len(release_ids)} recently updated releases")
            releases = Release.query.filter(Release.id.in_(release_ids)).all()
        else:
            logger.info(f"Fixing missing country for {missing['country']} releases")
            releases = Release.query.filter(
                (Release.country.is_(None)) | (Release.country == '')
            ).all()
        
        batch_count = 0
        for release in releases:
            try:
                data = client.get_release(release.discogs_id)
                if data:
                    release.country = data.get('country')
                    producers = data.get('producers', [])
                    if producers:
                        release.producer = ', '.join([p.get('name', '') for p in producers])
                    if not release.cover_image_url:
                        _update_images(release, data)
                    batch_count += 1
                    
                    # Batch commit every 50 releases
                    if batch_count % 50 == 0:
                        db.session.commit()
                        db.session.expire_all()
            except Exception as e:
                logger.error(f"Failed to fix country for {release.discogs_id}: {e}")
                db.session.rollback()
        
        # Final commit for remaining
        db.session.commit()
    
    if 'cover_image' in missing:
        if release_ids:
            logger.info(f"Fixing missing covers for {len(release_ids)} recently updated releases")
            releases = Release.query.filter(Release.id.in_(release_ids)).all()
        else:
            logger.info(f"Fixing missing cover for {missing['cover_image']} releases")
            releases = Release.query.filter(
                (Release.cover_image_url.is_(None)) | (Release.cover_image_url == '')
            ).all()
        
        batch_count = 0
        for release in releases:
            try:
                data = client.get_release(release.discogs_id)
                if data:
                    _update_images(release, data)
                    batch_count += 1
                    
                    # Batch commit every 50 releases
                    if batch_count % 50 == 0:
                        db.session.commit()
            except Exception as e:
                logger.error(f"Failed to fix cover for {release.discogs_id}: {e}")
                db.session.rollback()
        
        # Final commit for remaining
        db.session.commit()
    
    if 'tracks' in missing:
        logger.info(f"Fixing missing tracks for {missing['tracks']} releases")
        releases = Release.query.outerjoin(Track).filter(Track.id == None).all()
        _sync_tracks_for_releases(releases, client, log_entry)


def _check_wantlist_in_collection():
    """
    Check if any wantlist items now exist in the collection.
    Returns list of matching Wantlist items.
    """
    from models import Release, Wantlist
    
    # Get all discogs_ids from collection
    collection_ids = {r.discogs_id for r in Release.query.with_entities(Release.discogs_id).all()}
    
    # Find wantlist items that exist in collection
    acquired = Wantlist.query.filter(Wantlist.discogs_id.in_(collection_ids)).all()
    
    return acquired


# ==================== SYNC SERVICE ====================

class SyncService:
    """Main sync service for collection, tracks, and wantlist."""
    
    def _commit_with_retry(self, max_retries=3):
        """Commit with retry for optimistic locking conflicts."""
        for attempt in range(max_retries):
            try:
                with db.session.no_autoflush:
                    db.session.commit()
                break
            except Exception as commit_err:
                db.session.rollback()
                if '1020' in str(commit_err) and attempt < max_retries - 1:
                    logger.warning(f"Optimistic lock conflict, retrying ({attempt+1}/{max_retries})...")
                    db.session.expire_all()
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise
    
    def __init__(self, token, username):
        self.client = DiscogsClient(token, username)
        self.token = token
        self.username = username
    
    def sync_collection(self, triggered_by='manual', fetch_country=False):
        """Sync the full collection from Discogs."""
        log = UpdateLog(sync_type='collection', status='running', triggered_by=triggered_by)
        db.session.add(log)
        db.session.commit()
        
        try:
            total_added = 0
            total_updated = 0
            artists_added = 0
            updated_release_ids = []  # Track for targeted fix
            
            # Fetch all collection items
            page = 1
            while True:
                data = self.client.get_collection_items(page=page, per_page=100)
                if not data or 'releases' not in data:
                    break
                
                releases = data['releases']
                if not releases:
                    break
                
                for item in releases:
                    basic = item.get('basic_information', {})
                    release_id = basic.get('id')
                    
                    if not release_id:
                        continue
                    
                    # Get or create release
                    release = Release.query.filter_by(discogs_id=release_id).first()
                    is_new = release is None
                    
                    if is_new:
                        release = Release(discogs_id=release_id)
                        db.session.add(release)
                    
                    # Update fields
                    release.title = basic.get('title', release.title)
                    release.year = basic.get('year', release.year)
                    release.style = ', '.join(basic.get('styles', [])) if basic.get('styles') else None
                    release.genre = ', '.join(basic.get('genres', [])) if basic.get('genres') else None
                    _update_format(release, basic)
                    _update_images(release, basic)
                    
                    # Date added
                    date_added = item.get('date_added')
                    if date_added:
                        release.date_added = datetime.fromisoformat(date_added.replace('Z', '+00:00'))
                    
                    # Notes
                    notes = item.get('notes', [])
                    if notes:
                        release.notes = '; '.join([n.get('value', '') for n in notes])
                    
                    # Artist
                    artists_data = basic.get('artists', [])
                    if artists_data:
                        artist_name = artists_data[0].get('name', 'Unknown Artist')
                        artist_id = artists_data[0].get('id')
                        
                        artist = Artist.query.filter_by(discogs_id=artist_id).first()
                        if not artist:
                            artist = Artist(discogs_id=artist_id, name=artist_name)
                            db.session.add(artist)
                            artists_added += 1
                        
                        release.artist_id = artist.id
                    
                    # Label and catalog
                    labels = basic.get('labels', [])
                    if labels:
                        release.label = labels[0].get('name')
                        release.catalog_number = labels[0].get('catno')
                    
                    # Country
                    if fetch_country or is_new:
                        release.country = basic.get('country')
                    # Producer
                    producers = basic.get('producers', [])
                    if producers:
                        release.producer = ', '.join([p.get('name', '') for p in producers])
                    
                    if is_new:
                        total_added += 1
                        updated_release_ids.append(release.id)
                    else:
                        total_updated += 1
                        updated_release_ids.append(release.id)
                
                # Batch commit every 50 releases for performance
                if len(updated_release_ids) % 50 == 0:
                    try:
                        with db.session.no_autoflush:
                            db.session.commit()
                        db.session.expire_all()
                    except Exception as commit_err:
                        db.session.rollback()
                        if '1020' in str(commit_err):
                            logger.warning(f"Batch commit conflict, skipping batch")
                        else:
                            raise
                
                # Commit, skip batch on lock conflict (will be fixed later)
                try:
                    db.session.commit()
                except Exception as commit_err:
                    db.session.rollback()
                    if '1020' in str(commit_err):
                        logger.warning(f"Optimistic lock conflict, skipping batch")
                    else:
                        raise
                
                # Pagination
                pagination = data.get('pagination', {})
                if page >= pagination.get('pages', 1):
                    break
                page += 1
            
            log.status = 'success'
            log.releases_added = total_added
            log.releases_updated = total_updated
            log.artists_added = artists_added
            log.finished_at = _now()
            self._commit_with_retry()
            
            # Post-sync verification
            log.status = 'verifying'
            self._commit_with_retry()
            missing = _verify_sync(log)
            if missing:
                logger.warning(f"Sync verification found missing fields, fixing...")
                _fix_missing_fields(missing, self.token, self.username, log, release_ids=updated_release_ids)
                _verify_sync(log)
            
            # Mark as success after verification passes
            log.status = 'success'
            self._commit_with_retry()
            
            # Phase 4.4: Check if any wantlist items are now in collection
            acquired = _check_wantlist_in_collection()
            if acquired:
                logger.info(f"Wantlist detection: {len(acquired)} items from wantlist now in collection")
            
            logger.info(f"Sync complete: {total_added} added, {total_updated} updated")
            return {
                'status': 'success',
                'releases_added': total_added,
                'releases_updated': total_updated,
                'artists_added': artists_added,
                'wantlist_acquired': len(acquired) if acquired else 0
            }
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            log.status = 'error'
            log.error_message = str(e)
            log.finished_at = _now()
            self._commit_with_retry()
            raise
    
    def sync_wantlist(self, triggered_by='manual'):
        """Sync wantlist from Discogs."""
        log = UpdateLog(sync_type='wantlist', status='running', triggered_by=triggered_by)
        db.session.add(log)
        db.session.commit()
        
        try:
            total_added = 0
            total_updated = 0
            
            page = 1
            while True:
                data = self.client.get_wantlist(page=page)
                if not data or 'wants' not in data:
                    break
                
                wants = data['wants']
                if not wants:
                    break
                
                for item in wants:
                    result = self._process_wantlist_item(item)
                    if result == 'added':
                        total_added += 1
                    elif result == 'updated':
                        total_updated += 1
                
                # Commit with retry for optimistic locking
                for attempt in range(3):
                    try:
                        db.session.commit()
                        break
                    except Exception as commit_err:
                        db.session.rollback()
                        if '1020' in str(commit_err) and attempt < 2:
                            time.sleep(0.3 * (attempt + 1))
                            continue
                        raise
                
                pagination = data.get('pagination', {})
                if page >= pagination.get('pages', 1):
                    break
                page += 1
            
            log.status = 'success'
            log.releases_added = total_added
            log.releases_updated = total_updated
            log.finished_at = _now()
            db.session.commit()
            
            logger.info(f"Wantlist sync complete: {total_added} added, {total_updated} updated")
            return {'status': 'success', 'added': total_added, 'updated': total_updated}
            
        except Exception as e:
            logger.error(f"Wantlist sync failed: {e}")
            log.status = 'error'
            log.error_message = str(e)
            log.finished_at = _now()
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
            entry.date_added = datetime.fromisoformat(date_added.replace('Z', '+00:00'))
        
        return 'added' if is_new else 'updated'


logger = logging.getLogger(__name__)
