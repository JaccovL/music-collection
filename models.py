from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from zoneinfo import ZoneInfo

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

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=_now)
    last_login = db.Column(db.DateTime)

class Artist(db.Model):
    __tablename__ = 'artists'
    id = db.Column(db.Integer, primary_key=True)
    discogs_id = db.Column(db.Integer, unique=True)
    name = db.Column(db.String(500), nullable=False, index=True)
    profile = db.Column(db.Text)
    image_url = db.Column(db.String(1000))
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)
    
    releases = db.relationship('Release', backref='artist', lazy='dynamic')

class Release(db.Model):
    __tablename__ = 'releases'
    id = db.Column(db.Integer, primary_key=True)
    discogs_id = db.Column(db.Integer, unique=True)
    title = db.Column(db.String(500), nullable=False, index=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'), index=True)
    year = db.Column(db.Integer, index=True)
    format = db.Column(db.String(200))
    format_details = db.Column(db.Text)
    genre = db.Column(db.String(200), index=True)
    style = db.Column(db.String(500))
    label = db.Column(db.String(300), index=True)
    catalog_number = db.Column(db.String(100))
    country = db.Column(db.String(100))
    thumb_url = db.Column(db.String(1000))
    cover_image_url = db.Column(db.String(1000))
    folder_id = db.Column(db.Integer)
    date_added = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)
    
    tracks = db.relationship('Track', backref='release', lazy='dynamic', cascade='all, delete-orphan')

class Track(db.Model):
    __tablename__ = 'tracks'
    id = db.Column(db.Integer, primary_key=True)
    release_id = db.Column(db.Integer, db.ForeignKey('releases.id'), index=True)
    position = db.Column(db.String(20))
    title = db.Column(db.String(500), nullable=False)
    duration = db.Column(db.String(20))

class Wantlist(db.Model):
    __tablename__ = 'wantlist'
    id = db.Column(db.Integer, primary_key=True)
    discogs_id = db.Column(db.Integer, unique=True, nullable=False)
    title = db.Column(db.String(500), nullable=False, index=True)
    artist_name = db.Column(db.String(500), index=True)
    artist_id = db.Column(db.Integer)
    year = db.Column(db.Integer, index=True)
    format = db.Column(db.String(200))
    format_details = db.Column(db.Text)
    genre = db.Column(db.String(200), index=True)
    style = db.Column(db.String(500))
    label = db.Column(db.String(300), index=True)
    catalog_number = db.Column(db.String(100))
    country = db.Column(db.String(100))
    thumb_url = db.Column(db.String(1000))
    cover_image_url = db.Column(db.String(1000))
    notes = db.Column(db.Text)
    date_added = db.Column(db.DateTime)
    rating = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

class UpdateLog(db.Model):
    __tablename__ = 'update_log'
    id = db.Column(db.Integer, primary_key=True)
    sync_type = db.Column(db.String(20), default='collection')  # collection, track
    started_at = db.Column(db.DateTime, default=_now)
    finished_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='running')  # running, success, error, verifying
    releases_added = db.Column(db.Integer, default=0)
    releases_updated = db.Column(db.Integer, default=0)
    artists_added = db.Column(db.Integer, default=0)
    tracks_added = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    triggered_by = db.Column(db.String(20))  # cron, manual
    verification_status = db.Column(db.String(20))  # pending, passed, failed, retrying
    missing_fields = db.Column(db.Text)  # JSON: {"country": 4835, "tracks": 123}

class AppSettings(db.Model):
    __tablename__ = 'app_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)
