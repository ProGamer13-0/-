import pytest
from app import app as flask_app, db as _db
from app import User, Workout

@pytest.fixture(scope='session')
def test_app():
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['WTF_CSRF_ENABLED'] = False

    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.drop_all()

@pytest.fixture(scope='function')
def client(test_app):
    return test_app.test_client()

@pytest.fixture(scope='function')
def init_database(test_app):
    with test_app.app_context():
        user = User(username="testuser", role="user", password="password")
        _db.session.add(user)
        _db.session.commit()
        yield _db
        _db.session.remove()
        _db.drop_all()
        _db.create_all()
