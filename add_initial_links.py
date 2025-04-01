from app import app, db, Link
from werkzeug.security import generate_password_hash
from models import User

def add_initial_links():
    with app.app_context():
        # Clear existing links
        Link.query.delete()
        
        # Add initial links
        links = [
            {
                'title': 'Twitch',
                'url': 'https://twitch.tv/your_channel',
                'icon': 'M11.571 4.714h1.715v5.143H11.57zm4.715 0H18v5.143h-1.714zM6 0L1.714 4.286v15.428h5.143V24l4.286-4.286h3.428L22.286 12V0zm14.571 11.143l-3.428 3.428h-3.429l-3 3v-3H6.857V1.714h13.714Z'
            },
            {
                'title': 'YouTube',
                'url': 'https://youtube.com/your_channel',
                'icon': 'M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z'
            },
            {
                'title': 'TikTok',
                'url': 'https://tiktok.com/@your_channel',
                'icon': 'M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 5.2-1.74V9.39a8.66 8.66 0 0 0 5.52 2.75V9.39a6.14 6.14 0 0 1-3.77-2.7z'
            },
            {
                'title': 'Gear',
                'url': '/gear',
                'icon': 'M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5'
            }
        ]
        
        for link_data in links:
            link = Link(**link_data)
            db.session.add(link)
        
        db.session.commit()
        print("Initial links added successfully!")

if __name__ == '__main__':
    add_initial_links() 