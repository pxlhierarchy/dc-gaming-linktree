from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required, logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, time, timezone
import logging
import os
import traceback

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv is optional at runtime
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def utcnow():
    """Timezone-aware UTC timestamp (datetime.utcnow() is deprecated)."""
    return datetime.now(timezone.utc)


def utcnow_naive():
    """Naive UTC timestamp, for columns that get compared to a cutoff.

    Aware and naive datetimes raise TypeError when compared, and SQLite and
    Postgres do not agree on which kind they hand back for a plain DateTime
    column. Analytics filters by date range constantly, so ClickEvent keeps
    every value - stored and compared - naive UTC.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Vercel sets VERCEL=1 in every build and runtime environment.
IS_SERVERLESS = bool(os.environ.get('VERCEL'))

app = Flask(__name__)

# Missing config used to raise at import. On serverless that surfaces only as
# FUNCTION_INVOCATION_FAILED with no clue which variable is missing, and the
# reason is buried in logs. Collect the problems instead and let the app boot,
# then refuse every request with a page that names them - the site still fails
# safe (nothing is read or written), but it says why.
MISSING_CONFIG = []

# On Vercel each request may be served by a different instance. A per-process
# random key would sign every session with a different secret, so logins would
# appear to work and then randomly drop.
secret_key = os.environ.get('SECRET_KEY')
if not secret_key:
    if IS_SERVERLESS:
        MISSING_CONFIG.append('SECRET_KEY')
    else:
        logger.warning("SECRET_KEY not set - using a random key for this run only.")
    secret_key = os.urandom(32)
app.config['SECRET_KEY'] = secret_key

# Handle the legacy postgres:// scheme that some providers still hand out.
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

if not database_url and IS_SERVERLESS:
    # Serverless filesystems are read-only and discarded between invocations,
    # so SQLite would silently lose every write.
    MISSING_CONFIG.append('DATABASE_URL')

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///linktree.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max request size

# Flask serves /static itself here, and its default is Cache-Control: no-cache,
# which overrode the header set in vercel.json - every visit re-downloaded the
# ~250KB of artwork. One day, with the CDN allowed to serve stale while
# revalidating. Bump this if an asset ever needs to change faster than that.
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400

# Recycle connections before a serverless pooler drops them underneath us.
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 280,
}

logger.info("Database backend: %s", app.config['SQLALCHEMY_DATABASE_URI'].split(':')[0])

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'


# --------------------------------------------------------------------------
# Database Models
# --------------------------------------------------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    links = db.relationship('Link', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'


class Link(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    icon = db.Column(db.String(1000))
    position = db.Column(db.Integer, default=0)
    # Renders as a solid call-to-action instead of a plain card. Reserved for
    # one link at a time - two "primary" buttons is no emphasis at all.
    highlight = db.Column(db.Boolean, default=False, nullable=False)
    clicks = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'icon': self.icon,
            'position': self.position,
            'highlight': self.highlight,
            'clicks': self.clicks,
        }


class ClickEvent(db.Model):
    """One row per link click, so clicks can be counted over a date range.

    Link.clicks stays as the all-time counter rather than being derived from
    these rows: it holds the totals from before this table existed, and it
    keeps working if a single insert here is ever lost.
    """
    __tablename__ = 'click_event'

    id = db.Column(db.Integer, primary_key=True)
    link_id = db.Column(
        db.Integer,
        db.ForeignKey('link.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    # Naive UTC - see utcnow_naive(). Indexed because every dashboard query
    # filters on it.
    created_at = db.Column(db.DateTime, default=utcnow_naive,
                           nullable=False, index=True)


class Preferences(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    site_title = db.Column(db.String(100), default='DC Gaming')
    site_description = db.Column(db.String(200), default='Your gaming destination')
    profile_image = db.Column(db.String(500))
    background_color = db.Column(db.String(7), default='#0F1A12')
    accent_color = db.Column(db.String(7), default='#F5B921')
    text_color = db.Column(db.String(7), default='#F5F1E3')
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'site_title': self.site_title,
            'site_description': self.site_description,
            'profile_image': self.profile_image,
            'background_color': self.background_color,
            'accent_color': self.accent_color,
            'text_color': self.text_color,
        }


if MISSING_CONFIG:
    logger.error("Missing required configuration: %s", ', '.join(MISSING_CONFIG))

    @app.before_request
    def _refuse_until_configured():
        """Block every request while required configuration is absent."""
        names = ''.join(f'<li><code>{name}</code></li>' for name in MISSING_CONFIG)
        return (
            '<!doctype html><meta charset="utf-8">'
            '<title>Configuration needed</title>'
            '<style>body{font-family:system-ui,sans-serif;background:#0F1A12;'
            'color:#F5F1E3;margin:0;display:grid;place-items:center;min-height:100vh}'
            'main{max-width:34rem;padding:2rem}h1{color:#F5B921}'
            'code{background:#18271A;padding:.15em .4em;border-radius:4px}</style>'
            '<main><h1>Configuration needed</h1>'
            f'<p>This deployment is missing required environment variables:</p><ul>{names}</ul>'
            '<p>Set them in the Vercel project under '
            '<strong>Settings &rarr; Environment Variables</strong>, for the '
            '<strong>Production</strong> environment, then redeploy. Environment '
            'variables are read at build time, so an existing deployment will not '
            'pick them up until it is rebuilt.</p></main>'
        ), 503


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.context_processor
def inject_preferences():
    """Make the site owner's preferences available to every template.

    Public visitors are not logged in, so this reads the first user's
    preferences rather than current_user's.
    """
    try:
        prefs = Preferences.query.order_by(Preferences.id).first()
    except Exception:
        prefs = None
    return {'preferences': prefs, 'now_year': utcnow().year}


# --------------------------------------------------------------------------
# Public Routes
# --------------------------------------------------------------------------
@app.route('/')
def index():
    links = Link.query.order_by(Link.position, Link.created_at.desc()).all()
    return render_template('index.html', links=links)


@app.route('/setup-emulator')
def setup_emulator():
    """How to play Donkey Kong Country on a PC: emulator + ROM."""
    return render_template('setup_emulator.html')


# Crawlers follow plain <a href> links, and a page that is nothing but links is
# exactly what they walk. Counting them turns the dashboard into fiction. A
# substring match will not catch every bot, but it catches the volume.
BOT_UA_MARKERS = (
    'bot', 'crawl', 'spider', 'slurp', 'facebookexternalhit', 'preview',
    'fetch', 'monitor', 'headless', 'curl', 'wget', 'python-requests',
    'scrapy', 'httpclient', 'okhttp', 'go-http-client', 'embed', 'validator',
)


def looks_automated(user_agent):
    """True if this request should not be counted as a human click."""
    ua = (user_agent or '').lower()
    if not ua:
        # Every real browser sends a User-Agent. An empty one is a script.
        return True
    return any(marker in ua for marker in BOT_UA_MARKERS)


@app.route('/track/<int:id>')
def track_click(id):
    """Count a link click and redirect to the target URL."""
    link = db.get_or_404(Link, id)

    if not looks_automated(request.headers.get('User-Agent')):
        try:
            link.clicks = (link.clicks or 0) + 1
            db.session.add(ClickEvent(link_id=link.id))
            db.session.commit()
        except Exception:
            # Sending the visitor onward matters more than the statistic.
            # A failed write must never surface as a 500 on a working link.
            logger.error("Could not record click for link %s: %s",
                         id, traceback.format_exc())
            db.session.rollback()

    return redirect(link.url)


@app.route('/api/links')
def get_links():
    links = Link.query.order_by(Link.position, Link.created_at.desc()).all()
    return jsonify([link.to_dict() for link in links])


@app.route('/healthz')
def healthz():
    return jsonify({'status': 'ok'})


# --------------------------------------------------------------------------
# Auth Routes
# --------------------------------------------------------------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login route"""
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            logger.info("Successful login for %s", username)
            return redirect(url_for('admin_dashboard'))

        logger.warning("Failed login attempt for username: %s", username)
        flash('Invalid username or password', 'danger')

    return render_template('admin_login.html')


