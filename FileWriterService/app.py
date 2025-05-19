import os
import logging
import datetime

from flask import Flask, render_template, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import current_user, login_required


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# configure the database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///nepantla.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
# initialize the app with the extension, flask-sqlalchemy >= 3.0.x
db.init_app(app)

# Add template context processor for now() function
@app.context_processor
def inject_now():
    return {'now': datetime.datetime.utcnow}

# Import and initialize authentication
from auth import init_auth

# Initialize authentication with app
init_auth(app)

with app.app_context():
    # Make sure to import the models here or their tables won't be created
    import models  # noqa: F401

    try:
        db.create_all()
        logging.info("Database tables created successfully")
    except Exception as e:
        logging.error(f"Error creating database tables: {e}")


@app.route('/')
def index():
    """Home page route for the Nepantla mental health system."""
    return render_template('index.html')


@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard - requires authentication."""
    return render_template('dashboard.html')


@app.errorhandler(404)
def page_not_found(e):
    """Custom 404 page."""
    return render_template('base.html', error="Page not found"), 404


@app.errorhandler(500)
def server_error(e):
    """Custom 500 page."""
    return render_template('base.html', error="Server error occurred"), 500
