from flask import Blueprint
from flask_restful import Resource, Api, request, current_app
from sqlalchemy_pagination import paginate
import sqlalchemy.exc as ext
from sqlalchemy import and_
import re

import feedparser

from functools import wraps
from datetime import datetime, timedelta

import jwt

from .models import db, Episode, Podcast, User, Subscribe

api = Blueprint('api', __name__)
api_podcast = Api(api)


def token_required(f):
    @wraps(f)
    def _verify(*args, **kwargs):
        auth_readers = request.headers.get('Authorization', '').split()
        invalid_msg = {
            'message': 'Token inválido. Registro e / ou autenticação requeridos',
            'authenticated': False
        }
        expired_msg = {
            'message': 'Token expirado. Reautenticação necessária.',
            'authenticated': False
        }

        try:
            token = auth_readers[0]
            data = jwt.decode(token, current_app.config['SECRET_KEY'])
            user = User.query.filter(User.email == data['sub']).first()
            if not user:
                raise RuntimeError('Usuário não encontrado')
            return f(user, **kwargs)

        except jwt.ExpiredSignatureError:

            return expired_msg, 401
        except(jwt.InvalidTokenError, Exception) as e:

            print(e)
            return invalid_msg, 401

    return _verify


class IndexResource(Resource):
    def get(self):
        return {'msg': 'Bem vindo a API OpenPodcast'}


class PodcastResource(Resource):
    @token_required
    def get(self):
        q = request.args.get('q')
        if q:
            podcasts = Podcast.query.filter(Podcast.name.ilike(f'%{q}%')).all()
        else:
            podcasts = Podcast.query.all()
        return {'podcasts': [p.to_dict() for p in podcasts]}, 200

    @token_required
    def post(self):

        try:

            data = request.get_json()
            url_rss = data.get('url_rss')
            feed = feedparser.parse(url_rss)
            name_podcast = feed['feed']['title']
            description = feed['feed']['description']
            image = feed['feed']['image']['href']

            podcast = Podcast.query.filter(Podcast.name == name_podcast and Podcast.url_feed == url_rss).first()
            if podcast:
                return {'error': 'O podcast já existe no sistema'}

            podcast = Podcast(name=name_podcast, description=description, image=image, url_feed=url_rss)
            entradas = feed['entries']
            episodes = []

            for item in entradas:
                name_apisode = item.title
                description = item.content[0].value

                for link in item.links:
                    if 'audio' in link.type:
                        url_audio = link.href
                        break

                episode = Episode(
                    name=name_apisode,
                    description=description,
                    link_audio=url_audio
                )

                episodes.append(episode)

            podcast.episodes = episodes

            db.session.add(podcast)
            db.session.commit()

            return {'message': f'podcast {name_podcast} importado com sucesso'}

        except Exception as e:
            print(e)
            return {'error': 'erro ao importar o podcast'}


class EpisodesResource(Resource):
    @token_required
    def get(self, id):

        num_page = int(request.args.get('page')) if request.args.get('page') else 1
        limit_items = int(request.args.get('limit')) if request.args.get('limit') else 25
        q = request.args.get('q')

        if q:
            page = paginate(
                Episode.query.filter(
                    and_(Episode.name.ilike(f'%{q}%'), Episode.podcast_id == id)
                ), num_page, limit_items
            )
        else:
            page = paginate(Episode.query.filter(Episode.podcast_id == id), num_page, limit_items)

        num_pages = page.pages
        total_itens = page.total

        return {
                    'page': num_page,
                    'total_itens': total_itens,
                    'total_pages': num_pages,
                    'episodes': [e.to_dict() for e in page.items]
               }, 200


class RegisterUserResource(Resource):
    def post(self):
        try:
            data = request.get_json()
            validator_email = re.match(r'[^@]+@[^@]+\.[^@]+', data['email'])
            if not validator_email:
                return {'error': 'email não é válido'}
            user = User(**data)
            db.session.add(user)
            db.session.commit()

            return user.to_dict(), 201
        except ext.IntegrityError:
            return {'error': 'usuario já registrado'}, 409


class LoginUserResource(Resource):
    def post(self):
        data = request.get_json()
        user = User.authenticate(**data)
        if not user:
            return {'message': 'credenciais inválidas', 'authenticated': False}, 401

        token = jwt.encode({
            'sub': user.email,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(minutes=60)},
            current_app.config['SECRET_KEY']
        )

        return {'token': token.decode('UTF-8')}


class UserResource(Resource):
    @token_required
    def get(self):
        return self.to_dict(), 200


class UserSubscriptions(Resource):
    @token_required
    def get(self):
        subscriptions = Subscribe.query.filter(Subscribe.user_id == self.id).all()
        podcasts_id = [x.to_dict()['podcast_id'] for x in subscriptions]

        podcasts = Podcast.query.all()
        podcasts = [p.to_dict() for p in podcasts for id in podcasts_id if p.id == id]
        return {'subscriptions': podcasts}


class SubscribeResource(Resource):
    @token_required
    def get(self, podcast_id):
        podcast = Podcast.query.get(podcast_id)
        if not podcast:
            return {'error': 'podcast não encontrado'}, 401
        sub = Subscribe.query.filter(Subscribe.podcast_id == podcast_id and Subscribe.user_id == self.id).first()
        if sub:
            return {'error': 'você já é inscrito nesse podcast'}
        try:
            subscribe = Subscribe(podcast_id=podcast_id, user_id=self.id)
            db.session.add(subscribe)
            db.session.commit()
            return {'success': 'inscrição realizada do sucesso'}
        except Exception as e:
            print(e)
            return {'error': 'erro ao se inscrever'}

    @token_required
    def delete(self, podcast_id):
        try:
            subscriptions = Subscribe.query.filter(
                and_(Subscribe.user_id == self.id, Subscribe.podcast_id == podcast_id)).first()
            db.session.delete(subscriptions)
            db.session.commit()
            return {'message': 'inscrição cancelada con sucesso'}, 201
        except:
            return {'error': 'erro ao cancelar inscricao'}


# Routes

api_podcast.add_resource(IndexResource, '/')
api_podcast.add_resource(PodcastResource, '/podcast/')
api_podcast.add_resource(EpisodesResource, '/podcast/<int:id>/')
api_podcast.add_resource(SubscribeResource, '/podcast/<int:podcast_id>/subscribe/')


api_podcast.add_resource(RegisterUserResource, '/auth/register')
api_podcast.add_resource(LoginUserResource, '/auth/login')

api_podcast.add_resource(UserResource, '/user/')
api_podcast.add_resource(UserSubscriptions, '/user/subscriptions')
