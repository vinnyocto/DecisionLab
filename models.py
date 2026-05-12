from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

# ✅ NEW TABLE
class BlackjackResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    result = db.Column(db.String(10))  # win / loss / push

    wager = db.Column(db.Integer)
    bankroll_after = db.Column(db.Integer)

    player_total = db.Column(db.Integer)
    dealer_total = db.Column(db.Integer)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)