@app.route('/admin/logout')
@login_required
def admin_logout():
    """Admin logout route"""
    logout_user()
    return redirect(url_for('index'))


# --------------------------------------------------------------------------
# Admin Routes
# --------------------------------------------------------------------------
@app.route('/admin')
@login_required
def admin_dashboard():
    """Admin dashboard route"""
    links = Link.query.filter_by(user_id=current_user.id) \
                      .order_by(Link.position, Link.created_at.desc()).all()
    return render_template('admin.html', links=links)


# ---- Link management -----------------------------------------------------
@app.route('/admin/links/add', methods=['POST'])
@login_required
def add_link():
    """Add new link route"""
    try:
        title = (request.form.get('title') or '').strip()
        url = (request.form.get('url') or '').strip()
        icon = (request.form.get('icon') or '').strip()

        if not title or not url:
            return jsonify({'success': False, 'message': 'Title and URL are required'}), 400

        existing = Link.query.filter_by(title=title, user_id=current_user.id).first()
        if existing:
            return jsonify({'success': False, 'message': 'A link with this title already exists'}), 400

        next_position = (
            db.session.query(db.func.max(Link.position))
              .filter_by(user_id=current_user.id).scalar() or 0
        ) + 1

        link = Link(title=title, url=url, icon=icon,
                    position=next_position, user_id=current_user.id)
        db.session.add(link)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Link added', 'link': link.to_dict()})
    except Exception as e:
        logger.error("Error adding link: %s", traceback.format_exc())
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error adding link: {e}'}), 500


