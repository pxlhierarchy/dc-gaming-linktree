"""Set the live link list for the site.

This is the source of truth for what appears on the home page. Edit LINKS,
re-run, and the database is brought in line with it: entries are matched on
title, missing ones added, changed ones updated, and anything not listed here
is removed.

Usage:  venv/Scripts/python.exe set_links.py
"""
from app import app, db, Link, User

# Order here is the order on the page.
# 'highlight': True renders that link as a solid call-to-action. Use it on one
# link at a time - two primary buttons cancel each other out.
LINKS = [
    {
        'title': 'Set Up Emulator',
        'url': '/setup-emulator',
        'icon': 'fas fa-gamepad',
    },
    {
        'title': 'YouTube',
        'url': 'https://youtube.com/@dcgaming6898',
        'icon': 'fab fa-youtube',
    },
    {
        'title': 'Twitch',
        'url': 'https://twitch.tv/dcgaming708',
        'icon': 'fab fa-twitch',
    },
    {
        'title': 'X / Twitter',
        'url': 'https://x.com/isaac708',
        'icon': 'fab fa-x-twitter',
    },
    {
        'title': 'speedrun.com',
        'url': 'https://www.speedrun.com/users/deviantcode',
        'icon': 'fas fa-stopwatch',
    },
    {
        'title': 'DKC Speedrunning Wiki',
        'url': 'https://dkcspeedruns.com/Main_Page',
        'icon': 'fas fa-book',
    },
    {
        'title': 'Donate',
        'url': 'https://www.paypal.com/donate/?hosted_button_id=42YKZUXLBFFQ2',
        'icon': 'fab fa-paypal',
        'highlight': True,
    },
]


def set_links():
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            raise SystemExit("No admin user found - start the app once to seed it.")

        wanted = {item['title'] for item in LINKS}
        existing = {link.title: link for link in Link.query.filter_by(user_id=admin.id).all()}

        # Drop anything no longer in the list (click counts go with it).
        for title, link in existing.items():
            if title not in wanted:
                print(f"  removed  {title}")
                db.session.delete(link)

        for position, item in enumerate(LINKS, start=1):
            link = existing.get(item['title'])
            highlight = item.get('highlight', False)
            if link:
                changed = (link.url != item['url'] or link.icon != item['icon']
                           or link.position != position or link.highlight != highlight)
                link.url = item['url']
                link.icon = item['icon']
                link.position = position
                link.highlight = highlight
                print(f"  {'updated' if changed else 'ok     '}  {item['title']}")
            else:
                db.session.add(Link(position=position, user_id=admin.id,
                                    **{k: v for k, v in item.items() if k != 'highlight'},
                                    highlight=highlight))
                print(f"  added    {item['title']}")

        db.session.commit()
        print(f"\n{Link.query.filter_by(user_id=admin.id).count()} links live.")


if __name__ == '__main__':
    set_links()
