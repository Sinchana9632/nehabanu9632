import logging
import sys
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, jsonify, session, abort, current_app
from flask_login import login_user, logout_user, login_required, current_user
from email_validator import validate_email, EmailNotValidError
from sqlalchemy import func, desc
from sqlalchemy.exc import IntegrityError

# Import from the package
from . import db
from .ai_analyzer import MoodAnalyzer
from .models import User, MoodEntry, JournalEntry, CommunityPost, PostReaction, EmergencyAlert

# Initialize AI analyzer
mood_analyzer = MoodAnalyzer()

from flask import current_app as app

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not username or len(username) < 3:
            flash('Username must be at least 3 characters long.', 'danger')
            return render_template('register.html')
        
        if not email:
            flash('Email is required.', 'danger')
            return render_template('register.html')
        
        try:
            validate_email(email)
        except EmailNotValidError:
            flash('Please enter a valid email address.', 'danger')
            return render_template('register.html')
        
        if not password or len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('register.html')
        
        # Create new user
        try:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'danger')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with mood trends"""
    # Get recent mood entries for chart
    recent_moods = MoodEntry.query.filter_by(user_id=current_user.id)\
                                 .order_by(desc(MoodEntry.created_at))\
                                 .limit(30).all()
    
    # Calculate statistics
    total_entries = len(recent_moods)
    avg_mood = sum(entry.mood_score for entry in recent_moods) / total_entries if total_entries > 0 else 0
    
    # Get mood trend (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    week_moods = [entry for entry in recent_moods if entry.created_at >= week_ago]
    trend = mood_analyzer.calculate_mood_trend([entry.mood_score for entry in week_moods])
    
    # Get recent journal entries
    recent_journals = JournalEntry.query.filter_by(user_id=current_user.id)\
                                       .order_by(desc(JournalEntry.created_at))\
                                       .limit(3).all()
    
    return render_template('dashboard.html', 
                         mood_entries=recent_moods[:7],
                         total_entries=total_entries,
                         avg_mood=avg_mood,
                         mood_trend=trend,
                         recent_journals=recent_journals)

@app.route('/mood-checkin', methods=['GET', 'POST'])
@login_required
def mood_checkin():
    """Daily mood check-in"""
    if request.method == 'POST':
        mood_score = request.form.get('mood_score', type=float)
        mood_text = request.form.get('mood_text', '').strip()
        voice_analysis_score = request.form.get('voice_analysis_score', type=float)
        
        if mood_score is None or mood_score < -1 or mood_score > 1:
            flash('Please select a valid mood score.', 'danger')
            return render_template('mood_checkin.html')
        
        # Analyze text with AI
        ai_analysis = {}
        emotions_list = []
        
        if mood_text:
            ai_analysis = mood_analyzer.analyze_mood_text(mood_text)
            emotions_list = ai_analysis.get('emotions', [])
            
            # Check for emergency keywords
            emergency_keywords = mood_analyzer.check_emergency_keywords(mood_text)
            if emergency_keywords:
                # Create mood entry first
                mood_entry = MoodEntry(
                    user_id=current_user.id,
                    mood_score=mood_score,
                    mood_text=mood_text,
                    voice_analysis_score=voice_analysis_score,
                    ai_sentiment=ai_analysis.get('sentiment', 'neutral'),
                    ai_confidence=ai_analysis.get('confidence', 0.0),
                    emotions_detected=','.join([e['emotion'] for e in emotions_list]),
                    is_emergency_flagged=True
                )
                db.session.add(mood_entry)
                db.session.commit()
                
                # Handle emergency
                handle_emergency_alert(current_user, mood_entry, emergency_keywords)
                flash('Your entry has been saved. If you are in crisis, please reach out for help immediately.', 'warning')
            else:
                mood_entry = MoodEntry(
                    user_id=current_user.id,
                    mood_score=mood_score,
                    mood_text=mood_text,
                    voice_analysis_score=voice_analysis_score,
                    ai_sentiment=ai_analysis.get('sentiment', 'neutral'),
                    ai_confidence=ai_analysis.get('confidence', 0.0),
                    emotions_detected=','.join([e['emotion'] for e in emotions_list])
                )
                db.session.add(mood_entry)
                db.session.commit()
                flash('Mood check-in saved successfully!', 'success')
        else:
            mood_entry = MoodEntry(
                user_id=current_user.id,
                mood_score=mood_score,
                voice_analysis_score=voice_analysis_score
            )
            db.session.add(mood_entry)
            db.session.commit()
            flash('Mood check-in saved successfully!', 'success')
        
        return redirect(url_for('dashboard'))
    
    return render_template('mood_checkin.html')

@app.route('/journal', methods=['GET', 'POST'])
@login_required
def mood_journal():
    """Mood journal for detailed reflections"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        mood_tags = request.form.get('mood_tags', '').strip()
        
        if not content:
            flash('Journal content is required.', 'danger')
            return render_template('journal.html')
        
        # Analyze content with AI
        ai_analysis = mood_analyzer.analyze_mood_text(content)
        
        journal_entry = JournalEntry(
            user_id=current_user.id,
            title=title or f"Journal Entry - {datetime.utcnow().strftime('%B %d, %Y')}",
            content=content,
            mood_tags=mood_tags,
            ai_analysis=str(ai_analysis),
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
    
    return render_template('journal.html', entries=entries)

@app.route('/community', methods=['GET', 'POST'])
@login_required
def community():
    """Anonymous community support wall"""
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
    
    # Get community posts
    posts = CommunityPost.query.order_by(desc(CommunityPost.created_at)).limit(20).all()
    
    return render_template('community.html', posts=posts)

@app.route('/react/<int:post_id>/<reaction_type>')
@login_required
def react_to_post(post_id, reaction_type):
    """React to a community post"""
    if reaction_type not in ['heart', 'hug', 'support']:
        flash('Invalid reaction type.', 'danger')
        return redirect(url_for('community'))
    
    post = CommunityPost.query.get_or_404(post_id)
    
    # Check if user already reacted with this type
    existing_reaction = PostReaction.query.filter_by(
        user_id=current_user.id,
        post_id=post_id,
        reaction_type=reaction_type
    ).first()
    
    if existing_reaction:
        # Remove reaction
        db.session.delete(existing_reaction)
        if reaction_type == 'heart':
            post.hearts_count = max(0, post.hearts_count - 1)
        elif reaction_type == 'hug':
            post.hugs_count = max(0, post.hugs_count - 1)
        elif reaction_type == 'support':
            post.support_count = max(0, post.support_count - 1)
    else:
        # Add reaction
        reaction = PostReaction(
            user_id=current_user.id,
            post_id=post_id,
            reaction_type=reaction_type
        )
        db.session.add(reaction)
        
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
    """Micro-therapy and wellness activities"""
    return render_template('therapy.html')

@app.route('/emergency-settings', methods=['GET', 'POST'])
@login_required
def emergency_settings():
    """Emergency contact settings"""
    if request.method == 'POST':
        emergency_contact = request.form.get('emergency_contact', '').strip()
        emergency_contact_phone = request.form.get('emergency_contact_phone', '').strip()
        is_emergency_enabled = request.form.get('is_emergency_enabled') == 'on'
        
        current_user.emergency_contact = emergency_contact
        current_user.emergency_contact_phone = emergency_contact_phone
        current_user.is_emergency_enabled = is_emergency_enabled
        
        db.session.commit()
        flash('Emergency settings updated successfully.', 'success')
        return redirect(url_for('emergency_settings'))
    
    return render_template('emergency_settings.html')

def handle_emergency_alert(user, mood_entry, keywords):
    """Handle emergency situation detection"""
    alert = EmergencyAlert(
        user_id=user.id,
        mood_entry_id=mood_entry.id,
        alert_type='keyword_detected',
        alert_content=f"Emergency keywords detected: {', '.join(keywords)}"
    )
    db.session.add(alert)
    
    # Send notification if enabled
    if user.is_emergency_enabled and user.emergency_contact:
        try:
            send_emergency_notification(user, keywords)
            alert.emergency_contact_notified = True
        except Exception as e:
            logging.error(f"Failed to send emergency notification: {e}")
    
    db.session.commit()

def send_emergency_notification(user, keywords):
    """Send emergency notification to designated contact"""
    # This would integrate with email/SMS service
    # For now, just log the alert
    logging.warning(f"EMERGENCY ALERT for user {user.username}: Keywords detected - {keywords}")

@app.route('/api/mood-data')
@login_required
def api_mood_data():
    """API endpoint for mood chart data"""
    days = request.args.get('days', 30, type=int)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    mood_entries = MoodEntry.query.filter(
        MoodEntry.user_id == current_user.id,
        MoodEntry.created_at >= start_date
    ).order_by(MoodEntry.created_at).all()
    
    data = [{
        'date': entry.created_at.strftime('%Y-%m-%d'),
        'mood_score': entry.mood_score,
        'sentiment': entry.ai_sentiment
    } for entry in mood_entries]
    
    return jsonify(data)

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', 
                          error_code=404,
                          error_message="Page Not Found",
                          error_description="The page you're looking for doesn't exist."), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('error.html', 
                          error_code=500,
                          error_message="Internal Server Error",
                          error_description="Something went wrong on our end. Please try again later."), 500

@app.errorhandler(403)
def forbidden(error):
    return render_template('error.html', 
                          error_code=403,
                          error_message="Access Forbidden",
                          error_description="You don't have permission to access this resource."), 403