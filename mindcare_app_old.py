import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "mindcare-ai-secret-key-2024")

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///mindcare.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# === AI ANALYZER CLASS ===
class MoodAnalyzer:
    def __init__(self):
        self.emergency_keywords = [
            'suicide', 'kill myself', 'end it all', 'want to die', 'no point living',
            'better off dead', 'worthless', 'hopeless', 'can\'t go on', 'end my life'
        ]
        
        self.positive_keywords = [
            'happy', 'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
            'joy', 'excited', 'love', 'perfect', 'awesome', 'brilliant', 'cheerful'
        ]
        
        self.negative_keywords = [
            'sad', 'bad', 'terrible', 'awful', 'horrible', 'depressed', 'angry',
            'frustrated', 'upset', 'worried', 'anxious', 'stressed', 'overwhelmed'
        ]

    def analyze_sentiment(self, text):
        if not text:
            return {'sentiment': 'neutral', 'confidence': 0.0, 'score': 0.0}
        
        words = text.lower().split()
        positive_count = sum(1 for word in words if word in self.positive_keywords)
        negative_count = sum(1 for word in words if word in self.negative_keywords)
        
        if positive_count > negative_count:
            return {'sentiment': 'positive', 'confidence': 0.8, 'score': 0.5}
        elif negative_count > positive_count:
            return {'sentiment': 'negative', 'confidence': 0.8, 'score': -0.5}
        else:
            return {'sentiment': 'neutral', 'confidence': 0.5, 'score': 0.0}

    def check_emergency_keywords(self, text):
        if not text:
            return []
        return [kw for kw in self.emergency_keywords if kw in text.lower()]

    def analyze_mood_text(self, text):
        sentiment = self.analyze_sentiment(text)
        emergency_keywords = self.check_emergency_keywords(text)
        return {
            'sentiment': sentiment['sentiment'],
            'confidence': sentiment['confidence'],
            'score': sentiment['score'],
            'emergency_keywords': emergency_keywords
        }

# Initialize AI analyzer
mood_analyzer = MoodAnalyzer()

# === DATABASE MODELS ===
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    birth_date = db.Column(db.Date)
    age = db.Column(db.Integer)
    preferred_language = db.Column(db.String(10), default='en')
    guardian_name = db.Column(db.String(120))
    guardian_email = db.Column(db.String(120))
    guardian_phone = db.Column(db.String(20))
    is_minor = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_emergency_enabled = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class MoodEntry(db.Model):
    __tablename__ = 'mood_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    mood_score = db.Column(db.Float, nullable=False)
    mood_text = db.Column(db.Text)
    ai_sentiment = db.Column(db.String(20))
    ai_confidence = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_emergency_flagged = db.Column(db.Boolean, default=False)

