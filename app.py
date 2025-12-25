from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, current_user, logout_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask import flash, render_template

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret123'  # можно поменять
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///training_new.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = "login"

# Модели
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'user' или 'admin'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(db.Integer, db.ForeignKey('workout.id'))
    coach_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # тренер
    content = db.Column(db.String(500))
    date = db.Column(db.String(20))



@app.context_processor
def inject_now():
    return {'now': datetime.now}

@app.route("/admin")
@login_required
def admin_dashboard():  # единый маршрут
    if current_user.role != 'admin':
        return "Доступ запрещён"
    users = User.query.all()
    return render_template("admin.html", users=users)


@app.route("/admin/delete/<int:user_id>")
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return "Доступ запрещён"
    user = User.query.get(user_id)
    if user:
        # сначала удаляем все тренировки пользователя
        Workout.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for("admin_dashboard"))  # было admin_panel

def register_user(username, password, role="user"):
    if User.query.filter_by(username=username).first():
        return None  # пользователь уже есть
    user = User(username=username, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user

@app.route("/admin")
@login_required
def admin_page():
    if current_user.role != 'admin':
        return "Доступ запрещён"
    users = User.query.all()
    return render_template("admin.html", users=users)

def create_workout(user_id, date, exercise, sets, reps, weight):
    workout = Workout(
        user_id=user_id,
        date=date,
        exercise=exercise,
        sets=sets,
        reps=reps,
        weight=weight
    )
    db.session.add(workout)
    db.session.commit()
    return workout

@app.route("/coach")
@login_required
def coach_dashboard():
    if current_user.role != 'coach':
        return "Доступ только для тренера"

    users = User.query.filter(User.role == 'user').all()
    users_progress = {}

    for user in users:
        workouts = Workout.query.filter_by(user_id=user.id).order_by(Workout.date).all()
        # добавляем к каждому Workout его комментарии
        for w in workouts:
            w.comments = Comment.query.filter_by(workout_id=w.id).all()
        users_progress[user.username] = workouts  # сразу объекты Workout

    return render_template("coach.html", users_progress=users_progress)


@app.route("/coach/comment/<int:workout_id>", methods=["POST"])
@login_required
def add_comment(workout_id):
    if current_user.role != 'coach':
        return "Доступ только для тренера"

    content = request.form.get("content")
    if content:
        comment = Comment(
            workout_id=workout_id,
            coach_id=current_user.id,
            content=content,
            date=datetime.now().strftime("%Y-%m-%d")
        )
        db.session.add(comment)
        db.session.commit()
    return redirect(url_for("coach_dashboard"))



class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.String(20))
    exercise = db.Column(db.String(100))
    sets = db.Column(db.Integer)
    reps = db.Column(db.Integer)
    weight = db.Column(db.Float)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_panel'))
        else:
            return redirect(url_for('dashboard'))
    return redirect(url_for("login"))

@app.route("/admin")
@login_required
def admin_panel():
    if current_user.role != 'admin':
        return "Доступ запрещён"
    users = User.query.all()
    return render_template("admin.html", users=users)



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if User.query.filter_by(username=username).first():
            return "Пользователь уже существует"

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # НЕ логиним сразу
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)

            # Редирект в зависимости от роли
            if user.role == 'admin':
                return redirect(url_for("admin_dashboard"))
            elif user.role == 'coach':
                return redirect(url_for("coach_dashboard"))
            else:  # обычный пользователь
                return redirect(url_for("dashboard"))
        else:
            return "Неверный логин или пароль"

    return render_template("login.html")




@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.role != 'user':
        return "Только для обычных пользователей"

    workouts = Workout.query.filter_by(user_id=current_user.id).all()
    total_workouts = len(workouts)
    total_weight = sum(w.weight * w.reps * w.sets for w in workouts)

    # Получаем комментарии для каждой тренировки
    for w in workouts:
        w.comments = Comment.query.filter_by(workout_id=w.id).all()

    return render_template("dashboard.html", workouts=workouts,
                           total_workouts=total_workouts,
                           total_weight=total_weight)




@app.route("/progress")
@login_required
def progress():
    if current_user.role != 'user':
        flash("Доступ разрешён только для обычных пользователей!", "danger")
        return redirect(url_for('index'))

    workouts = Workout.query.filter_by(user_id=current_user.id).order_by(Workout.date).all()
    exercise_progress = {}
    for w in workouts:
        if w.exercise not in exercise_progress:
            exercise_progress[w.exercise] = []
        exercise_progress[w.exercise].append((w.date, w.weight))

    return render_template("progress.html", exercise_progress=exercise_progress)


@app.route("/statistics")
@login_required
def statistics():
    if current_user.role != 'user':
        flash("Доступ разрешён только для обычных пользователей!", "danger")
        return redirect(url_for('index'))

    workouts = Workout.query.filter_by(user_id=current_user.id).all()
    current_year = datetime.now().year
    monthly_stats = {i: 0 for i in range(1, 13)}

    for w in workouts:
        workout_date = datetime.strptime(w.date, "%Y-%m-%d")
        if workout_date.year == current_year:
            monthly_stats[workout_date.month] += w.weight * w.sets * w.reps

    return render_template("statistics.html", monthly_stats=monthly_stats)


# Добавление тренировки
@app.route("/add", methods=["GET", "POST"])
@login_required
def add_workout():
    if current_user.role != 'user':
        return render_template("access_denied.html", message="Только для обычных пользователей")

    if request.method == "POST":
        date = request.form.get("date")
        exercise = request.form.get("exercise")
        sets = int(request.form.get("sets"))
        reps = int(request.form.get("reps"))
        weight = float(request.form.get("weight"))

        workout = Workout(
            user_id=current_user.id,
            date=date,
            exercise=exercise,
            sets=sets,
            reps=reps,
            weight=weight
        )
        db.session.add(workout)
        db.session.commit()
        return redirect(url_for("dashboard"))

    return render_template("add_workout.html")

@app.route("/edit/<int:workout_id>", methods=["GET", "POST"])
@login_required
def edit_workout(workout_id):
    workout = Workout.query.get(workout_id)

    # Проверяем, что это упражнение текущего пользователя
    if workout.user_id != current_user.id or current_user.role != 'user':
        return render_template("access_denied.html", message="Доступ запрещён")

    if request.method == "POST":
        workout.date = request.form.get("date")
        workout.exercise = request.form.get("exercise")
        workout.sets = int(request.form.get("sets"))
        workout.reps = int(request.form.get("reps"))
        workout.weight = float(request.form.get("weight"))

        db.session.commit()
        return redirect(url_for("dashboard"))

    return render_template("edit_workout.html", workout=workout)

@app.route("/delete/<int:workout_id>")
@login_required
def delete_workout(workout_id):
    workout = Workout.query.get(workout_id)

    if workout.user_id != current_user.id or current_user.role != 'user':
        return render_template("access_denied.html", message="Доступ запрещён")

    db.session.delete(workout)
    db.session.commit()
    return redirect(url_for("dashboard"))


# Выход
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# Запуск сервера
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        # Админ
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', role='admin')
            admin_user.set_password('admin123')
            db.session.add(admin_user)

        # Тренер
        if not User.query.filter_by(username='coach').first():
            coach_user = User(username='coach', role='coach')
            coach_user.set_password('coach123')  # пароль для тренера
            db.session.add(coach_user)
            db.session.commit()

        db.session.commit()

    app.run(debug=True)
