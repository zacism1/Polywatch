import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_apscheduler import APScheduler
from .config import Config


db = SQLAlchemy()
scheduler = APScheduler()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    # Ensure instance folder exists for SQLite
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)

    from .routes import main_bp
    app.register_blueprint(main_bp)

    from .cli import register_cli
    register_cli(app)

    if app.config.get("SCHEDULER_ENABLED"):
        scheduler.init_app(app)
        scheduler.start()

        from .tasks import scheduled_weekly_job
        scheduler.add_job(
            id="weekly_scrape",
            func=scheduled_weekly_job,
            trigger="interval",
            days=7,
            replace_existing=True,
        )

    return app