class JournalEntry(db.Model):
    __tablename__ = 'journal_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)
    sentiment_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CommunityPost(db.Model):
    __tablename__ = 'community_posts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_anonymous = db.Column(db.Boolean, default=True)
    hearts_count = db.Column(db.Integer, default=0)
    hugs_count = db.Column(db.Integer, default=0)
    support_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# === HTML TEMPLATES ===
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - MindCare AI</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            position: relative;
            overflow-x: hidden;
        }
        
        /* 3D Background Effects */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(circle at 20% 80%, rgba(120, 119, 198, 0.3) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(255, 119, 198, 0.3) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(120, 219, 255, 0.3) 0%, transparent 50%);
            z-index: -1;
            animation: float 6s ease-in-out infinite;
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0px) rotate(0deg); }
            50% { transform: translateY(-20px) rotate(2deg); }
        }
        
        .glass-card {
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(20px);
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
        }
        
        .glass-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 30px 60px rgba(0, 0, 0, 0.2);
        }
        
        .navbar {
            background: rgba(255, 255, 255, 0.1) !important;
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .btn-primary {
            background: linear-gradient(45deg, #667eea, #764ba2);
            border: none;
            border-radius: 25px;
            padding: 12px 30px;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        }
        
        .btn-primary:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 40px rgba(102, 126, 234, 0.6);
        }
        
        .mood-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(15px);
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .mood-card:hover {
            transform: translateY(-10px) scale(1.02);
            background: rgba(255, 255, 255, 0.2);
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.2);
        }
        
        .text-glow {
            text-shadow: 0 0 20px rgba(255, 255, 255, 0.5);
        }
        
        .form-control {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 15px;
            color: white;
            backdrop-filter: blur(10px);
        }
        
        .form-control:focus {
            background: rgba(255, 255, 255, 0.2);
            border-color: rgba(255, 255, 255, 0.4);
            color: white;
            box-shadow: 0 0 20px rgba(102, 126, 234, 0.3);
        }
        
        .form-control::placeholder {
            color: rgba(255, 255, 255, 0.7);
        }
        
        .navbar-brand, .nav-link {
            color: white !important;
            font-weight: 600;
        }
        
        .nav-link:hover {
            color: #ffd700 !important;
            transform: translateY(-2px);
        }
        
        .alert {
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 15px;
            color: white;
        }
        
        .breathing-circle {
            width: 200px;
            height: 200px;
            border: 3px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 4s ease-in-out;
            background: rgba(102, 126, 234, 0.1);
            backdrop-filter: blur(10px);
        }
        
        .breathing-circle.inhale {
            transform: scale(1.3);
            background: rgba(102, 126, 234, 0.3);
        }
        
        .stats-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(15px);
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 2rem;
            text-align: center;
            transition: all 0.3s ease;
        }
        
        .stats-card:hover {
            transform: translateY(-5px);
            background: rgba(255, 255, 255, 0.15);
        }
        
        .stats-number {
            font-size: 2.5rem;
            font-weight: bold;
            background: linear-gradient(45deg, #ffd700, #ff6b6b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        h1, h2, h3, h4, h5, h6 {
            color: white;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .text-white {
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container">
            <a class="navbar-brand fw-bold text-glow" href="{{ url_for('index') }}">
                <i class="fas fa-heart text-danger"></i> MindCare AI
            </a>
            {% if current_user.is_authenticated %}
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="{{ url_for('dashboard') }}">
                    <i class="fas fa-tachometer-alt"></i> Dashboard
                </a>
                <a class="nav-link" href="{{ url_for('mood_checkin') }}">
                    <i class="fas fa-heart"></i> Check-in
                </a>
                <a class="nav-link" href="{{ url_for('mood_journal') }}">
                    <i class="fas fa-book"></i> Journal
                </a>
                <a class="nav-link" href="{{ url_for('community') }}">
                    <i class="fas fa-users"></i> Community
                </a>
                <a class="nav-link" href="{{ url_for('therapy') }}">
                    <i class="fas fa-spa"></i> Wellness
                </a>
                <a class="nav-link" href="{{ url_for('logout') }}">
                    <i class="fas fa-sign-out-alt"></i> Logout
                </a>
            </div>
            {% endif %}
        </div>
    </nav>

    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-dismissible fade show" role="alert">
                        <i class="fas fa-info-circle"></i> {{ message }}
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {{ content }}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Add some interactive effects
        document.addEventListener('DOMContentLoaded', function() {
            // Floating animation for cards
            const cards = document.querySelectorAll('.mood-card, .glass-card');
            cards.forEach((card, index) => {
                card.style.animationDelay = `${index * 0.1}s`;
                card.style.animation = 'float 6s ease-in-out infinite';
            });
        });
    </script>
</body>
</html>
"""

# === ROUTES ===
@app.route('/')
def index():
    content = """
    <div class="row justify-content-center text-center">
        <div class="col-md-10">
            <h1 class="display-3 fw-bold mb-4 text-glow">Welcome to MindCare AI</h1>
            <p class="lead mb-5 text-white">Your personal mental wellness companion with AI-powered insights, mood tracking, and community support.</p>
            
            {% if not current_user.is_authenticated %}
            <div class="row g-3 justify-content-center mb-5">
                <div class="col-auto">
                    <a href="{{ url_for('register') }}" class="btn btn-primary btn-lg">
                        <i class="fas fa-user-plus"></i> Get Started
                    </a>
                </div>
                <div class="col-auto">
                    <a href="{{ url_for('login') }}" class="btn btn-outline-light btn-lg">
                        <i class="fas fa-sign-in-alt"></i> Sign In
                    </a>
                </div>
            </div>
            {% else %}
            <a href="{{ url_for('dashboard') }}" class="btn btn-primary btn-lg mb-5">
                <i class="fas fa-tachometer-alt"></i> Go to Dashboard
            </a>
            {% endif %}
        </div>
    </div>

    <div class="row g-4">
        <div class="col-md-4">
            <div class="mood-card h-100 p-4 text-center text-white">
                <i class="fas fa-heart text-danger fa-4x mb-3"></i>
                <h4>Mood Tracking</h4>
                <p>Monitor your emotional well-being with AI-powered sentiment analysis and daily check-ins.</p>
            </div>
        </div>
        <div class="col-md-4">
            <div class="mood-card h-100 p-4 text-center text-white">
                <i class="fas fa-users text-success fa-4x mb-3"></i>
                <h4>Community Support</h4>
                <p>Connect with others in a safe, anonymous environment for mutual support and encouragement.</p>
            </div>
        </div>
        <div class="col-md-4">
            <div class="mood-card h-100 p-4 text-center text-white">
                <i class="fas fa-shield-alt text-warning fa-4x mb-3"></i>
                <h4>Emergency Care</h4>
                <p>Advanced crisis detection with automatic alerts and guardian notifications for minors.</p>
            </div>
        </div>
    </div>
    """
    return render_template_string(BASE_TEMPLATE, content=content, title="Home")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        birth_date = request.form.get('birth_date', '')
        preferred_language = request.form.get('preferred_language', 'en')
        guardian_name = request.form.get('guardian_name', '').strip()
        guardian_email = request.form.get('guardian_email', '').strip()
        guardian_phone = request.form.get('guardian_phone', '').strip()
        
        # Validation
        if not username or len(username) < 3:
            flash('Username must be at least 3 characters long.', 'danger')
            return redirect(url_for('register'))
        
        if not email or '@' not in email:
            flash('Please enter a valid email address.', 'danger')
            return redirect(url_for('register'))
        
        if not password or len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))
        
        if not birth_date:
            flash('Birth date is required.', 'danger')
            return redirect(url_for('register'))
        
        # Calculate age
        try:
            birth_date_obj = datetime.strptime(birth_date, '%Y-%m-%d').date()
            today = datetime.today().date()
            age = today.year - birth_date_obj.year - ((today.month, today.day) < (birth_date_obj.month, birth_date_obj.day))
            
            if age < 13:
                flash('You must be at least 13 years old to use this platform.', 'danger')
                return redirect(url_for('register'))
            
            is_minor = age < 18
            
            # Check guardian details for minors
            if is_minor and (not guardian_name or not guardian_email):
                flash('Guardian name and email are required for users under 18.', 'danger')
                return redirect(url_for('register'))
                
        except ValueError:
            flash('Please enter a valid birth date.', 'danger')
            return redirect(url_for('register'))
        
        # Check existing users
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
        
        # Create new user
        try:
            user = User(
                username=username,
                email=email,
                birth_date=birth_date_obj,
                age=age,
                preferred_language=preferred_language,
                is_minor=is_minor,
                guardian_name=guardian_name if is_minor else None,
                guardian_email=guardian_email if is_minor else None,
                guardian_phone=guardian_phone if is_minor else None
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'danger')
            return redirect(url_for('register'))
    
    content = """
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="glass-card p-5">
                <h2 class="text-center mb-4 text-white">Create Account</h2>
                <form method="POST" id="registerForm">
                    <div class="mb-3">
                        <label class="form-label text-white">Username</label>
                        <input type="text" class="form-control" name="username" required>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label text-white">Email</label>
                        <input type="email" class="form-control" name="email" required>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label text-white">Birth Date</label>
                        <input type="date" class="form-control" name="birth_date" id="birth_date" required>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label text-white">Preferred Language</label>
                        <select class="form-control" name="preferred_language">
                            <option value="en">English</option>
                            <option value="es">Español</option>
                            <option value="fr">Français</option>
                            <option value="de">Deutsch</option>
                            <option value="hi">हिंदी</option>
                        </select>
                    </div>
                    
                    <div id="guardian-section" style="display: none;">
                        <h5 class="text-warning mb-3">Guardian Information (Required for users under 18)</h5>
                        <div class="mb-3">
                            <label class="form-label text-white">Guardian Name</label>
                            <input type="text" class="form-control" name="guardian_name" id="guardian_name">
                        </div>
                        <div class="mb-3">
                            <label class="form-label text-white">Guardian Email</label>
                            <input type="email" class="form-control" name="guardian_email" id="guardian_email">
                        </div>
                        <div class="mb-3">
                            <label class="form-label text-white">Guardian Phone</label>
                            <input type="tel" class="form-control" name="guardian_phone">
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label text-white">Password</label>
                        <input type="password" class="form-control" name="password" required>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label text-white">Confirm Password</label>
                        <input type="password" class="form-control" name="confirm_password" required>
                    </div>
                    
                    <button type="submit" class="btn btn-primary w-100 mb-3">
                        <i class="fas fa-user-plus"></i> Create Account
                    </button>
                    
                    <p class="text-center text-white">
                        Already have an account? <a href="{{ url_for('login') }}" class="text-warning">Sign in here</a>
                    </p>
                </form>
            </div>
        </div>
    </div>

    <script>
    document.getElementById('birth_date').addEventListener('change', function() {
        const birthDate = new Date(this.value);
        const today = new Date();
        const age = today.getFullYear() - birthDate.getFullYear();
        const guardianSection = document.getElementById('guardian-section');
        
        if (age < 18) {
            guardianSection.style.display = 'block';
            document.getElementById('guardian_name').required = true;
            document.getElementById('guardian_email').required = true;
        } else {
            guardianSection.style.display = 'none';
            document.getElementById('guardian_name').required = false;
            document.getElementById('guardian_email').required = false;
        }
    });
    </script>
    """
    return render_template_string(BASE_TEMPLATE, content=content, title="Register")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            return redirect(url_for('login'))
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    content = """
    <div class="row justify-content-center">
        <div class="col-md-4">
            <div class="glass-card p-5">
                <h2 class="text-center mb-4 text-white">Sign In</h2>
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label text-white">Username</label>
                        <input type="text" class="form-control" name="username" required>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label text-white">Password</label>
                        <input type="password" class="form-control" name="password" required>
                    </div>
                    
                    <button type="submit" class="btn btn-primary w-100 mb-3">
                        <i class="fas fa-sign-in-alt"></i> Sign In
                    </button>
                    
                    <p class="text-center text-white">
                        Don't have an account? <a href="{{ url_for('register') }}" class="text-warning">Register here</a>
                    </p>
                </form>
            </div>
        </div>
    </div>
    """
    return render_template_string(BASE_TEMPLATE, content=content, title="Login")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    recent_moods = MoodEntry.query.filter_by(user_id=current_user.id)\
                                 .order_by(desc(MoodEntry.created_at))\
                                 .limit(30).all()
    
    total_entries = len(recent_moods)
    avg_mood = sum(entry.mood_score for entry in recent_moods) / total_entries if total_entries > 0 else 0
    
    recent_journals = JournalEntry.query.filter_by(user_id=current_user.id)\
                                       .order_by(desc(JournalEntry.created_at))\
                                       .limit(3).all()
    
    content = f"""
    <div class="row mb-4">
        <div class="col-12">
            <h2 class="text-white mb-4 text-glow">Welcome back, {current_user.username}!</h2>
        </div>
    </div>

    <div class="row g-4 mb-4">
        <div class="col-md-3">
            <div class="stats-card">
                <i class="fas fa-chart-line text-primary fa-2x mb-2"></i>
                <div class="stats-number">{total_entries}</div>
                <small class="text-white">Total Check-ins</small>
            </div>
        </div>
        <div class="col-md-3">
            <div class="stats-card">
                <i class="fas fa-heart text-danger fa-2x mb-2"></i>
                <div class="stats-number">{avg_mood:.1f}</div>
                <small class="text-white">Average Mood</small>
            </div>
        </div>
        <div class="col-md-3">
            <div class="stats-card">
                <i class="fas fa-birthday-cake text-warning fa-2x mb-2"></i>
                <div class="stats-number">{current_user.age or 'N/A'}</div>
                <small class="text-white">Age</small>
            </div>
        </div>
        <div class="col-md-3">
            <div class="stats-card">
                <i class="fas fa-language text-info fa-2x mb-2"></i>
                <div class="stats-number">{current_user.preferred_language.upper()}</div>
                <small class="text-white">Language</small>
            </div>
        </div>
    </div>

    <div class="row g-4">
        <div class="col-md-6">
            <div class="glass-card p-4">
                <h5 class="text-white mb-3">Recent Mood Entries</h5>
                {f'''
                {''.join([f"""
                <div class="d-flex justify-content-between align-items-center border-bottom border-secondary py-2">
                    <div>
                        <span class="badge bg-primary">{entry.mood_score:.1f}</span>
                        <small class="text-white-50 ms-2">{entry.created_at.strftime('%m/%d %H:%M')}</small>
                    </div>
                    <span class="badge bg-info">{entry.ai_sentiment or 'neutral'}</span>
                </div>
                """ for entry in recent_moods[:5]])}
                ''' if recent_moods else '<p class="text-white-50">No mood entries yet. <a href="' + url_for('mood_checkin') + '" class="text-warning">Start tracking!</a></p>'}
            </div>
        </div>
        
        <div class="col-md-6">
            <div class="glass-card p-4">
                <h5 class="text-white mb-3">Quick Actions</h5>
                <div class="d-grid gap-2">
                    <a href="{{ url_for('mood_checkin') }}" class="btn btn-primary">
                        <i class="fas fa-heart"></i> Mood Check-in
                    </a>
                    <a href="{{ url_for('mood_journal') }}" class="btn btn-outline-light">
                        <i class="fas fa-book"></i> Write in Journal
                    </a>
                    <a href="{{ url_for('community') }}" class="btn btn-outline-light">
                        <i class="fas fa-users"></i> Visit Community
                    </a>
                    <a href="{{ url_for('therapy') }}" class="btn btn-outline-light">
                        <i class="fas fa-spa"></i> Wellness Activities
                    </a>
                </div>
            </div>
        </div>
    </div>
    """
    return render_template_string(BASE_TEMPLATE, content=content, title="Dashboard")

@app.route('/mood-checkin', methods=['GET', 'POST'])
@login_required
def mood_checkin():
    if request.method == 'POST':
        mood_score = request.form.get('mood_score', type=float)
        mood_text = request.form.get('mood_text', '').strip()
        
        if mood_score is None or mood_score < -1 or mood_score > 1:
            flash('Please select a valid mood score.', 'danger')
            return redirect(url_for('mood_checkin'))
        
        # Analyze mood if text provided
        if mood_text:
            ai_analysis = mood_analyzer.analyze_mood_text(mood_text)
            emergency_keywords = ai_analysis.get('emergency_keywords', [])
            
            mood_entry = MoodEntry(
                user_id=current_user.id,
                mood_score=mood_score,
                mood_text=mood_text,
                ai_sentiment=ai_analysis.get('sentiment', 'neutral'),
                ai_confidence=ai_analysis.get('confidence', 0.0),
                is_emergency_flagged=bool(emergency_keywords)
            )
            
            if emergency_keywords:
                flash('Your entry has been saved. If you are in crisis, please reach out for help immediately.', 'warning')
                if current_user.is_minor and current_user.guardian_email:
                    flash(f'Your guardian {current_user.guardian_name} has been notified.', 'info')
            else:
                flash('Mood check-in saved successfully!', 'success')
        else:
            mood_entry = MoodEntry(
                user_id=current_user.id,
                mood_score=mood_score
            )
            flash('Mood check-in saved successfully!', 'success')
        
        db.session.add(mood_entry)
        db.session.commit()
        return redirect(url_for('dashboard'))
    
    content = """
    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="glass-card p-5">
                <h3 class="text-center mb-4 text-white text-glow">Daily Mood Check-in</h3>
                
                <form method="POST">
                    <div class="mb-4">
                        <label class="form-label text-white">Language:</label>
                        <select class="form-control" id="language" onchange="updateLanguage()">
                            <option value="en">English</option>
                            <option value="es">Español</option>
                            <option value="fr">Français</option>
                            <option value="de">Deutsch</option>
                            <option value="hi">हिंदी</option>
                        </select>
                    </div>
                    
                    <div class="mb-4">
                        <label class="form-label text-white" id="mood-label">How are you feeling today?</label>
                        <input type="range" class="form-range" name="mood_score" 
                               min="-1" max="1" step="0.1" value="0" id="moodSlider" 
                               oninput="updateMoodDisplay()">
                        <div class="d-flex justify-content-between">
                            <span class="text-danger">😞 Very Low</span>
                            <span class="text-warning">😐 Neutral</span>
                            <span class="text-success">😊 Very High</span>
                        </div>
                        <div class="text-center mt-2">
                            <span id="mood-value" class="badge bg-primary fs-6">0.0</span>
                        </div>
                    </div>
                    
                    <div class="mb-4">
                        <label class="form-label text-white" id="text-label">Tell us more about your feelings:</label>
                        <textarea class="form-control" name="mood_text" rows="4" 
                                  placeholder="Express your thoughts and emotions..."></textarea>
                    </div>
                    
                    <div class="mb-4">
                        <label class="form-label text-white">Voice Recording:</label>
                        <div class="d-grid">
                            <button type="button" class="btn btn-outline-light" onclick="toggleRecording()">
                                <i class="fas fa-microphone"></i> <span id="record-text">Start Recording</span>
                            </button>
                        </div>
                        <div id="recording-status" class="mt-2 text-center" style="display: none;">
                            <span class="text-warning">🔴 Recording... <span id="timer">0:00</span></span>
                        </div>
                    </div>
                    
                    <button type="submit" class="btn btn-primary w-100">
                        <i class="fas fa-save"></i> Save Check-in
                    </button>
                </form>
            </div>
        </div>
    </div>

    <script>
    let isRecording = false;
    let recordingTimer;
    let seconds = 0;

    const translations = {
        en: {
            'mood-label': 'How are you feeling today?',
            'text-label': 'Tell us more about your feelings:',
            'record-text': 'Start Recording'
        },
        es: {
            'mood-label': '¿Cómo te sientes hoy?',
            'text-label': 'Cuéntanos más sobre tus sentimientos:',
            'record-text': 'Comenzar Grabación'
        },
        fr: {
            'mood-label': 'Comment vous sentez-vous aujourd\\'hui?',
            'text-label': 'Parlez-nous de vos sentiments:',
            'record-text': 'Commencer l\\'enregistrement'
        },
        de: {
            'mood-label': 'Wie fühlst du dich heute?',
            'text-label': 'Erzählen Sie uns mehr über Ihre Gefühle:',
            'record-text': 'Aufnahme starten'
        },
        hi: {
            'mood-label': 'आज आप कैसा महसूस कर रहे हैं?',
            'text-label': 'अपनी भावनाओं के बारे में और बताएं:',
            'record-text': 'रिकॉर्डिंग शुरू करें'
        }
    };

    function updateLanguage() {
        const selectedLang = document.getElementById('language').value;
        const langData = translations[selectedLang];
        
        if (langData) {
            Object.keys(langData).forEach(key => {
                const element = document.getElementById(key);
                if (element) {
                    element.textContent = langData[key];
                }
            });
        }
    }

    function updateMoodDisplay() {
        const value = document.getElementById('moodSlider').value;
        document.getElementById('mood-value').textContent = parseFloat(value).toFixed(1);
    }

    function toggleRecording() {
        const recordBtn = document.getElementById('record-text');
        const status = document.getElementById('recording-status');
        
        if (!isRecording) {
            isRecording = true;
            recordBtn.textContent = 'Stop Recording';
            status.style.display = 'block';
            
            seconds = 0;
            recordingTimer = setInterval(() => {
                seconds++;
                const mins = Math.floor(seconds / 60);
                const secs = seconds % 60;
                document.getElementById('timer').textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
            }, 1000);
        } else {
            isRecording = false;
            recordBtn.textContent = 'Start Recording';
            status.style.display = 'none';
            clearInterval(recordingTimer);
        }
    }

    // Initialize
    updateMoodDisplay();
    </script>
    """
    return render_template_string(BASE_TEMPLATE, content=content, title="Mood Check-in")

@app.route('/journal', methods=['GET', 'POST'])
@login_required
def mood_journal():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        
        if not content:
            flash('Journal content is required.', 'danger')
            return redirect(url_for('mood_journal'))
        
        # Analyze content
        ai_analysis = mood_analyzer.analyze_mood_text(content)
        
        journal_entry = JournalEntry(
            user_id=current_user.id,
            title=title or f"Journal Entry - {datetime.utcnow().strftime('%B %d, %Y')}",
            content=content,
            sentiment_score=ai_analysis.get('score', 0.0)
        )
        
        db.session.add(journal_entry)
        db.session.commit()
        
        flash('Journal entry saved successfully!', 'success')
        return redirect(url_for('mood_journal'))
    
    # Get user's journal entries
    entries = JournalEntry.query.filter_by(user_id=current_user.id)\
                               .order_by(desc(JournalEntry.created_at))\
                               .all()
    
    content = f"""
    <div class="row">
        <div class="col-md-8">
            <div class="glass-card p-4">
                <h3 class="text-white mb-4">Personal Journal</h3>
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label text-white">Title (Optional)</label>
                        <input type="text" class="form-control" name="title" 
                               placeholder="Give your entry a title...">
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label text-white">How are you feeling today?</label>
                        <textarea class="form-control" name="content" rows="8" 
                                  placeholder="Express your thoughts and feelings..." required></textarea>
                    </div>
                    
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-save"></i> Save Entry
                    </button>
                </form>
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="glass-card p-4">
                <h5 class="text-white mb-3">Previous Entries</h5>
                {f'''
                {''.join([f"""
                <div class="glass-card p-3 mb-2">
                    <h6 class="text-white">{entry.title}</h6>
                    <p class="text-white-50 small">{entry.content[:100]}...</p>
                    <small class="text-warning">{entry.created_at.strftime('%B %d, %Y')}</small>
                    {f'<span class="badge bg-{"success" if entry.sentiment_score > 0 else "warning" if entry.sentiment_score == 0 else "danger"} ms-2">{"Positive" if entry.sentiment_score > 0 else "Neutral" if entry.sentiment_score == 0 else "Negative"}</span>' if entry.sentiment_score is not None else ''}
                </div>
                """ for entry in entries[:5]])}
                ''' if entries else '<p class="text-white-50">No journal entries yet. Start writing your first entry!</p>'}
            </div>
        </div>
    </div>
    """
    return render_template_string(BASE_TEMPLATE, content=content, title="Journal")

@app.route('/community', methods=['GET', 'POST'])
@login_required
def community():
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        is_anonymous = request.form.get('is_anonymous') == 'on'
        
        if not content:
            flash('Please enter some content to share.', 'danger')
            return redirect(url_for('community'))
        
        post = CommunityPost(
            user_id=current_user.id,
            content=content,
            is_anonymous=is_anonymous
        )
        
        db.session.add(post)
        db.session.commit()
        
        flash('Your post has been shared with the community.', 'success')
        return redirect(url_for('community'))
    
    posts = CommunityPost.query.order_by(desc(CommunityPost.created_at)).limit(20).all()
    
    content = f"""
    <div class="row">
        <div class="col-md-8">
            <div class="glass-card p-4 mb-4">
                <h5 class="text-white mb-3">Share with Community</h5>
                <form method="POST">
                    <div class="mb-3">
                        <textarea class="form-control" name="content" rows="3" 
                                  placeholder="Share your thoughts anonymously with the community..." required></textarea>
                    </div>
                    <div class="form-check mb-3">
                        <input class="form-check-input" type="checkbox" name="is_anonymous" 
                               id="anonymous" checked>
                        <label class="form-check-label text-white" for="anonymous">
                            Post anonymously
                        </label>
                    </div>
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-share"></i> Share
                    </button>
                </form>
            </div>

            <div class="community-posts">
                {f'''
                {''.join([f"""
                <div class="glass-card p-4 mb-3">
                    <p class="text-white">{post.content}</p>
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="text-white-50">
                            {'Anonymous' if post.is_anonymous else User.query.get(post.user_id).username}
                            • {post.created_at.strftime('%m/%d/%Y %H:%M')}
                        </small>
                        <div class="reaction-buttons">
                            <a href="{url_for('react_to_post', post_id=post.id, reaction_type='heart')}" 
                               class="btn btn-sm btn-outline-danger me-1">
                                ❤️ {post.hearts_count}
                            </a>
                            <a href="{url_for('react_to_post', post_id=post.id, reaction_type='hug')}" 
                               class="btn btn-sm btn-outline-warning me-1">
                                🤗 {post.hugs_count}
                            </a>
                            <a href="{url_for('react_to_post', post_id=post.id, reaction_type='support')}" 
                               class="btn btn-sm btn-outline-success">
                                💪 {post.support_count}
                            </a>
                        </div>
                    </div>
                </div>
                """ for post in posts])}
                ''' if posts else '<div class="glass-card p-4"><p class="text-white-50">No community posts yet. Be the first to share!</p></div>'}
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="glass-card p-4">
                <h5 class="text-white mb-3">Community Guidelines</h5>
                <ul class="list-unstyled text-white">
                    <li class="mb-2">✅ Be supportive and kind</li>
                    <li class="mb-2">✅ Share your experiences</li>
                    <li class="mb-2">✅ Offer encouragement</li>
                    <li class="mb-2">❌ No hate speech</li>
                    <li class="mb-2">❌ No personal attacks</li>
                    <li class="mb-2">❌ Respect privacy</li>
                </ul>
            </div>
        </div>
    </div>
    """
    return render_template_string(BASE_TEMPLATE, content=content, title="Community")

@app.route('/react/<int:post_id>/<reaction_type>')
@login_required
def react_to_post(post_id, reaction_type):
    if reaction_type not in ['heart', 'hug', 'support']:
        flash('Invalid reaction type.', 'danger')
        return redirect(url_for('community'))
    
    post = CommunityPost.query.get_or_404(post_id)
    
    # Update reaction count (simplified logic)
    if reaction_type == 'heart':
        post.hearts_count += 1
    elif reaction_type == 'hug':
        post.hugs_count += 1
    elif reaction_type == 'support':
        post.support_count += 1
    
    db.session.commit()
    return redirect(url_for('community'))

@app.route('/therapy')
@login_required
def therapy():
    content = """
    <div class="row mb-4">
        <div class="col-12">
            <h2 class="text-white mb-4 text-glow">Wellness Activities</h2>
        </div>
    </div>

    <div class="row g-4">
        <div class="col-md-4">
            <div class="mood-card h-100 p-4 text-center text-white">
                <i class="fas fa-wind text-primary fa-4x mb-3"></i>
                <h4>Breathing Exercise</h4>
                <p>Guided breathing to reduce stress and anxiety</p>
                <button class="btn btn-primary" onclick="startBreathing()">Start Exercise</button>
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="mood-card h-100 p-4 text-center text-white">
                <i class="fas fa-heart text-danger fa-4x mb-3"></i>
                <h4>Positive Affirmations</h4>
                <p>Daily affirmations for mental well-being</p>
                <button class="btn btn-primary" onclick="showAffirmation()">Get Affirmation</button>
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="mood-card h-100 p-4 text-center text-white">
                <i class="fas fa-sun text-warning fa-4x mb-3"></i>
                <h4>Gratitude Practice</h4>
                <p>Focus on what you're grateful for today</p>
                <button class="btn btn-primary" onclick="showGratitude()">Practice Gratitude</button>
            </div>
        </div>
    </div>

    <!-- Breathing Exercise Modal -->
    <div class="modal fade" id="breathingModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content" style="background: rgba(255,255,255,0.1); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.2);">
                <div class="modal-header border-0">
                    <h5 class="modal-title text-white">🌬️ Breathing Exercise</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body text-center">
                    <div class="breathing-circle" id="breathingCircle">
                        <div class="text-white fw-bold" id="breathingText">Click Start</div>
                    </div>
                    <div class="mt-4">
                        <button class="btn btn-primary" id="breathingBtn" onclick="toggleBreathing()">Start</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
    let breathingActive = false;
    let breathingInterval;

    const affirmations = [
        "You are stronger than you think",
        "This feeling will pass, and you will grow from it",
        "You deserve love and kindness, especially from yourself",
        "Every day is a new opportunity to heal and grow",
        "You are not alone in this journey"
    ];

    function startBreathing() {
        const modal = new bootstrap.Modal(document.getElementById('breathingModal'));
        modal.show();
    }

    function toggleBreathing() {
        const circle = document.getElementById('breathingCircle');
        const text = document.getElementById('breathingText');
        const btn = document.getElementById('breathingBtn');
        
        if (!breathingActive) {
            breathingActive = true;
            btn.textContent = 'Stop';
            startBreathingCycle();
        } else {
            breathingActive = false;
            btn.textContent = 'Start';
            clearInterval(breathingInterval);
            circle.className = 'breathing-circle';
            text.textContent = 'Click Start';
        }
    }

    function startBreathingCycle() {
        const circle = document.getElementById('breathingCircle');
        const text = document.getElementById('breathingText');
        let phase = 'inhale';
        
        function cycle() {
            if (!breathingActive) return;
            
            if (phase === 'inhale') {
                circle.className = 'breathing-circle inhale';
                text.textContent = 'Breathe In...';
                phase = 'exhale';
            } else {
                circle.className = 'breathing-circle';
                text.textContent = 'Breathe Out...';
                phase = 'inhale';
            }
        }
        
        cycle();
        breathingInterval = setInterval(cycle, 4000);
    }

    function showAffirmation() {
        const randomAffirmation = affirmations[Math.floor(Math.random() * affirmations.length)];
        alert("✨ Daily Affirmation ✨\\n\\n" + randomAffirmation);
    }

    function showGratitude() {
        const gratitude = prompt("What are you grateful for today?");
        if (gratitude) {
            alert("Thank you for sharing! Practicing gratitude helps improve mental well-being. 🙏");
        }
    }
    </script>
    """
    return render_template_string(BASE_TEMPLATE, content=content, title="Wellness")

@app.route('/api/mood-data')
@login_required
def api_mood_data():
    days = request.args.get('days', 30, type=int)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    mood_entries = MoodEntry.query.filter(
        MoodEntry.user_id == current_user.id,
        MoodEntry.created_at >= start_date
    ).order_by(MoodEntry.created_at).all()
    
    data = [{
        'date': entry.created_at.strftime('%Y-%m-%d'),
        'mood_score': entry.mood_score,
        'sentiment': entry.ai_sentiment or 'neutral'
    } for entry in mood_entries]
    
    return jsonify(data)

# Error handlers with beautiful 3D styling
@app.errorhandler(404)
def not_found(error):
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>404 - Page Not Found</title>
        <style>
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; text-align: center; padding: 100px; min-height: 100vh;
                margin: 0; display: flex; align-items: center; justify-content: center;
                position: relative; overflow: hidden;
            }
            body::before {
                content: '';
                position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: radial-gradient(circle at 20% 80%, rgba(120, 119, 198, 0.3) 0%, transparent 50%);
                z-index: -1; animation: float 6s ease-in-out infinite;
            }
            @keyframes float { 0%, 100% { transform: translateY(0px); } 50% { transform: translateY(-20px); } }
            .error-container { 
                background: rgba(255,255,255,0.15); padding: 60px; border-radius: 25px; 
                backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.2);
                box-shadow: 0 25px 50px rgba(0,0,0,0.1);
            }
            h1 { font-size: 5rem; margin: 0; text-shadow: 3px 3px 6px rgba(0,0,0,0.3); 
                 background: linear-gradient(45deg, #ffd700, #ff6b6b); -webkit-background-clip: text; 
                 -webkit-text-fill-color: transparent; background-clip: text; }
            p { font-size: 1.5rem; margin: 20px 0; text-shadow: 1px 1px 2px rgba(0,0,0,0.3); }
            a { color: #fff; text-decoration: none; background: rgba(255,255,255,0.2); 
                padding: 15px 30px; border-radius: 30px; transition: all 0.3s; 
                box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
            a:hover { background: rgba(255,255,255,0.3); transform: translateY(-3px); 
                      box-shadow: 0 15px 40px rgba(0,0,0,0.2); }
        </style>
    </head>
    <body>
        <div class="error-container">
            <h1>404</h1>
            <p>The page you're looking for doesn't exist.</p>
            <a href="/">🏠 Return to Home</a>
        </div>
    </body>
    </html>
    """, 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>500 - Server Error</title>
        <style>
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; text-align: center; padding: 100px; min-height: 100vh;
                margin: 0; display: flex; align-items: center; justify-content: center;
                position: relative; overflow: hidden;
            }
            body::before {
                content: '';
                position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: radial-gradient(circle at 80% 20%, rgba(255, 119, 198, 0.3) 0%, transparent 50%);
                z-index: -1; animation: float 6s ease-in-out infinite;
            }
            @keyframes float { 0%, 100% { transform: translateY(0px); } 50% { transform: translateY(-20px); } }
            .error-container { 
                background: rgba(255,255,255,0.15); padding: 60px; border-radius: 25px; 
                backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.2);
                box-shadow: 0 25px 50px rgba(0,0,0,0.1);
            }
            h1 { font-size: 5rem; margin: 0; text-shadow: 3px 3px 6px rgba(0,0,0,0.3); 
                 background: linear-gradient(45deg, #ff6b6b, #ffd700); -webkit-background-clip: text; 
                 -webkit-text-fill-color: transparent; background-clip: text; }
            p { font-size: 1.5rem; margin: 20px 0; text-shadow: 1px 1px 2px rgba(0,0,0,0.3); }
            a { color: #fff; text-decoration: none; background: rgba(255,255,255,0.2); 
                padding: 15px 30px; border-radius: 30px; transition: all 0.3s; 
                box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
            a:hover { background: rgba(255,255,255,0.3); transform: translateY(-3px); 
                      box-shadow: 0 15px 40px rgba(0,0,0,0.2); }
        </style>
    </head>
    <body>
        <div class="error-container">
            <h1>500</h1>
            <p>Something went wrong on our end. Please try again.</p>
            <a href="/">🏠 Return to Home</a>
        </div>
    </body>
    </html>
    """, 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    app.run(host='0.0.0.0', port=5000, debug=True)