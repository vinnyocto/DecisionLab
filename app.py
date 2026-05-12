from flask import Flask, render_template, request, redirect, url_for, session
from flask_login import LoginManager, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User
from coinflip import run_simulation
from blackjack import blackjack_bp

app = Flask(__name__)

app.config["SECRET_KEY"] = "secretkey"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Register blueprints
app.register_blueprint(blackjack_bp)


@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template("signup.html", error="Username already taken. Try another one.")

        hashed_password = generate_password_hash(password)

        user = User(username=username, password_hash=hashed_password)
        db.session.add(user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("dashboard"))

        return "Invalid credentials ❌"

    return render_template("login.html")


@app.route("/logout")
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/simulate", methods=["GET", "POST"])
@login_required
def simulate():
    if request.method == "POST":
        trials = int(request.form["trials"])
        starting_money = int(request.form["money"])
        bet_amount = int(request.form["bet"])

        result = run_simulation(trials, starting_money, bet_amount)

        return render_template(
            "simulate_results.html",
            starting_money=starting_money,
            final_money=result["final_money"],
            profit=result["profit"],
            wins=result["wins"],
            losses=result["losses"],
            history=result["history"],
            win_rate=result["win_rate"],
            max_drawdown=result["max_drawdown"],
            trials=trials
        )

    return render_template("simulate.html")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)