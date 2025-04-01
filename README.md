# DC Gaming Linktree

A modern, customizable Linktree clone built with Flask and designed for deployment on Vercel.

## Features

- Customizable social media links
- Gaming gear showcase
- Click tracking for links and gear items
- Admin dashboard for managing content
- Responsive design
- SVG icon support

## Local Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/dc-gaming-linktree.git
cd dc-gaming-linktree
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file with the following variables:
```
SECRET_KEY=your-secret-key-here
ADMIN_PASSWORD=your-admin-password
```

5. Run the application:
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Deployment to Vercel

1. Push your code to a GitHub repository

2. Install the Vercel CLI:
```bash
npm install -g vercel
```

3. Deploy to Vercel:
```bash
vercel
```

4. Set up environment variables in the Vercel dashboard:
- `SECRET_KEY`: A secure random string for Flask session encryption
- `ADMIN_PASSWORD`: Password for the admin dashboard
- `DATABASE_URL`: URL for your database (Vercel provides PostgreSQL)

5. Configure your domain in the Vercel dashboard

## Admin Dashboard

Access the admin dashboard at `/admin` with the following credentials:
- Username: admin
- Password: (set in ADMIN_PASSWORD environment variable)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 