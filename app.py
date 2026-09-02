"""Music Collection web application — entry point."""
from app_factory import create_app
from extensions import db, scheduler

app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)