@app.route('/admin/links/edit/<int:id>', methods=['POST'])
@login_required
def edit_link(id):
    """Edit existing link route"""
    try:
        link = db.get_or_404(Link, id)
        if link.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        title = (request.form.get('title') or '').strip()
        url = (request.form.get('url') or '').strip()
        icon = (request.form.get('icon') or '').strip()

        if not title or not url:
            return jsonify({'success': False, 'message': 'Title and URL are required'}), 400

        link.title, link.url, link.icon = title, url, icon
        db.session.commit()
        return jsonify({'success': True, 'link': link.to_dict()})
    except Exception as e:
        logger.error("Error editing link: %s", traceback.format_exc())
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/admin/links/delete/<int:id>', methods=['POST'])
@login_required
def delete_link(id):
    """Delete link route"""
    try:
        link = db.get_or_404(Link, id)
        if link.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        # SQLite does not enforce ON DELETE CASCADE unless PRAGMA
        # foreign_keys is on, so clear the click history explicitly. On
        # Postgres this is a no-op the constraint would have done anyway.
        ClickEvent.query.filter_by(link_id=link.id).delete(synchronize_session=False)
        db.session.delete(link)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        logger.error("Error deleting link: %s", traceback.format_exc())
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/admin/links/reorder', methods=['POST'])
@login_required
def reorder_links():
    """Persist a new link ordering. Expects {"order": [id, id, ...]}."""
    try:
        order = (request.get_json(silent=True) or {}).get('order', [])
        for position, link_id in enumerate(order):
            link = db.session.get(Link, int(link_id))
            if link and link.user_id == current_user.id:
                link.position = position
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        logger.error("Error reordering links: %s", traceback.format_exc())
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ---- Analytics -----------------------------------------------------------
# Offered ranges, in days. Keep this short - a range picker with eight options
# is a menu, not a control.
CLICK_RANGES = (7, 30, 90)
DEFAULT_CLICK_RANGE = 30


