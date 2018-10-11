from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Podcast(db.Model):
    __tablename__ = 'podcasts'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    description = db.Column(db.String(500), nullable=False)
    image = db.Column(db.String(200), nullable=False)
    url_feed = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    episodes = db.relationship(
        'Episode', backref='podcast', order_by='Episode.id', lazy="dynamic"
    )

    def to_dict(self):
        return dict(
            id=self.id,
            name=self.name,
            description=self.description,
            image=self.image,
            url_feed=self.url_feed,
            created_at=self.created_at.strftime('%Y-%m-%d %H:%M:%S')

        )


class Episode(db.Model):
    __tablename__ = 'episodes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)
    link_audio = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    podcast_id = db.Column(db.Integer, db.ForeignKey('podcasts.id'))

    def to_dict(self):
        return dict(
            id=self.id,
            name=self.name,
            description=self.description,
            link_audio=self.link_audio,
            created_at=self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            podcast_id=self.podcast_id
        )


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(200), nullable=True)

    def __init__(self, email, password, name):
        self.email = email
        self.password = generate_password_hash(password, method='sha256')
        self.name = name

    @classmethod
    def authenticate(cls, **kwargs):
        email = kwargs.get('email')
        password = kwargs.get('password')

        if not email or not password:
            return None

        user = cls.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password, password):
            return None

        return user

    def to_dict(self):
        return dict(
            id=self.id,
            email=self.email,
            name=self.name
        )


class Subscribe(db.Model):
    __tablename__ = 'subscripes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    podcast_id = db.Column(db.Integer, db.ForeignKey('podcasts.id'))

    def to_dict(self):
        return dict(
            podcast_id=self.podcast_id
        )
