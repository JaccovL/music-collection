import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'mysql+pymysql://music:music@10.10.0.10:3306/music_collection')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Discogs
    DISCOGS_TOKEN = os.environ.get('DISCOGS_TOKEN', '')
    DISCOGS_USERNAME = os.environ.get('DISCOGS_USERNAME', '')
    
    # LDAP
    LDAP_ENABLED = os.environ.get('LDAP_ENABLED', 'false').lower() == 'true'
    LDAP_HOST = os.environ.get('LDAP_HOST', '')
    LDAP_PORT = int(os.environ.get('LDAP_PORT', '389'))
    LDAP_USE_SSL = os.environ.get('LDAP_USE_SSL', 'false').lower() == 'true'
    LDAP_BASE_DN = os.environ.get('LDAP_BASE_DN', '')
    LDAP_BIND_DN = os.environ.get('LDAP_BIND_DN', '')
    LDAP_BIND_PASSWORD = os.environ.get('LDAP_BIND_PASSWORD', '')
    LDAP_USER_FILTER = os.environ.get('LDAP_USER_FILTER', '(uid={username})')
    LDAP_GROUP_DN = os.environ.get('LDAP_GROUP_DN', '')
    LDAP_ADMIN_GROUP_DN = os.environ.get('LDAP_ADMIN_GROUP_DN', '')
    
    # Update schedule
    UPDATE_INTERVAL_HOURS = int(os.environ.get('UPDATE_INTERVAL_HOURS', '24'))