def click_analytics(user_id, days):
    """Everything the analytics dashboard renders, for one owner and range.

    Days are bucketed in Python rather than with SQL date functions:
    strftime(), date_trunc() and CAST-to-date differ across SQLite and
    Postgres, and this site's click volume makes the round trip free.
    """
    links = (Link.query.filter_by(user_id=user_id)
             .order_by(Link.position, Link.created_at.desc()).all())
    link_ids = [link.id for link in links]

    end_day = utcnow_naive().date()
    start_day = end_day - timedelta(days=days - 1)
    # Midnight UTC on the first day, so the range is whole days, not "N * 24h
    # ago" - a partial first day makes the leftmost bar look like a slump.
    cutoff = datetime.combine(start_day, time.min)

    events = []
    last_seen = {}
    tracked_total = 0
    tracking_since = None

    if link_ids:
        events = (db.session.query(ClickEvent.link_id, ClickEvent.created_at)
                  .filter(ClickEvent.link_id.in_(link_ids),
                          ClickEvent.created_at >= cutoff)
                  .all())

        # All-time, so the table can show when each link was last used and the
        # page can say honestly how far back per-day history actually goes.
        for link_id, last, count in (
            db.session.query(ClickEvent.link_id,
                             db.func.max(ClickEvent.created_at),
                             db.func.count(ClickEvent.id))
            .filter(ClickEvent.link_id.in_(link_ids))
            .group_by(ClickEvent.link_id).all()
        ):
            last_seen[link_id] = last
            tracked_total += count

        tracking_since = (db.session.query(db.func.min(ClickEvent.created_at))
                          .filter(ClickEvent.link_id.in_(link_ids)).scalar())

    # Zero-filled day buckets: a day with no clicks is a real zero and has to
    # occupy width on the chart, or the time axis lies.
    buckets = {start_day + timedelta(days=i): 0 for i in range(days)}
    per_link = {link_id: 0 for link_id in link_ids}
    for link_id, created_at in events:
        day = created_at.date()
        # Both counters move together, so the tiles, the chart and the table
        # can never disagree - a row timestamped in the future by clock skew
        # is dropped from all three rather than from only one.
        if day in buckets:
            buckets[day] += 1
            per_link[link_id] = per_link.get(link_id, 0) + 1

    series = [
        {'date': day.isoformat(),
         # Built by hand rather than with strftime: the no-pad day directive
         # is %-d on Linux and %#d on Windows, and this runs on both.
         'label': '{} {}'.format(day.strftime('%b'), day.day),
         'clicks': count}
        for day, count in sorted(buckets.items())
    ]

    total_range = sum(per_link.values())
    rows = [{
        'id': link.id,
        'title': link.title,
        'url': link.url,
        'icon': link.icon or 'fas fa-link',
        'range_clicks': per_link.get(link.id, 0),
        'all_time': link.clicks or 0,
        # Share of the selected range, so the bar and the number agree.
        'share': round(per_link.get(link.id, 0) * 100.0 / total_range, 1) if total_range else 0.0,
        'last_click': last_seen.get(link.id),
    } for link in links]
    rows.sort(key=lambda row: (-row['range_clicks'], -row['all_time'], row['title'].lower()))

    busiest = max(series, key=lambda point: point['clicks']) if series else None
    if busiest and not busiest['clicks']:
        busiest = None

    return {
        'days': days,
        'ranges': CLICK_RANGES,
        'series': series,
        'rows': rows,
        'total_range': total_range,
        'total_all_time': sum(link.clicks or 0 for link in links),
        'daily_average': round(total_range / days, 1) if days else 0.0,
        'busiest': busiest,
        'top_link': next((row for row in rows if row['range_clicks']), None),
        'tracking_since': tracking_since,
        'tracked_total': tracked_total,
        'start_day': start_day,
        'end_day': end_day,
    }


def _requested_range():
    """Read ?days= and clamp it to an offered range."""
    try:
        days = int(request.args.get('days', DEFAULT_CLICK_RANGE))
    except (TypeError, ValueError):
        return DEFAULT_CLICK_RANGE
    return days if days in CLICK_RANGES else DEFAULT_CLICK_RANGE


@app.route('/admin/analytics')
@login_required
def admin_analytics():
    """Click dashboard: totals, clicks per day, and a per-link breakdown."""
    return render_template('admin_analytics.html',
                           stats=click_analytics(current_user.id, _requested_range()))


@app.route('/admin/analytics.json')
@login_required
def admin_analytics_json():
    """The same figures as JSON, for exporting or checking a number by hand."""
    stats = click_analytics(current_user.id, _requested_range())
    return jsonify({
        'days': stats['days'],
        'from': stats['start_day'].isoformat(),
        'to': stats['end_day'].isoformat(),
        'total_in_range': stats['total_range'],
        'total_all_time': stats['total_all_time'],
        'per_day': stats['series'],
        'links': [{
            'id': row['id'],
            'title': row['title'],
            'url': row['url'],
            'clicks_in_range': row['range_clicks'],
            'clicks_all_time': row['all_time'],
            'last_click': row['last_click'].isoformat() + 'Z' if row['last_click'] else None,
        } for row in stats['rows']],
    })


