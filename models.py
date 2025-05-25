from . import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# ✅ User Model
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    emergency_contact = db.Column(db.String(120))
    emergency_contact_phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_emergency_enabled = db.Column(db.Boolean, default=False)

    # Relationships
    mood_entries = db.relationship("MoodEntry", backref="user", lazy=True, cascade="all, delete-orphan")
    journal_entries = db.relationship("JournalEntry", backref="user", lazy=True, cascade="all, delete-orphan")
    community_posts = db.relationship("CommunityPost", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ✅ MoodEntry Model
class MoodEntry(db.Model):
    __tablename__ = "mood_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    mood_score = db.Column(db.Float, nullable=False)
    mood_text = db.Column(db.Text)
    voice_analysis_score = db.Column(db.Float)
    ai_sentiment = db.Column(db.String(20))
    ai_confidence = db.Column(db.Float)
    emotions_detected = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_emergency_flagged = db.Column(db.Boolean, default=False)

# ✅ JournalEntry Model
class JournalEntry(db.Model):
    __tablename__ = "journal_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)
    mood_tags = db.Column(db.String(200))
    ai_analysis = db.Column(db.Text)
    sentiment_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ✅ CommunityPost Model
class CommunityPost(db.Model):
    __tablename__ = "community_posts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_anonymous = db.Column(db.Boolean, default=True)
    hearts_count = db.Column(db.Integer, default=0)
    hugs_count = db.Column(db.Integer, default=0)
    support_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ✅ PostReaction Model
class PostReaction(db.Model):
    __tablename__ = "post_reactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("community_posts.id"), nullable=False)
    reaction_type = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("user_id", "post_id", "reaction_type"),)

# ✅ EmergencyAlert Model
class EmergencyAlert(db.Model):
    __tablename__ = "emergency_alerts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    mood_entry_id = db.Column(db.Integer, db.ForeignKey("mood_entries.id"))
    alert_type = db.Column(db.String(50), nullable=False)
    alert_content = db.Column(db.Text)
    is_resolved = db.Column(db.Boolean, default=False)
    emergency_contact_notified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    