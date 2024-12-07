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

# Модели базы данных
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    steam_id = db.Column(db.String(50), unique=True, nullable=True)
    name = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    games = db.relationship('Game', secondary='user_games', backref=db.backref('users', lazy='dynamic'))
    friends = db.relationship('User', secondary='friendships',
                            primaryjoin='User.id==friendships.c.user_id',
                            secondaryjoin='User.id==friendships.c.friend_id',
                            backref=db.backref('friends_of', lazy='dynamic'), lazy='dynamic')
    messages = db.relationship('Message', backref='sender', lazy='dynamic')


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

# Маршруты
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        bio = request.form.get('bio', 'No bio')
        user = User(name=name, bio=bio)
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        flash('User registered successfully!', 'success')
        return redirect(url_for('profile', user_id=user.id))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        user = User.query.filter_by(name=name).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('profile', user_id=user.id))
        else:
            flash('User not found', 'danger')
    return render_template('login.html')

@app.route('/profile/<int:user_id>')
def profile(user_id):
    user = User.query.get_or_404(user_id)
    if not user.steam_id:
        flash('Please link your Steam profile to use this feature.', 'warning')
        return redirect(url_for('link_steam', user_id=user.id))
    return render_template('profile.html', user=user)

@app.route('/link_steam/<int:user_id>', methods=['GET', 'POST'])
def link_steam(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        steam_id = request.form['steam_id']
        user.steam_id = steam_id
        db.session.commit()
        flash('Steam profile linked successfully!', 'success')
        return redirect(url_for('profile', user_id=user.id))
    return render_template('link_steam.html', user=user)

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
        return render_template('search.html', games=games)
    return render_template('search.html')

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
