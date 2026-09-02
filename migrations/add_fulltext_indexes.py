"""Database migration: Add FULLTEXT indexes for search optimization.

Run this script to add FULLTEXT indexes to the releases and artists tables.
This enables fast full-text search using MATCH ... AGAINST instead of LIKE '%...%'.

Usage:
    python -m migrations.add_fulltext_indexes
"""

import os
import sys
from sqlalchemy import create_engine, text

def add_fulltext_indexes():
    """Add FULLTEXT indexes for search optimization."""
    db_uri = os.environ.get('DATABASE_URL', 'mysql+pymysql://music:DiscoGS2026@10.10.0.10:3306/music_collection')
    engine = create_engine(db_uri)
    
    with engine.connect() as conn:
        # Check if indexes already exist
        result = conn.execute(text("""
            SELECT INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS 
            WHERE TABLE_SCHEMA = 'music_collection' 
            AND INDEX_TYPE = 'FULLTEXT'
        """))
        existing = {row[0] for row in result}
        
        if 'idx_releases_title_fulltext' not in existing:
            print("Adding FULLTEXT index on releases.title...")
            conn.execute(text("ALTER TABLE releases ADD FULLTEXT INDEX idx_releases_title_fulltext (title)"))
            print("  ✓ Done")
        
        if 'idx_releases_label_fulltext' not in existing:
            print("Adding FULLTEXT index on releases.label...")
            conn.execute(text("ALTER TABLE releases ADD FULLTEXT INDEX idx_releases_label_fulltext (label)"))
            print("  ✓ Done")
        
        if 'idx_artists_name_fulltext' not in existing:
            print("Adding FULLTEXT index on artists.name...")
            conn.execute(text("ALTER TABLE artists ADD FULLTEXT INDEX idx_artists_name_fulltext (name)"))
            print("  ✓ Done")
        
        if 'idx_tracks_title_fulltext' not in existing:
            print("Adding FULLTEXT index on tracks.title...")
            conn.execute(text("ALTER TABLE tracks ADD FULLTEXT INDEX idx_tracks_title_fulltext (title)"))
            print("  ✓ Done")
        
        print("\nAll FULLTEXT indexes added successfully!")

if __name__ == '__main__':
    add_fulltext_indexes()
