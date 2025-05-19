import os
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, db

# Create Blueprint for auth routes
auth_bp = Blueprint('auth', __name__)

# Initialize flask-login
login_manager = LoginManager()
# Set the login view (must be done after app initialization)
# login_view will be set in init_auth function

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for flask-login."""
    return User.query.get(int(user_id))

def init_auth(app):
    """Initialize authentication with the main Flask app."""
    login_manager.init_app(app)
    # Now that app is initialized, we can set these properties
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    app.register_blueprint(auth_bp, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page."""
    # If user is already logged in, redirect to home
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    # Handle form submission
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate input
        if not username or not email or not password:
            flash('All fields are required', 'danger')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('auth/register.html')
        
        # Check if username or email already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or email already exists', 'danger')
            return render_template('auth/register.html')
        
        # Create new user with hashed password
        new_user = User()
        new_user.username = username
        new_user.email = email
        new_user.password_hash = generate_password_hash(password)
        new_user.created_at = datetime.utcnow()
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Registration error: {e}")
            flash('An error occurred during registration. Please try again.', 'danger')
    
    # Display registration form for GET requests
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    # If user is already logged in, redirect to home
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    # Handle form submission
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        # Validate input
        if not email or not password:
            flash('Email and password are required', 'danger')
            return render_template('auth/login.html')
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        # Check if user exists and password is correct
        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid email or password', 'danger')
            return render_template('auth/login.html')
        
        # Check if user is active
        if not user.is_active:
            flash('Your account is inactive. Please contact support.', 'danger')
            return render_template('auth/login.html')
        
        # Log in user
        login_user(user, remember=remember)
        flash('Login successful!', 'success')
        
        # Redirect to requested page or default to home
        next_page = request.args.get('next')
        return redirect(next_page or url_for('index'))
    
    # Display login form for GET requests
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Log out user."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page."""
    return render_template('auth/profile.html')

@auth_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """Change user password."""
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Validate input
    if not current_password or not new_password or not confirm_password:
        flash('All fields are required', 'danger')
        return redirect(url_for('auth.profile'))
    
    if new_password != confirm_password:
        flash('New passwords do not match', 'danger')
        return redirect(url_for('auth.profile'))
    
    # Check if current password is correct
    if not check_password_hash(current_user.password_hash, current_password):
        flash('Current password is incorrect', 'danger')
        return redirect(url_for('auth.profile'))
    
    # Update password
    current_user.password_hash = generate_password_hash(new_password)
    
    try:
        db.session.commit()
        flash('Password changed successfully', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f"Password change error: {e}")
        flash('An error occurred. Please try again.', 'danger')
    
    return redirect(url_for('auth.profile'))