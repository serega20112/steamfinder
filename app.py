from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///steam_finder.db'
db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    steam_id = db.Column(db.String(64), nullable=False)
    profile_info = db.Column(db.Text, nullable=False)
    favorite_games = db.Column(db.Text, default='[]')
    gaming_schedule = db.Column(db.Text, default='{}')
    skill_level = db.Column(db.Integer, default=1)
    experience_points = db.Column(db.Integer, default=0)
    achievements = db.Column(db.Text, default='[]')
    preferred_genres = db.Column(db.Text, default='[]')
    language_preferences = db.Column(db.Text, default='["English"]')
    discord_id = db.Column(db.String(64))
    twitch_username = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_premium = db.Column(db.Boolean, default=False)
    notification_settings = db.Column(db.Text, default='{}')

    def __init__(self, username, password, steam_id, profile_info):
        self.username = username
        self.password = generate_password_hash(password)
        self.steam_id = steam_id
        self.profile_info = profile_info

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def add_experience(self, amount):
        self.experience_points += amount
        level_threshold = self.skill_level * 1000
        if self.experience_points >= level_threshold:
            self.skill_level += 1
            return True
        return False

# Game Model
class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    steam_id = db.Column(db.String(64), unique=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    genres = db.Column(db.Text, default='[]')
    tags = db.Column(db.Text, default='[]')
    release_date = db.Column(db.DateTime)
    developer = db.Column(db.String(128))
    publisher = db.Column(db.String(128))
    price = db.Column(db.Float)
    rating = db.Column(db.Float)
    player_count = db.Column(db.Integer)
    achievements = db.Column(db.Text, default='[]')
    requirements = db.Column(db.Text)

# Group Model
class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    game_focus = db.Column(db.String(64))
    skill_requirement = db.Column(db.Integer, default=0)
    max_members = db.Column(db.Integer, default=100)
    is_private = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    rules = db.Column(db.Text, default='[]')
    announcement = db.Column(db.Text)
    discord_invite = db.Column(db.String(128))
    scheduled_events = db.Column(db.Text, default='[]')
    achievement_tracking = db.Column(db.Boolean, default=True)
    users = db.relationship('User', secondary='user_group', backref=db.backref('groups', lazy=True))

# Event Model
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    game_id = db.Column(db.String(64))
    max_participants = db.Column(db.Integer)
    skill_requirement = db.Column(db.Integer, default=0)
    voice_required = db.Column(db.Boolean, default=False)
    recurring = db.Column(db.Boolean, default=False)
    recurring_pattern = db.Column(db.String(64))
    location = db.Column(db.String(128))
    status = db.Column(db.String(32), default='scheduled')
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    participants = db.relationship('User', secondary='event_participants')
    rewards = db.Column(db.Text, default='[]')

# Message Model
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    message_type = db.Column(db.String(32), default='text')
    attachments = db.Column(db.Text, default='[]')
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    edited = db.Column(db.Boolean, default=False)
    edited_timestamp = db.Column(db.DateTime)
    reactions = db.Column(db.Text, default='[]')

# Achievement Model
class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    game_id = db.Column(db.String(64))
    achievement_id = db.Column(db.String(64))
    name = db.Column(db.String(128))
    description = db.Column(db.Text)
    unlock_date = db.Column(db.DateTime)
    rarity = db.Column(db.Float)
    icon_url = db.Column(db.String(256))

# UserStats Model
class UserStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    game_id = db.Column(db.String(64))
    playtime = db.Column(db.Integer, default=0)
    last_played = db.Column(db.DateTime)
    achievements_count = db.Column(db.Integer, default=0)
    stats = db.Column(db.Text, default='{}')

# Friend Model
class Friend(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(32), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_game_together = db.Column(db.String(64))
    playtime_together = db.Column(db.Integer, default=0)

# Review Model
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    game_id = db.Column(db.String(64))
    rating = db.Column(db.Integer)
    text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    edited_at = db.Column(db.DateTime)
    helpful_votes = db.Column(db.Integer, default=0)
    playtime_at_review = db.Column(db.Integer)

# Tournament Model
class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    game_id = db.Column(db.String(64))
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    max_participants = db.Column(db.Integer)
    prize_pool = db.Column(db.Text, default='{}')
    rules = db.Column(db.Text)
    status = db.Column(db.String(32), default='upcoming')
    bracket = db.Column(db.Text, default='[]')
    participants = db.relationship('User', secondary='tournament_participants')

# Association Tables
user_group = db.Table('user_group',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('group_id', db.Integer, db.ForeignKey('group.id'))
)

event_participants = db.Table('event_participants',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'))
)

tournament_participants = db.Table('tournament_participants',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('tournament_id', db.Integer, db.ForeignKey('tournament.id'))
)

# Authentication Decorator
# Authentication Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes

@app.route('/')
def index():
    featured_games = Game.query.order_by(Game.rating.desc()).limit(5).all()
    active_tournaments = Tournament.query.filter_by(status='active').all()
    return render_template('index.html', featured_games=featured_games, tournaments=active_tournaments)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            user.last_login = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('profile', username=username))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        steam_id = request.form['steam_id']
        profile_info = request.form['profile_info']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return render_template('register.html')
            
        user = User(username, password, steam_id, profile_info)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/profile/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first()
    if user:
        user_stats = UserStats.query.filter_by(user_id=user.id).all()
        achievements = Achievement.query.filter_by(user_id=user.id).all()
        recent_games = Game.query.join(UserStats).filter(UserStats.user_id == user.id)\
            .order_by(UserStats.last_played.desc()).limit(5).all()
        return render_template('profile.html', user=user, stats=user_stats, 
                             achievements=achievements, recent_games=recent_games)
    return redirect(url_for('index'))

@app.route('/games')
def games():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    games = Game.query.paginate(page=page, per_page=per_page)
    return render_template('games.html', games=games)

@app.route('/game/<game_id>')
def game_details(game_id):
    game = Game.query.filter_by(steam_id=game_id).first()
    if game:
        reviews = Review.query.filter_by(game_id=game_id).order_by(Review.helpful_votes.desc()).limit(10).all()
        similar_games = Game.query.filter(Game.genres.contains(game.genres)).limit(5).all()
        return render_template('game_details.html', game=game, reviews=reviews, similar_games=similar_games)
    return redirect(url_for('games'))

@app.route('/achievements')
@login_required
def achievements():
    user_id = session['user_id']
    achievements = Achievement.query.filter_by(user_id=user_id).all()
    return render_template('achievements.html', achievements=achievements)

@app.route('/friends')
@login_required
def friends():
    user_id = session['user_id']
    friends = Friend.query.filter_by(user_id=user_id, status='accepted').all()
    pending_requests = Friend.query.filter_by(friend_id=user_id, status='pending').all()
    return render_template('friends.html', friends=friends, pending_requests=pending_requests)

@app.route('/add_friend/<int:friend_id>', methods=['POST'])
@login_required
def add_friend(friend_id):
    user_id = session['user_id']
    if user_id == friend_id:
        flash('You cannot add yourself as a friend')
        return redirect(url_for('friends'))
    
    existing = Friend.query.filter_by(user_id=user_id, friend_id=friend_id).first()
    if existing:
        flash('Friend request already sent')
        return redirect(url_for('friends'))
    
    friend_request = Friend(user_id=user_id, friend_id=friend_id)
    db.session.add(friend_request)
    db.session.commit()
    flash('Friend request sent')
    return redirect(url_for('friends'))

@app.route('/accept_friend/<int:request_id>', methods=['POST'])
@login_required
def accept_friend(request_id):
    friend_request = Friend.query.get_or_404(request_id)
    if friend_request.friend_id != session['user_id']:
        flash('Unauthorized action')
        return redirect(url_for('friends'))
    
    friend_request.status = 'accepted'
    # Create reverse friendship
    reverse_friend = Friend(user_id=friend_request.friend_id,
                          friend_id=friend_request.user_id,
                          status='accepted')
    db.session.add(reverse_friend)
    db.session.commit()
    flash('Friend request accepted')
    return redirect(url_for('friends'))

@app.route('/tournaments')
def tournaments():
    active = Tournament.query.filter_by(status='active').all()
    upcoming = Tournament.query.filter_by(status='upcoming').all()
    past = Tournament.query.filter_by(status='completed').all()
    return render_template('tournaments.html', active=active, upcoming=upcoming, past=past)

@app.route('/create_tournament', methods=['GET', 'POST'])
@login_required
def create_tournament():
    if request.method == 'POST':
        tournament = Tournament(
            name=request.form['name'],
            game_id=request.form['game_id'],
            description=request.form['description'],
            start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d'),
            end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d'),
            max_participants=int(request.form['max_participants']),
            prize_pool=request.form['prize_pool'],
            rules=request.form['rules']
        )
        db.session.add(tournament)
        db.session.commit()
        flash('Tournament created successfully')
        return redirect(url_for('tournaments'))
    return render_template('create_tournament.html')

@app.route('/join_tournament/<int:tournament_id>', methods=['POST'])
@login_required
def join_tournament(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    if len(tournament.participants) >= tournament.max_participants:
        flash('Tournament is full')
        return redirect(url_for('tournaments'))
    
    user = User.query.get(session['user_id'])
    tournament.participants.append(user)
    db.session.commit()
    flash('Successfully joined tournament')
    return redirect(url_for('tournaments'))

@app.route('/groups')
def groups():
    public_groups = Group.query.filter_by(is_private=False).all()
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        user_groups = user.groups
        return render_template('groups.html', public_groups=public_groups, user_groups=user_groups)
    return render_template('groups.html', public_groups=public_groups)

@app.route('/create_group', methods=['GET', 'POST'])
@login_required
def create_group():
    if request.method == 'POST':
        group = Group(
            name=request.form['name'],
            description=request.form['description'],
            game_focus=request.form['game_focus'],
            skill_requirement=int(request.form['skill_requirement']),
            max_members=int(request.form['max_members']),
            is_private=bool(request.form.get('is_private')),
            owner_id=session['user_id'],
            rules=request.form['rules']
        )
        db.session.add(group)
        db.session.commit()
        flash('Group created successfully')
        return redirect(url_for('groups'))
    return render_template('create_group.html')

@app.route('/group/<int:group_id>')
def group_details(group_id):
    group = Group.query.get_or_404(group_id)
    if group.is_private and ('user_id' not in session or 
                           User.query.get(session['user_id']) not in group.users):
        flash('This is a private group')
        return redirect(url_for('groups'))
    return render_template('group_details.html', group=group)

@app.route('/join_group/<int:group_id>', methods=['POST'])
@login_required
def join_group(group_id):
    group = Group.query.get_or_404(group_id)
    user = User.query.get(session['user_id'])
    
    if user in group.users:
        flash('Already a member of this group')
        return redirect(url_for('group_details', group_id=group_id))
    
    if len(group.users) >= group.max_members:
        flash('Group is full')
        return redirect(url_for('group_details', group_id=group_id))
    
    if group.skill_requirement > user.skill_level:
        flash('You do not meet the skill requirement for this group')
        return redirect(url_for('group_details', group_id=group_id))
    
    group.users.append(user)
    db.session.commit()
    flash('Successfully joined group')
    return redirect(url_for('group_details', group_id=group_id))

@app.route('/messages')
@login_required
def messages():
    user_id = session['user_id']
    sent = Message.query.filter_by(sender_id=user_id).order_by(Message.timestamp.desc()).all()
    received = Message.query.filter_by(recipient_id=user_id).order_by(Message.timestamp.desc()).all()
    return render_template('messages.html', sent=sent, received=received)

@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    recipient_id = request.form['recipient_id']
    text = request.form['text']
    message = Message(
        text=text,
        sender_id=session['user_id'],
        recipient_id=recipient_id,
        message_type=request.form.get('message_type', 'text'),
        attachments=request.form.get('attachments', '[]'),
        group_id=request.form.get('group_id')
    )
    db.session.add(message)
    db.session.commit()
    flash('Message sent')
    return redirect(url_for('messages'))

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query = request.form['query']
        users = User.query.filter(User.username.like(f'%{query}%')).all()
        games = Game.query.filter(Game.name.like(f'%{query}%')).all()
        groups = Group.query.filter(Group.name.like(f'%{query}%')).all()
        tournaments = Tournament.query.filter(Tournament.name.like(f'%{query}%')).all()
        return render_template('search_results.html', users=users, games=games,
                             groups=groups, tournaments=tournaments)
    return render_template('search.html')

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        user.profile_info = request.form['profile_info']
        user.discord_id = request.form['discord_id']
        user.twitch_username = request.form['twitch_username']
        user.preferred_genres = request.form['preferred_genres']
        user.language_preferences = request.form['language_preferences']
        user.notification_settings = request.form['notification_settings']
        
        if request.form.get('password'):
            user.password = generate_password_hash(request.form['password'])
        
        db.session.commit()
        flash('Profile updated successfully')
        return redirect(url_for('profile', username=user.username))
    return render_template('edit_profile.html', user=user)

@app.route('/write_review/<game_id>', methods=['GET', 'POST'])
@login_required
def write_review(game_id):
    if request.method == 'POST':
        review = Review(
            user_id=session['user_id'],
            game_id=game_id,
            rating=int(request.form['rating']),
            text=request.form['text'],
            playtime_at_review=int(request.form['playtime'])
        )
        db.session.add(review)
        db.session.commit()
        flash('Review submitted successfully')
        return redirect(url_for('game_details', game_id=game_id))
    return render_template('write_review.html', game_id=game_id)

@app.route('/vote_review/<int:review_id>', methods=['POST'])
@login_required
def vote_review(review_id):
    review = Review.query.get_or_404(review_id)
    review.helpful_votes += 1
    db.session.commit()
    return jsonify({'success': True, 'new_votes': review.helpful_votes})

# API Routes for AJAX calls

@app.route('/api/user_stats/<int:user_id>')
def api_user_stats(user_id):
    stats = UserStats.query.filter_by(user_id=user_id).all()
    return jsonify([{
        'game_id': stat.game_id,
        'playtime': stat.playtime,
        'achievements_count': stat.achievements_count,
        'last_played': stat.last_played.isoformat() if stat.last_played else None
    } for stat in stats])

@app.route('/api/game_recommendations/<int:user_id>')
def api_game_recommendations(user_id):
    user = User.query.get_or_404(user_id)
    preferred_genres = json.loads(user.preferred_genres)
    
    # Simple recommendation system based on genres and user's playtime
    recommended_games = Game.query.filter(
        Game.genres.contains(preferred_genres[0]) if preferred_genres else True
    ).order_by(Game.rating.desc()).limit(5).all()
    
    return jsonify([{
        'id': game.steam_id,
        'name': game.name,
        'description': game.description,
        'rating': game.rating
    } for game in recommended_games])

@app.route('/api/tournament_bracket/<int:tournament_id>')
def api_tournament_bracket(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    return jsonify({
        'bracket': json.loads(tournament.bracket),
        'participants': [user.username for user in tournament.participants]
    })

# Background Tasks (would typically use Celery in production)
def update_user_stats():
    users = User.query.all()
    for user in users:
        try:
            # Simulate fetching stats from Steam API
            stats = UserStats.query.filter_by(user_id=user.id).all()
            for stat in stats:
                # Simulate updating playtime
                stat.playtime += random.randint(0, 60)
                # Simulate achievement unlocks
                if random.random() < 0.1:  # 10% chance
                    new_achievement = Achievement(
                        user_id=user.id,
                        game_id=stat.game_id,
                        achievement_id=f'ach_{random.randint(1, 1000)}',
                        name=f'Achievement {random.randint(1, 100)}',
                        description='Random achievement description',
                        unlock_date=datetime.utcnow(),
                        rarity=random.random()
                    )
                    db.session.add(new_achievement)
            db.session.commit()
        except Exception as e:
            print(f"Error updating stats for user {user.id}: {str(e)}")

def clean_old_messages():
    # Delete messages older than 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    Message.query.filter(Message.timestamp < thirty_days_ago).delete()
    db.session.commit()

def update_tournament_status():
    now = datetime.utcnow()
    tournaments = Tournament.query.all()
    for tournament in tournaments:
        if tournament.start_date <= now <= tournament.end_date:
            tournament.status = 'active'
        elif now > tournament.end_date:
            tournament.status = 'completed'
        db.session.commit()

if __name__ == '__main__':
    # Create all database tables within the application context
    with app.app_context():
        db.create_all()

    # Register background tasks (in production, use a proper task queue)
    from threading import Thread
    import time

    def run_background_tasks():
        while True:
            update_user_stats()
            clean_old_messages()
            update_tournament_status()
            time.sleep(3600)  # Run every hour

    background_thread = Thread(target=run_background_tasks, daemon=True)
    background_thread.start()

    app.run(debug=True)
