from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from config import Config
from models import db, User, Habit, HabitCheck
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import date, timedelta
import os

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# simple quotes for achievements
MOTIVATIONAL_QUOTES = [
    "Small steps every day.",
    "Consistency is the secret sauce.",
    "One more day. You're doing great!",
    "Every check counts — keep going!",
    "Streaks build champions."
]

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_first_request
def create_tables():
    db.create_all()

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('base.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        if not username or not password:
            flash("Please provide username and password")
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash("Username already taken")
            return redirect(url_for('register'))
        u = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(u)
        db.session.commit()
        flash("Registered! Please login.")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash("Invalid credentials")
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        # create habit
        name = request.form.get('name', '').strip()
        if name:
            h = Habit(name=name, user=current_user)
            db.session.add(h)
            db.session.commit()
            flash("Habit added")
        return redirect(url_for('dashboard'))

    habits = Habit.query.filter_by(user_id=current_user.id).all()

    # compute streaks and last check info per habit
    habit_info = []
    for h in habits:
        checks = sorted([c.date for c in h.checks])
        today = date.today()
        # was done today?
        done_today = any(c == today for c in checks)
        # compute streak: consecutive days ending today
        streak = 0
        d = today
        while any(c == d for c in checks):
            streak += 1
            d = d - timedelta(days=1)
        # achievements simple
        achievement = None
        if streak > 0 and streak % 7 == 0:
            achievement = f"Great! {streak}-day streak!"
        habit_info.append({
            "habit": h,
            "done_today": done_today,
            "streak": streak,
            "achievement": achievement
        })

    # a motivational quote random-ish by user id and num habits
    quote = MOTIVATIONAL_QUOTES[(current_user.id + len(habits)) % len(MOTIVATIONAL_QUOTES)]

    return render_template('dashboard.html', habit_info=habit_info, quote=quote)

@app.route('/habit/<int:habit_id>/delete', methods=['POST'])
@login_required
def delete_habit(habit_id):
    h = Habit.query.get_or_404(habit_id)
    if h.user_id != current_user.id:
        flash("Not allowed")
        return redirect(url_for('dashboard'))
    # delete checks first
    HabitCheck.query.filter_by(habit_id=habit_id).delete()
    db.session.delete(h)
    db.session.commit()
    flash("Habit deleted")
    return redirect(url_for('dashboard'))

@app.route('/habit/<int:habit_id>/mark', methods=['POST'])
@login_required
def mark_habit(habit_id):
    h = Habit.query.get_or_404(habit_id)
    if h.user_id != current_user.id:
        flash("Not allowed")
        return redirect(url_for('dashboard'))
    today = date.today()
    existing = HabitCheck.query.filter_by(habit_id=habit_id, date=today).first()
    if existing:
        flash("Already marked today")
    else:
        check = HabitCheck(habit_id=habit_id, date=today)
        db.session.add(check)
        db.session.commit()
        flash("Marked as done for today! 🎉")
    return redirect(url_for('dashboard'))

@app.route('/habit/<int:habit_id>/progress')
@login_required
def habit_progress(habit_id):
    h = Habit.query.get_or_404(habit_id)
    if h.user_id != current_user.id:
        flash("Not allowed")
        return redirect(url_for('dashboard'))

    # Build weekly data for last 30 days
    today = date.today()
    days = [today - timedelta(days=i) for i in range(29, -1, -1)]  # last 30 days
    dates = [d for d in days]
    checks = {c.date for c in h.checks}
    values = [1 if d in checks else 0 for d in dates]

    # plot bar + line showing streak progression
    fig, ax = plt.subplots(figsize=(10,4))
    ax.bar(range(len(dates)), values)
    # line for rolling sum (7-day completion)
    rolling = []
    for i in range(len(values)):
        window = values[max(0, i-6):i+1]
        rolling.append(sum(window))
    ax2 = ax.twinx()
    ax2.plot(range(len(dates)), rolling, linestyle='-', marker='o')
    ax.set_title(f"Progress for: {h.name}")
    ax.set_xlabel("Days (last 30)")
    ax.set_ylabel("Done (0/1)")
    ax2.set_ylabel("7-day completed count")

    fig.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close(fig)
    return send_file(buf, mimetype='image/png')

if __name__ == '__main__':
    # create app context for initial db create if run directly
    with app.app_context():
        db.create_all()
    app.run(debug=True)
