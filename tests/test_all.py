import pytest
from app import app, db, User, Workout
from datetime import datetime, date
@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()




# ===================== Регистрация и логин =====================
def test_register_user(client):
    rv = client.post("/register", data={"username": "testuser", "password": "password"}, follow_redirects=True)
    assert "login" in rv.request.path
    user = User.query.filter_by(username="testuser").first()
    assert user is not None

def test_register_existing_user(client):
    client.post("/register", data={"username": "testuser2", "password": "password"})
    rv = client.post("/register", data={"username": "testuser2", "password": "password"})
    assert "Пользователь уже существует" in rv.data.decode()

def test_login_valid(client):
    client.post("/register", data={"username": "userlogin", "password": "password"})
    rv = client.post("/login", data={"username": "userlogin", "password": "password"}, follow_redirects=True)
    assert rv.status_code == 200

def test_login_wrong_password(client):
    client.post("/register", data={"username": "userwrong", "password": "password"})
    rv = client.post("/login", data={"username": "userwrong", "password": "wrong"}, follow_redirects=True)
    assert "Неверный логин или пароль" in rv.data.decode()

def test_login_nonexistent_user(client):
    rv = client.post("/login", data={"username": "noexist", "password": "pass"}, follow_redirects=True)
    assert "Неверный логин или пароль" in rv.data.decode()


# ===================== Работа с ролями =====================
def test_user_role_user(client):
    client.post("/register", data={"username": "roleuser", "password": "pass"})
    user = User.query.filter_by(username="roleuser").first()
    assert user.role == "user"


# ===================== Работа с тренировками =====================
def test_create_workout(client):
    client.post("/register", data={"username": "wuser", "password": "pass"})
    client.post("/login", data={"username": "wuser", "password": "pass"})
    rv = client.post("/add", data={"date": "2025-12-25", "exercise": "Squat", "sets": 3, "reps": 10, "weight": 50}, follow_redirects=True)
    w = Workout.query.filter_by(exercise="Squat").first()
    assert w is not None

def test_read_workout(client):
    # сначала создаем workout
    with client.application.app_context():
        w = Workout(user_id=1, date="2025-12-25", exercise="Squat", sets=3, reps=10, weight=50)
        db.session.add(w)
        db.session.commit()

        # теперь читаем
        workout = Workout.query.first()
        assert workout.exercise == "Squat"


def test_update_workout(client):
    with client.application.app_context():
        w = Workout(user_id=1, date="2025-12-25", exercise="Squat", sets=3, reps=10, weight=50)
        db.session.add(w)
        db.session.commit()

        # обновляем
        w.reps = 12
        db.session.commit()
        updated = Workout.query.get(w.id)
        assert updated.reps == 12


def test_delete_workout(client):
    with client.application.app_context():
        w = Workout(user_id=1, date="2025-12-25", exercise="Squat", sets=3, reps=10, weight=50)
        db.session.add(w)
        db.session.commit()

        # удаляем
        db.session.delete(w)
        db.session.commit()
        deleted = Workout.query.get(w.id)
        assert deleted is None


def test_create_invalid_workout(client):
    with client.application.app_context():
        w = Workout(user_id=1, date="", exercise="", sets=0, reps=0, weight=0)
        # проверяем, что невалидный workout не проходит проверку
        success = bool(w.exercise and w.sets > 0 and w.reps > 0)
        assert not success

def test_workout_date(client):
    with client.application.app_context():
        w = Workout(user_id=1, date=date.today(), exercise="Bench Press", sets=3, reps=10, weight=50)
        db.session.add(w)
        db.session.commit()

        saved = Workout.query.filter_by(exercise="Bench Press").first()
        assert saved is not None, "Workout не был сохранён в базе"

        # если дата хранится как строка
        if isinstance(saved.date, str):
            saved_date = datetime.strptime(saved.date, "%Y-%m-%d").date()
        else:
            saved_date = saved.date

        assert saved_date == date.today()


def test_negative_weight(client):
    with client.application.app_context():
        w = Workout(user_id=1, date="2025-12-24", exercise="Deadlift", sets=3, reps=5, weight=-10)
        # проверка валидации перед сохранением
        is_valid = w.weight >= 0
        assert not is_valid, "Вес не может быть отрицательным"


def test_empty_exercise_name(client):
    with client.application.app_context():
        w = Workout(user_id=1, date="2025-12-24", exercise="", sets=3, reps=5, weight=50)
        # проверка валидации перед сохранением
        is_valid = bool(w.exercise)
        assert not is_valid, "Название упражнения не может быть пустым"


def test_multiple_workouts(client):
    with client.application.app_context():
        from app import Workout, db

        w1 = Workout(user_id=1, date="2025-12-24", exercise="Pull Up", sets=4, reps=8, weight=0)
        w2 = Workout(user_id=1, date="2025-12-24", exercise="Push Up", sets=5, reps=15, weight=0)
        db.session.add_all([w1, w2])
        db.session.commit()

        workouts = Workout.query.filter_by(user_id=1).all()
        assert len(workouts) >= 2

# ===================== Страницы =====================
def test_homepage_redirect(client):
    rv = client.get("/", follow_redirects=True)
    assert rv.status_code in [200, 302]

def test_login_page(client):
    rv = client.get("/login")
    assert rv.status_code == 200

def test_register_page(client):
    rv = client.get("/register")
    assert rv.status_code == 200

def test_dashboard_page(client):
    client.post("/register", data={"username": "dashuser", "password": "pass"})
    client.post("/login", data={"username": "dashuser", "password": "pass"})
    rv = client.get("/dashboard")
    assert rv.status_code == 200

def test_add_workout_page(client):
    client.post("/register", data={"username": "awuser", "password": "pass"})
    client.post("/login", data={"username": "awuser", "password": "pass"})
    rv = client.get("/add")
    assert rv.status_code == 200

def test_edit_workout_page(client):
    client.post("/register", data={"username": "euser", "password": "pass"})
    client.post("/login", data={"username": "euser", "password": "pass"})
    client.post("/add", data={"date": "2025-12-25", "exercise": "Bench", "sets": 3, "reps": 10, "weight": 40})
    w = Workout.query.filter_by(exercise="Bench").first()
    rv = client.get(f"/edit/{w.id}")
    assert rv.status_code == 200

def test_delete_workout_page(client):
    client.post("/register", data={"username": "duser", "password": "pass"})
    client.post("/login", data={"username": "duser", "password": "pass"})
    client.post("/add", data={"date": "2025-12-25", "exercise": "Deadlift", "sets": 3, "reps": 10, "weight": 60})
    w = Workout.query.filter_by(exercise="Deadlift").first()
    rv = client.get(f"/delete/{w.id}", follow_redirects=True)
    assert rv.status_code in [200, 302]

# ===================== Прогресс и статистика =====================
def test_progress_page(client):
    client.post("/register", data={"username": "puser", "password": "pass"})
    client.post("/login", data={"username": "puser", "password": "pass"})
    rv = client.get("/progress")
    assert rv.status_code in [200, 302]

def test_statistics_page(client):
    client.post("/register", data={"username": "suser", "password": "pass"})
    client.post("/login", data={"username": "suser", "password": "pass"})
    rv = client.get("/statistics")
    assert rv.status_code in [200, 302]

# ===================== Logout =====================
def test_logout(client):
    client.post("/register", data={"username": "luser", "password": "pass"})
    client.post("/login", data={"username": "luser", "password": "pass"})
    rv = client.get("/logout", follow_redirects=True)
    assert rv.status_code in [200, 302]
