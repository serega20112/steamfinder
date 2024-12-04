from flask import Flask, request, jsonify, abort, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import json
import requests
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'  # Секретный ключ для сессий
db = SQLAlchemy(app)

# Инициализация защиты CSRF
csrf = CSRFProtect(app)

# Инициализация лимитера
limiter = Limiter(app)

# Модель пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    steam_id = db.Column(db.String(100), unique=True, nullable=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=True)  # Пароль может быть пустым для пользователей, вошедших через Steam

# Регистрация пользователя
@app.route('/register', methods=['POST'])
@limiter.limit("5 per minute")  # Ограничение на 5 регистраций в минуту
def register():
    data = request.json
    if not all(key in data for key in ('username', 'password')):
        abort(400, 'Missing data')

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': 'Username already exists!'}), 400

    new_user = User(
        username=data['username'],
        password=generate_password_hash(data['password'])
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User  registered successfully!'}), 201

# Вход пользователя
@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")  # Ограничение на 5 попыток входа в минуту
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password, data['password']):
        token = jwt.encode({'user_id': user.id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)}, app.secret_key)
        return jsonify({'token': token}), 200
    return jsonify({'message': 'Invalid credentials!'}), 401

# Вход пользователя через Steam
@app.route('/login/steam', methods=['GET'])
def login_steam():
    return redirect("https://steamcommunity.com/openid/login?openid.ns=http://specs.openid.net/auth/2.0&openid.mode=checkid_setup&openid.return_to=http://localhost:5000/steam/authorized&openid.realm=http://localhost:5000&openid.identity=http://specs.openid.net/auth/2.0/identifier_select")

# Обработка авторизации через Steam
@app.route('/steam/authorized')
def steam_authorized():
    openid_response = request.args
    if 'openid.mode' in openid_response and openid_response['openid.mode'] == 'id_res':
        steam_id = openid_response['openid.claimed_id'].split('/')[-1]
        
        user_info = requests.get(f'https://api.steampowered.com/ISteamUser /GetPlayerSumm aries/v0002/?steamids={steam_id}')
        if user_info.status_code != 200:
            return jsonify({'message': 'Не удалось получить информацию о пользователе из Steam!'}), 400
        
        user_data = user_info.json().get('response', {}).get('players', [{}])[0]

        user = User.query.filter_by(steam_id=user_data['steamid']).first()
        if not user:
            user = User(
                steam_id=user_data['steamid'],
                username=user_data['personaname']
            )
            db.session.add(user)
            db.session.commit()

        return jsonify({'message': 'Пользователь успешно зарегистрирован!', 'user': user_data}), 200
    return jsonify({'message': 'Авторизация не удалась!'}), 400

# Выход пользователя
@app.route('/logout', methods=['GET'])
def logout():
    return jsonify({'message': 'Вы вышли из системы!'}), 200

# Профиль пользователя
@app.route('/profile', methods=['GET', 'PUT'])
def profile():
    if request.method == 'GET':
        user_id = request.args.get('user_id')
        user = User.query.get(user_id)
        if user:
            return jsonify({
                'username': user.username,
                'steam_id': user.steam_id
            }), 200
        return jsonify({'message': 'Пользователь не найден!'}), 404

    if request.method == 'PUT':
        user_id = request.args.get('user_id')
        user = User.query.get(user_id)
        if user:
            data = request.json
            user.username = data.get('username', user.username)
            db.session.commit()
            return jsonify({'message': 'Профиль успешно обновлен!'}), 200
        return jsonify({'message': 'Пользователь не найден!'}), 404

# Запуск приложения
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)