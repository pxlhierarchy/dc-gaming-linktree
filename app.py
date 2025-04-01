from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Handle Vercel's PostgreSQL URL
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///linktree.db'

# Add logging for database URL (without sensitive info)
print(f"Database URL: {database_url[:20]}..." if database_url else "No database URL found")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

# Database Models
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
    clicks = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Gear(db.Model):
    """Model for gear items."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.String(20), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    image = db.Column(db.String(500), nullable=False)
    clicks = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert gear item to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'price': self.price,
            'url': self.url,
            'image': self.image,
            'clicks': self.clicks,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Preferences(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    site_title = db.Column(db.String(100), default='DC Gaming')
    site_description = db.Column(db.String(200), default='Your gaming destination')
    profile_image = db.Column(db.String(500))
    background_color = db.Column(db.String(7), default='#000000')
    accent_color = db.Column(db.String(7), default='#E50914')
    text_color = db.Column(db.String(7), default='#ffffff')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'site_title': self.site_title,
            'site_description': self.site_description,
            'profile_image': self.profile_image,
            'background_color': self.background_color,
            'accent_color': self.accent_color,
            'text_color': self.text_color
        }

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    links = Link.query.order_by(Link.created_at.desc()).all()
    return render_template('index.html', links=links)

@app.route('/gear')
def gear():
    """Gear recommendations page"""
    gear_items = Gear.query.order_by(Gear.created_at.desc()).all()
    return render_template('gear.html', gear_items=gear_items)

@app.route('/gear/<int:id>/click')
def track_gear_click(id):
    """Track gear item clicks and redirect to purchase URL"""
    gear = Gear.query.get_or_404(id)
    gear.clicks += 1
    db.session.commit()
    return redirect(gear.url)

@app.route('/api/links')
def get_links():
    links = Link.query.order_by(Link.created_at.desc()).all()
    return jsonify([{
        'id': link.id,
        'title': link.title,
        'url': link.url,
        'icon': link.icon,
        'clicks': link.clicks
    } for link in links])

@app.route('/track/<int:id>')
def track_click(id):
    """Track link clicks and redirect to the target URL"""
    link = Link.query.get_or_404(id)
    
    # Special handling for gear page
    if link.url == '/gear':
        return redirect(url_for('gear'))
    
    # Increment click counter
    link.clicks += 1
    db.session.commit()
    
    return redirect(link.url)

# Admin Routes
@app.route('/admin')
@login_required
def admin_dashboard():
    """Admin dashboard route"""
    try:
        print(f"Loading admin dashboard for user {current_user.id}")
        links = Link.query.filter_by(user_id=current_user.id).order_by(Link.created_at.desc()).all()
        print(f"Found {len(links)} links")
        return render_template('admin.html', links=links)
    except Exception as e:
        print(f"Error loading admin dashboard: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        flash('Error loading admin dashboard', 'error')
        return redirect(url_for('index'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login route"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        print(f"Login attempt for username: {username}")
        
        user = User.query.filter_by(username=username).first()
        if user:
            print(f"User found: {user.username}")
            print(f"User ID: {user.id}")
            if check_password_hash(user.password_hash, password):
                print("Password check passed!")
                login_user(user)
                return redirect(url_for('admin_dashboard'))
            else:
                print("Password check failed!")
                print(f"Provided password hash: {generate_password_hash(password)[:20]}...")
                print(f"Stored password hash: {user.password_hash[:20]}...")
        else:
            print("User not found!")
            
        flash('Invalid username or password', 'error')
    return render_template('admin_login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    """Admin logout route"""
    logout_user()
    return redirect(url_for('index'))

# Link Management Routes
@app.route('/admin/links/add', methods=['POST'])
@login_required
def add_link():
    """Add new link route"""
    try:
        print("Attempting to add new link...")
        title = request.form.get('title')
        url = request.form.get('url')
        icon = request.form.get('icon')
        
        print(f"Received data - Title: {title}, URL: {url}, Icon: {icon}")
        print(f"Current user ID: {current_user.id}")
        
        if not title or not url:
            print("Missing required fields")
            return jsonify({'success': False, 'message': 'Title and URL are required'}), 400
        
        # Check if link already exists
        existing_link = Link.query.filter_by(title=title, user_id=current_user.id).first()
        if existing_link:
            print(f"Link with title '{title}' already exists")
            return jsonify({'success': False, 'message': 'A link with this title already exists'}), 400
        
        print(f"Creating new link for user {current_user.id}")
        link = Link(
            title=title,
            url=url,
            icon=icon,
            user_id=current_user.id
        )
        db.session.add(link)
        db.session.commit()
        print(f"Link created successfully with ID: {link.id}")
        
        # Verify the link was created
        created_link = Link.query.get(link.id)
        if created_link:
            print(f"Verified link exists in database with ID: {created_link.id}")
            return jsonify({
                'success': True, 
                'message': 'Link added successfully',
                'link': {
                    'id': created_link.id,
                    'title': created_link.title,
                    'url': created_link.url,
                    'icon': created_link.icon
                }
            })
        else:
            print("Link was not found after creation!")
            return jsonify({'success': False, 'message': 'Link was not created properly'}), 500
            
    except Exception as e:
        print(f"Error adding link: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error adding link: {str(e)}'}), 500

@app.route('/admin/links/edit/<int:id>', methods=['POST'])
@login_required
def edit_link(id):
    """Edit existing link route"""
    link = Link.query.get_or_404(id)
    if link.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    title = request.form.get('title')
    url = request.form.get('url')
    icon = request.form.get('icon')
    
    if not title or not url:
        return jsonify({'error': 'Title and URL are required'}), 400
    
    link.title = title
    link.url = url
    link.icon = icon
    db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/links/delete/<int:id>', methods=['POST'])
@login_required
def delete_link(id):
    """Delete link route"""
    link = Link.query.get_or_404(id)
    if link.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(link)
    db.session.commit()
    return jsonify({'success': True})

# Gear Management Routes
@app.route('/admin/gear')
@login_required
def admin_gear():
    """Admin gear management page"""
    try:
        print("Loading gear management page...")
        gear_items = Gear.query.all()
        print(f"Found {len(gear_items)} gear items")
        return render_template('admin_gear.html', gear_items=gear_items)
    except Exception as e:
        print(f"Error loading gear management page: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return render_template('admin_gear.html', error=str(e))

@app.route('/admin/gear/add', methods=['POST'])
@login_required
def add_gear():
    try:
        title = request.form.get('title')
        description = request.form.get('description')
        price = request.form.get('price')
        url = request.form.get('url')
        image_url = request.form.get('image_url')  # Changed from file upload to URL

        if not all([title, description, price, url, image_url]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        new_gear = Gear(
            title=title,
            description=description,
            price=price,
            url=url,
            image=image_url  # Store the URL directly
        )
        db.session.add(new_gear)
        db.session.commit()

        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/gear/edit/<int:id>', methods=['POST'])
@login_required
def edit_gear(id):
    try:
        gear = Gear.query.get_or_404(id)
        
        gear.title = request.form.get('title', gear.title)
        gear.description = request.form.get('description', gear.description)
        gear.price = request.form.get('price', gear.price)
        gear.url = request.form.get('url', gear.url)

        # Handle image update if provided
        image_url = request.form.get('image_url')
        if image_url:
            gear.image = image_url

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/gear/delete/<int:id>', methods=['POST'])
@login_required
def delete_gear(id):
    try:
        gear = Gear.query.get_or_404(id)
        db.session.delete(gear)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/gear/<int:id>')
@login_required
def get_gear(id):
    """Get gear details for editing"""
    try:
        print(f"Fetching gear details for ID: {id}")
        gear = Gear.query.get_or_404(id)
        print(f"Found gear: {gear.title}")
        return jsonify(gear.to_dict())
    except Exception as e:
        print(f"Error fetching gear details: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'message': f'Error fetching gear details: {str(e)}'}), 500

# Debug route - REMOVE AFTER DEBUGGING
@app.route('/debug/db')
def debug_db():
    """Debug route to check database state"""
    try:
        print("Checking database state...")
        print(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI'][:20]}...")
        
        # Check if tables exist
        print("Checking if tables exist...")
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Found tables: {tables}")
        
        # Check admin user
        print("Checking for admin user...")
        admin = User.query.filter_by(username='admin').first()
        
        # Check environment variables
        admin_password = os.environ.get('ADMIN_PASSWORD')
        has_admin_password = bool(admin_password)
        
        if admin:
            print(f"Admin user found with ID: {admin.id}")
            return jsonify({
                'admin_exists': True,
                'admin_id': admin.id,
                'admin_username': admin.username,
                'admin_password_hash': admin.password_hash[:20] + '...',
                'tables': tables,
                'has_admin_password': has_admin_password
            })
        else:
            print("Admin user not found")
            # Try to create admin user if it doesn't exist
            try:
                print("Attempting to create admin user...")
                if not admin_password:
                    print("WARNING: ADMIN_PASSWORD environment variable not set!")
                    admin_password = 'admin123'  # Default password
                
                admin = User(
                    username='admin',
                    password_hash=generate_password_hash(admin_password)
                )
                db.session.add(admin)
                db.session.commit()
                print("Admin user created successfully!")
                
                return jsonify({
                    'admin_exists': True,
                    'admin_id': admin.id,
                    'admin_username': admin.username,
                    'admin_password_hash': admin.password_hash[:20] + '...',
                    'tables': tables,
                    'has_admin_password': has_admin_password,
                    'message': 'Admin user was just created'
                })
            except Exception as e:
                print(f"Error creating admin user: {str(e)}")
                db.session.rollback()
                return jsonify({
                    'admin_exists': False,
                    'message': 'Admin user not found and could not be created',
                    'error': str(e),
                    'tables': tables,
                    'has_admin_password': has_admin_password
                })
    except Exception as e:
        print(f"Error in debug route: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        })

def init_db():
    """Initialize the database"""
    try:
        print("Starting database initialization...")
        print(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI'][:20]}...")
        
        # Create all tables
        with app.app_context():
            db.create_all()
            print("Database tables created successfully")
            
            # Check if admin user exists
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                print("Creating admin user...")
                admin = User(
                    username='admin',
                    password_hash=generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'admin'))
                )
                db.session.add(admin)
                db.session.commit()
                print("Admin user created successfully")
            else:
                print("Admin user already exists")
            
            # Check if preferences exist
            preferences = Preferences.query.filter_by(user_id=admin.id).first()
            if not preferences:
                print("Creating default preferences...")
                preferences = Preferences(user_id=admin.id)
                db.session.add(preferences)
                db.session.commit()
                print("Default preferences created successfully")
            else:
                print("Preferences already exist")
            
            # Check if default links exist
            existing_links = Link.query.filter_by(user_id=admin.id).count()
            if existing_links == 0:
                print("Creating default links...")
                default_links = [
                    Link(title='Gear Recommendations', url=url_for('gear', _external=True), icon='fas fa-gamepad', user_id=admin.id),
                    Link(title='YouTube', url='https://youtube.com/@dcgaming', icon='fab fa-youtube', user_id=admin.id),
                    Link(title='Twitch', url='https://twitch.tv/dcgaming', icon='fab fa-twitch', user_id=admin.id),
                    Link(title='Twitter', url='https://twitter.com/dcgaming', icon='fab fa-twitter', user_id=admin.id)
                ]
                for link in default_links:
                    db.session.add(link)
                db.session.commit()
                print("Default links created successfully")
            else:
                print("Links already exist in database")
        
        return True
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        print("Traceback:", traceback.format_exc())
        db.session.rollback()
        return False

# Initialize database when the application starts
with app.app_context():
    print("Initializing database...")
    success = init_db()
    if not success:
        print("WARNING: Database initialization failed!")

# For local development
if __name__ == '__main__':
    app.run(debug=True) 

@app.route('/admin/preferences', methods=['GET', 'POST'])
@login_required
def preferences():
    if request.method == 'POST':
        try:
            preferences = Preferences.query.filter_by(user_id=current_user.id).first()
            if not preferences:
                preferences = Preferences(user_id=current_user.id)
                db.session.add(preferences)

            data = request.get_json()
            preferences.site_title = data.get('site_title', preferences.site_title)
            preferences.site_description = data.get('site_description', preferences.site_description)
            preferences.profile_image = data.get('profile_image', preferences.profile_image)
            preferences.background_color = data.get('background_color', preferences.background_color)
            preferences.accent_color = data.get('accent_color', preferences.accent_color)
            preferences.text_color = data.get('text_color', preferences.text_color)

            db.session.commit()
            return jsonify({'success': True, 'message': 'Preferences updated successfully'})
        except Exception as e:
            print(f"Error updating preferences: {str(e)}")
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Error updating preferences'})

    preferences = Preferences.query.filter_by(user_id=current_user.id).first()
    return jsonify(preferences.to_dict() if preferences else {}) 

@app.context_processor
def inject_preferences():
    if current_user.is_authenticated:
        preferences = Preferences.query.filter_by(user_id=current_user.id).first()
        return {'preferences': preferences}
    return {'preferences': None} 