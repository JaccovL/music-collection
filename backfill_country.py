#!/usr/bin/env python3
"""Backfill country data for all releases from Discogs API"""
import sys
import time
import logging

sys.path.insert(0, '/app')

from app import app
from models import db, Release
from discogs_client import DiscogsClient
from sqlalchemy import func

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

def backfill_country():
    with app.app_context():
        # Get Discogs credentials
        from app import get_setting
        token = get_setting('discogs_token', '') or app.config.get('DISCOGS_TOKEN', '')
        username = get_setting('discogs_username', '') or app.config.get('DISCOGS_USERNAME', '')
        
        if not token or not username:
            logger.error("Discogs credentials not configured")
            return
        
        client = DiscogsClient(token, username)
        
        # Get all releases without country
        releases = Release.query.filter(
            (Release.country.is_(None) | (Release.country == ''))
        ).order_by(Release.id).all()
        
        total = len(releases)
        logger.info(f"Found {total} releases without country data")
        
        updated = 0
        errors = 0
        
        for i, release in enumerate(releases):
            try:
                data = client.get_release(release.discogs_id)
                if data:
                    country = data.get('country')
                    if country:
                        release.country = country
                        db.session.commit()
                        updated += 1
                    else:
                        # Mark as 'Unknown' to avoid re-fetching
                        release.country = 'Unknown'
                        db.session.commit()
                else:
                    errors += 1
                
                if (i + 1) % 50 == 0:
                    logger.info(f"Progress: {i+1}/{total} (updated: {updated}, errors: {errors})")
                    
            except Exception as e:
                logger.error(f"Failed to fetch release {release.discogs_id}: {e}")
                db.session.rollback()
                errors += 1
        
        logger.info(f"Backfill complete: {updated} updated, {errors} errors")

if __name__ == '__main__':
    backfill_country()
