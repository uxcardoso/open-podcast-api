from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

from podcast_api.application import create_app
from podcast_api.models import db, Podcast, Episode


app = create_app()

migrate = Migrate(app, db)
manager = Manager(app)


manager.add_command('db', MigrateCommand)


@manager.shell
def shell_ctx():
    return dict(
        app=app,
        db=db,
        Podcast=Podcast,
        Episode=Episode
    )


if __name__ == '__main__':
    manager.run()
