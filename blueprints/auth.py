"""Authentication blueprint — login, logout."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import User
from app_utils import get_setting, get_health_status

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('collection.search'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Username and password required', 'error')
            return render_template('login.html')
        
        ldap_enabled = get_setting('ldap_enabled', 'false') == 'true'
        
        if ldap_enabled:
            status = get_health_status()
            if status.ldap_ok:
                user = _try_ldap_login(username, password)
                if user:
                    return _complete_login(user)
            elif status.ldap_configured:
                if get_setting('local_fallback', 'true') == 'true':
                    flash('LDAP unavailable — local login enabled', 'warning')
                else:
                    flash('LDAP unavailable and local fallback disabled', 'error')
                    return render_template('login.html')
        
        if username == 'admin' and password == current_app.config.get('SECRET_KEY'):
            user = User.query.filter_by(username='admin').first()
            if not user:
                user = User(username='admin', is_admin=True)
                db.session.add(user)
                db.session.commit()
            return _complete_login(user)
        
        flash('Invalid credentials', 'error')
    
    return render_template('login.html')


def _try_ldap_login(username, password):
    """Attempt LDAP authentication."""
    try:
        import ldap
    except ImportError:
        return None
    
    from app_utils import get_setting
    
    host = get_setting('ldap_host', '')
    port = int(get_setting('ldap_port', '389') or '389')
    use_ssl = get_setting('ldap_use_ssl', 'false') == 'true'
    base_dn = get_setting('ldap_base_dn', '')
    
    if not host or not base_dn:
        return None
    
    uri = f"{'ldaps' if use_ssl else 'ldap'}://{host}:{port}"
    
    try:
        conn = ldap.initialize(uri)
        conn.set_option(ldap.OPT_REFERRALS, 0)
        conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 5)
        conn.set_option(ldap.OPT_TIMEOUT, 5)
        if use_ssl:
            conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
        
        bind_dn = get_setting('ldap_bind_dn', '')
        bind_password = get_setting('ldap_bind_password', '')
        if bind_dn and bind_password:
            conn.simple_bind_s(bind_dn, bind_password)
        
        user_filter = get_setting('ldap_user_filter', '(uid={username})')
        result = conn.search_s(base_dn, ldap.SCOPE_SUBTREE, user_filter.format(username=username), ['dn', 'cn', 'mail'])
        
        if not result:
            return None
        
        user_dn = result[0][0]
        user_conn = ldap.initialize(uri)
        user_conn.set_option(ldap.OPT_REFERRALS, 0)
        user_conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 5)
        user_conn.set_option(ldap.OPT_TIMEOUT, 5)
        user_conn.simple_bind_s(user_dn, password)
        
        group_dn = get_setting('ldap_group_dn', '')
        if group_dn:
            group_result = conn.search_s(group_dn, ldap.SCOPE_BASE, f"(member={user_dn})")
            if not group_result:
                return None
        
        is_admin = False
        admin_group_dn = get_setting('ldap_admin_group_dn', '')
        if admin_group_dn:
            admin_result = conn.search_s(admin_group_dn, ldap.SCOPE_BASE, f"(member={user_dn})")
            is_admin = bool(admin_result)
        
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, is_admin=is_admin)
            db.session.add(user)
        else:
            user.is_admin = is_admin
        
        conn.unbind()
        user_conn.unbind()
        return user
        
    except Exception as e:
        import logging
        logging.error(f"LDAP error: {e}")
        return None


def _complete_login(user):
    from app_utils import now_amsterdam
    user.last_login = now_amsterdam()
    db.session.commit()
    login_user(user)
    return redirect(url_for('collection.search'))


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))