# ---- Preferences ---------------------------------------------------------
@app.route('/admin/preferences', methods=['GET', 'POST'])
@login_required
def preferences():
    if request.method == 'POST':
        try:
            prefs = Preferences.query.filter_by(user_id=current_user.id).first()
            if not prefs:
                prefs = Preferences(user_id=current_user.id)
                db.session.add(prefs)

            data = request.get_json(silent=True) or {}
            prefs.site_title = data.get('site_title', prefs.site_title)
            prefs.site_description = data.get('site_description', prefs.site_description)
            prefs.profile_image = data.get('profile_image', prefs.profile_image)
            prefs.background_color = data.get('background_color', prefs.background_color)
            prefs.accent_color = data.get('accent_color', prefs.accent_color)
            prefs.text_color = data.get('text_color', prefs.text_color)

            db.session.commit()
            return jsonify({'success': True, 'message': 'Preferences updated successfully'})
        except Exception as e:
            logger.error("Error updating preferences: %s", traceback.format_exc())
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500

    prefs = Preferences.query.filter_by(user_id=current_user.id).first()
    return jsonify(prefs.to_dict() if prefs else {})


# --------------------------------------------------------------------------
# Error handlers
# --------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404,
                           message="This page took a wrong warp pipe."), 404


@app.errorhandler(500)
def server_error(e):
    logger.error("500: %s", traceback.format_exc())
    return render_template('error.html', code=500,
                           message="Something broke on our end. Try again."), 500


# --------------------------------------------------------------------------
# Database bootstrap
# --------------------------------------------------------------------------
def init_db():
    """Create tables and seed an admin user, preferences and default links."""
    # The rollback lives inside the app context: outside it, db.session raises
    # "Working outside of application context" and masks the real failure.
    with app.app_context():
        try:
            db.create_all()

            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin_password = os.environ.get('ADMIN_PASSWORD')
                if not admin_password:
                    admin_password = 'admin'
                    logger.warning(
                        "ADMIN_PASSWORD not set - seeding admin with password 'admin'. "
                        "Set ADMIN_PASSWORD before deploying."
                    )
                admin = User(username='admin',
                             password_hash=generate_password_hash(admin_password))
                db.session.add(admin)
                db.session.commit()
                logger.info("Admin user created")

            if not Preferences.query.filter_by(user_id=admin.id).first():
                db.session.add(Preferences(user_id=admin.id))
                db.session.commit()

            if Link.query.filter_by(user_id=admin.id).count() == 0:
                default_links = [
                    Link(title='Set Up Emulator', url='/setup-emulator',
                         icon='fas fa-gamepad', position=1, user_id=admin.id),
                    Link(title='YouTube', url='https://youtube.com/@dcgaming6898',
                         icon='fab fa-youtube', position=2, user_id=admin.id),
                    Link(title='Twitch', url='https://twitch.tv/dcgaming708',
                         icon='fab fa-twitch', position=3, user_id=admin.id),
                ]
                db.session.add_all(default_links)
                db.session.commit()
                logger.info("Default links created")

            return True
        except Exception:
            logger.error("Error initializing database: %s", traceback.format_exc())
            db.session.rollback()
            return False


@app.cli.command('set-admin-password')
def set_admin_password_command():
    """Change the admin password. Reads it from ADMIN_PASSWORD.

        ADMIN_PASSWORD='new-password' flask --app app set-admin-password

    init-db only seeds a password when it creates the user, so this is the way
    to rotate it on a database that already exists.
    """
    new_password = os.environ.get('ADMIN_PASSWORD')
    if not new_password:
        raise SystemExit("Set ADMIN_PASSWORD in the environment first.")
    if len(new_password) < 12:
        raise SystemExit("Use at least 12 characters for a live site.")

    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            raise SystemExit("No admin user found - run init-db first.")
        admin.password_hash = generate_password_hash(new_password)
        db.session.commit()
        print("Admin password updated.")


@app.cli.command('init-db')
def init_db_command():
    """Create tables and seed the admin user. Run once against a new database.

        flask --app app init-db
    """
    if init_db():
        print("Database ready.")
    else:
        raise SystemExit("Database initialization failed - see the log above.")


# Local development bootstraps itself so `flask run` just works. On serverless
# this is skipped: db.create_all() would run reflection queries on every cold
# start, and the schema should be created once, deliberately, via `init-db`.
if not IS_SERVERLESS:
    if not init_db():
        logger.warning("Database initialization failed!")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
