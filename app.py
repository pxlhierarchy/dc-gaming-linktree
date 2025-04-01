from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')  # Use environment variable in production
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///linktree.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/gear_images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    links = db.relationship('Link', backref='user', lazy=True)

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

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    """Home page route"""
    return render_template('index.html')

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
    """API endpoint to get all links"""
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
def admin():
    """Admin dashboard route"""
    links = Link.query.order_by(Link.created_at.desc()).all()
    return render_template('admin.html', links=links)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login route"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('admin'))
        flash('Invalid username or password')
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
    title = request.form.get('title')
    url = request.form.get('url')
    icon = request.form.get('icon')
    
    if not title or not url:
        return jsonify({'error': 'Title and URL are required'}), 400
    
    link = Link(
        title=title,
        url=url,
        icon=icon,
        user_id=current_user.id
    )
    db.session.add(link)
    db.session.commit()
    return jsonify({'success': True})

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
    gear_items = Gear.query.all()
    return render_template('admin_gear.html', gear_items=gear_items)

@app.route('/admin/gear/add', methods=['POST'])
@login_required
def add_gear():
    try:
        title = request.form.get('title')
        description = request.form.get('description')
        price = request.form.get('price')
        url = request.form.get('url')
        image = request.files.get('image')

        if not all([title, description, price, url, image]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        # Save image
        filename = secure_filename(image.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        image_path = os.path.join('static', 'gear_images', unique_filename)
        
        # Save to local filesystem
        image.save(os.path.join(app.root_path, image_path))

        new_gear = Gear(
            title=title,
            description=description,
            price=price,
            url=url,
            image=image_path
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
        if 'image' in request.files:
            image = request.files['image']
            if image.filename:
                # Delete old image
                old_image_path = os.path.join(app.root_path, gear.image)
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)

                # Save new image
                filename = secure_filename(image.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_filename = f"{timestamp}_{filename}"
                image_path = os.path.join('static', 'gear_images', unique_filename)
                image.save(os.path.join(app.root_path, image_path))
                gear.image = image_path

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
        
        # Delete image file
        image_path = os.path.join(app.root_path, gear.image)
        if os.path.exists(image_path):
            os.remove(image_path)
        
        db.session.delete(gear)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# Database Initialization
def init_db():
    """Initialize the database and create tables if they don't exist."""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Add clicks column to gear table if it doesn't exist
        try:
            db.session.execute('ALTER TABLE gear ADD COLUMN clicks INTEGER DEFAULT 0')
            db.session.commit()
        except Exception as e:
            # Column might already exist, which is fine
            pass
        
        # Create admin user if not exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                password_hash=generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'admin123'))
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully!")
        
        # Initialize default links if none exist
        if not Link.query.first():
            default_links = [
                Link(title='Gaming Gear', url='/gear', icon='M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5', user_id=admin.id),
                Link(title='YouTube', url='https://youtube.com/@dcgaming', icon='M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z', user_id=admin.id),
                Link(title='TikTok', url='https://tiktok.com/@dcgaming', icon='M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z', user_id=admin.id),
                Link(title='Instagram', icon='M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.012-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z', user_id=admin.id),
                Link(title='Twitter', url='https://twitter.com/dcgaming', icon='M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z', user_id=admin.id)
            ]
            for link in default_links:
                db.session.add(link)
            db.session.commit()
            print("Default links initialized successfully!")
        
        # Initialize default gear items if none exist
        if not Gear.query.first():
            default_gear = [
                Gear(
                    title='Gaming Headset',
                    description='High-quality gaming headset with surround sound',
                    price='$99.99',
                    url='https://amazon.com/gaming-headset',
                    image='headset.jpg'
                ),
                Gear(
                    title='Gaming Mouse',
                    description='Precision gaming mouse with RGB lighting',
                    price='$79.99',
                    url='https://amazon.com/gaming-mouse',
                    image='mouse.jpg'
                ),
                Gear(
                    title='Gaming Keyboard',
                    description='Mechanical gaming keyboard with custom switches',
                    price='$129.99',
                    url='https://amazon.com/gaming-keyboard',
                    image='keyboard.jpg'
                )
            ]
            for gear in default_gear:
                db.session.add(gear)
            db.session.commit()
            print("Default gear items initialized successfully!")
        
        print("Database initialized successfully!")

# Initialize database
init_db()

# For local development
if __name__ == '__main__':
    app.run(debug=True) 