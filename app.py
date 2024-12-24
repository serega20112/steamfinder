from flask_migrate import Migrate
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
import random
import string
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///steam_finder.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    steam_id = db.Column(db.String(50), unique=True, nullable=True)
    steam_link = db.Column(db.String(200), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    faceit_elo = db.Column(db.Integer, nullable=True)
    total_playtime = db.Column(db.Integer, nullable=True)
    profile_url = db.Column(db.String(200), unique=True, nullable=False)  # New field for custom profile URL
    games = db.relationship('Game', secondary='user_games', backref=db.backref('users', lazy='dynamic'))
    friends = db.relationship('User', secondary='friendships',
                            primaryjoin='User.id==friendships.c.user_id',
                            secondaryjoin='User.id==friendships.c.friend_id',
                            backref=db.backref('friends_of', lazy='dynamic'), lazy='dynamic')
    messages = db.relationship('Message', backref='sender', lazy='dynamic')

    def generate_profile_url(self):
        # Generate profile URL from name and steam_id
        if self.steam_id:
            return f"{self.name.lower().replace(' ', '-')}_{self.steam_id}"
        return f"{self.name.lower().replace(' ', '-')}"

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

user_games = db.Table('user_games',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('game_id', db.Integer, db.ForeignKey('game.id'), primary_key=True)
)

friendships = db.Table('friendships',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Create all tables
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        bio = request.form.get('bio', 'No bio')
        steam_link = request.form['steam_link']
        faceit_elo = request.form.get('faceit_elo', type=int)
        total_playtime = request.form.get('total_playtime', type=int)

        # Check Steam link format
        if not steam_link.startswith("https://steamcommunity.com/"):
            flash('Please enter a valid Steam profile link.', 'danger')
            return redirect(url_for('register'))

        # Extract Steam ID from the link
        steam_id = None
        if 'profiles/' in steam_link:
            steam_id = steam_link.split('profiles/')[-1].split('/')[0]
        elif 'id/' in steam_link:
            steam_id = steam_link.split('id/')[-1].split('/')[0]

        # Create user
        user = User(
            name=name,
            bio=bio,
            steam_link=steam_link,
            steam_id=steam_id,
            faceit_elo=faceit_elo,
            total_playtime=total_playtime
        )
        
        # Generate and set profile URL
        user.profile_url = user.generate_profile_url()
        
        db.session.add(user)
        db.session.commit()

        session['user_id'] = user.id
        flash('User registered successfully!', 'success')
        return redirect(url_for('view_profile', profile_url=user.profile_url))

    return render_template('register.html')

@app.route('/profile/<profile_url>')
def view_profile(profile_url):
    user = User.query.filter_by(profile_url=profile_url).first_or_404()
    return render_template('user_profile.html', user=user)

@app.route('/search', methods=['GET', 'POST'])
def search():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = User.query.get_or_404(user_id)
    if not user.steam_id:
        flash('Please link your Steam profile to use this feature.', 'warning')
        return redirect(url_for('link_steam', user_id=user.id))
    
    if request.method == 'POST':
        game_name = request.form['game_name']
        games = Game.query.filter(Game.name.ilike(f'%{game_name}%')).all()
        return render_template('search.html', games=games, popular_players=[])
    
    # List of 10 real esports players with profile URLs
    popular_players = [
        {"name": "Niko", "steam_link": "https://steamcommunity.com/profiles/76561197989736583", "bio": "Pro CS:GO Player", "faceit_elo": 3000, "id": 1, "profile_url": "niko_76561197989736583"},
        {"name": "m0NESY", "steam_link": "https://steamcommunity.com/id/m0NESY-/", "bio": "Young CS:GO talent", "faceit_elo": 3500, "id": 2, "profile_url": "m0nesy_76561198113666193"},
        {"name": "ZywOo", "steam_link": "https://steamcommunity.com/profiles/76561198113666193/", "bio": "Top 1 CS GO Player", "faceit_elo": 3700, "id": 3, "profile_url": "zywoo_76561198113666193"},
        {"name": "s1mple", "steam_link": "https://steamcommunity.com/profiles/[U:1:338040518]", "bio": "The GOAT", "faceit_elo": 4000, "id": 4, "profile_url": "s1mple_338040518"},
        {"name": "device", "steam_link": "https://steamcommunity.com/id/deviceCS", "bio": "Legendary Danish AWPer", "faceit_elo": 3200, "id": 5, "profile_url": "device_76561197987713664"},
        {"name": "ropz", "steam_link": "https://steamcommunity.com/id/ropzicle", "bio": "Silent Assassin", "faceit_elo": 3300, "id": 6, "profile_url": "ropz_76561198073591392"},
        {"name": "electroNic", "steam_link": "https://steamcommunity.com/id/electroNicNAVI", "bio": "Elite Rifler", "faceit_elo": 3100, "id": 7, "profile_url": "electronic_76561198044045107"},
        {"name": "Twistzz", "steam_link": "https://steamcommunity.com/id/Twistzz", "bio": "Headshot Machine", "faceit_elo": 3400, "id": 8, "profile_url": "twistzz_76561198134356993"},
        {"name": "karrigan", "steam_link": "https://steamcommunity.com/id/karriganCS", "bio": "IGL Genius", "faceit_elo": 3000, "id": 9, "profile_url": "karrigan_76561197989430253"},
        {"name": "b1t", "steam_link": "https://steamcommunity.com/id/b1tCS", "bio": "Sharp Aimer", "faceit_elo": 3100, "id": 10, "profile_url": "b1t_76561198996712695"},
    ]
    
    return render_template('search.html', games=[], popular_players=popular_players)



@app.route('/add_friend/<int:user_id>/<int:friend_id>')
def add_friend(user_id, friend_id):
    user = User.query.get_or_404(user_id)
    friend = User.query.get_or_404(friend_id)
    if user != friend and not user.is_following(friend):
        message = Message(sender=user, recipient_id=friend_id, content=f'{user.name} wants to add you as a friend on Steam Finder!')
        db.session.add(message)
        db.session.commit()
        flash(f'Friend request sent to {friend.name}', 'success')
    return redirect(url_for('profile', user_id=user.id))

@app.route('/messages')
def messages():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    user = User.query.get_or_404(user_id)
    messages = Message.query.filter_by(recipient_id=user_id).all()
    return render_template('messages.html', messages=messages)

@app.route('/send_message/<int:recipient_id>', methods=['GET', 'POST'])
def send_message(recipient_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    user = User.query.get_or_404(user_id)
    recipient = User.query.get_or_404(recipient_id)
    if request.method == 'POST':
        content = request.form['content']
        message = Message(sender=user, recipient_id=recipient_id, content=content)
        db.session.add(message)
        db.session.commit()
        flash('Message sent successfully!', 'success')
        return redirect(url_for('messages'))
    return render_template('send_message.html', recipient=recipient)

@app.route('/accept_friend/<int:user_id>/<int:friend_id>')
def accept_friend(user_id, friend_id):
    user = User.query.get_or_404(user_id)
    friend = User.query.get_or_404(friend_id)
    user.friends.append(friend)
    friend.friends.append(user)
    db.session.commit()
    flash(f'You are now friends with {friend.name}', 'success')
    return redirect(url_for('profile', user_id=user.id))

@app.route('/decline_friend/<int:user_id>/<int:friend_id>')
def decline_friend(user_id, friend_id):
    user = User.query.get_or_404(user_id)
    friend = User.query.get_or_404(friend_id)
    message = Message.query.filter_by(sender_id=friend_id, recipient_id=user_id).first()
    if message:
        db.session.delete(message)
        db.session.commit()
    flash(f'Friend request from {friend.name} declined', 'success')
    return redirect(url_for('messages'))

@app.route('/add_game/<int:user_id>', methods=['GET', 'POST'])
def add_game(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        game_name = request.form['game_name']
        game = Game.query.filter_by(name=game_name).first()
        if not game:
            game = Game(name=game_name)
            db.session.add(game)
        user.games.append(game)
        db.session.commit()
        flash(f'Game {game_name} added successfully!', 'success')
        return redirect(url_for('profile', user_id=user.id))
    return render_template('add_game.html', user=user)

# Запуск приложения
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
