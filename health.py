"""Health check services for MariaDB and LDAP connectivity."""
import logging
import socket
import time
from datetime import datetime, timedelta
from threading import Lock
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class HealthCache:
    """Thread-safe cache for health check results with TTL."""
    def __init__(self, ttl_seconds=60):
        self._cache = {}
        self._lock = Lock()
        self._ttl = ttl_seconds
    
    def get(self, key):
        with self._lock:
            entry = self._cache.get(key)
            if entry and time.time() - entry['ts'] < self._ttl:
                return entry['value']
            return None
    
    def set(self, key, value):
        with self._lock:
            self._cache[key] = {'value': value, 'ts': time.time()}
    
    def invalidate(self, key=None):
        with self._lock:
            if key:
                self._cache.pop(key, None)
            else:
                self._cache.clear()


# Global health cache instance
_health_cache = HealthCache(ttl_seconds=60)


def check_mariadb(host: str, port: int = 3306, timeout: int = 5) -> Tuple[bool, Optional[str]]:
    """Check if MariaDB server is reachable. Returns (ok, error_msg)."""
    cached = _health_cache.get(f'mariadb:{host}:{port}')
    if cached is not None:
        return cached
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        result = (True, None)
    except (socket.timeout, socket.error, OSError) as e:
        result = (False, f"Cannot connect to MariaDB at {host}:{port}: {e}")
        logger.warning(result[1])
    
    _health_cache.set(f'mariadb:{host}:{port}', result)
    return result


def check_ldap(host: str, port: int = 389, use_ssl: bool = False, timeout: int = 5) -> Tuple[bool, Optional[str]]:
    """Check if LDAP server is reachable. Returns (ok, error_msg)."""
    cached = _health_cache.get(f'ldap:{host}:{port}')
    if cached is not None:
        return cached
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        result = (True, None)
    except (socket.timeout, socket.error, OSError) as e:
        protocol = 'LDAPS' if use_ssl else 'LDAP'
        result = (False, f"Cannot connect to {protocol} at {host}:{port}: {e}")
        logger.warning(result[1])
    
    _health_cache.set(f'ldap:{host}:{port}', result)
    return result


def check_ldap_with_bind(host: str, port: int = 389, use_ssl: bool = False,
                         bind_dn: str = '', bind_password: str = '',
                         timeout: int = 5) -> Tuple[bool, Optional[str]]:
    """Check LDAP with actual bind test. Returns (ok, error_msg)."""
    try:
        import ldap
    except ImportError:
        return (False, "python-ldap not installed")
    
    protocol = 'ldaps' if use_ssl else 'ldap'
    uri = f"{protocol}://{host}:{port}"
    
    try:
        conn = ldap.initialize(uri)
        conn.set_option(ldap.OPT_REFERRALS, 0)
        conn.set_option(ldap.OPT_NETWORK_TIMEOUT, timeout)
        conn.set_option(ldap.OPT_TIMEOUT, timeout)
        
        if use_ssl:
            conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
        
        if bind_dn and bind_password:
            conn.simple_bind_s(bind_dn, bind_password)
        else:
            conn.simple_bind_s()
        
        conn.unbind()
        return (True, None)
    except Exception as e:
        error_msg = str(e)
        if 'SERVER_DOWN' in error_msg or 'Server is down' in error_msg:
            return (False, f"LDAP server down: {host}:{port}")
        elif 'INVALID_CREDENTIALS' in error_msg:
            return (False, "LDAP bind credentials invalid")
        else:
            return (False, f"LDAP error: {e}")


class HealthStatus:
    """Aggregated health status for the application."""
    def __init__(self):
        self.mariadb_ok: bool = True
        self.mariadb_error: Optional[str] = None
        self.ldap_ok: bool = True
        self.ldap_error: Optional[str] = None
        self.ldap_configured: bool = False
        self.local_fallback_enabled: bool = True
        self.last_check: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            'mariadb_ok': self.mariadb_ok,
            'mariadb_error': self.mariadb_error,
            'ldap_ok': self.ldap_ok,
            'ldap_error': self.ldap_error,
            'ldap_configured': self.ldap_configured,
            'local_fallback_enabled': self.local_fallback_enabled,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'healthy': self.mariadb_ok and (not self.ldap_configured or self.ldap_ok)
        }


def run_health_checks(db_host: str = '10.10.0.10', db_port: int = 3306,
                      ldap_enabled: bool = False, ldap_host: str = '',
                      ldap_port: int = 389, ldap_use_ssl: bool = False,
                      ldap_bind_dn: str = '', ldap_bind_password: str = '',
                      local_fallback: bool = True) -> HealthStatus:
    """Run all health checks and return status."""
    status = HealthStatus()
    status.local_fallback_enabled = local_fallback
    status.last_check = datetime.utcnow()
    
    # Check MariaDB
    ok, err = check_mariadb(db_host, db_port)
    status.mariadb_ok = ok
    status.mariadb_error = err
    
    # Check LDAP if configured
    if ldap_enabled and ldap_host:
        status.ldap_configured = True
        ok, err = check_ldap_with_bind(
            ldap_host, ldap_port, ldap_use_ssl,
            ldap_bind_dn, ldap_bind_password
        )
        status.ldap_ok = ok
        status.ldap_error = err
    
    return status
