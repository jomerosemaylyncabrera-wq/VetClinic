from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = "petclinic_secret_key"

# Database setup
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///petclinic.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# --------------------- MODELS ---------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    appointments = db.relationship("Appointment", backref="user", lazy=True)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    pet_name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), default="Pending")

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)

# --------------------- INITIALIZE ADMIN ---------------------
# --------------------- INITIALIZE ADMIN ---------------------
with app.app_context():
    db.create_all()
    if not Admin.query.filter_by(username="admin").first():
        admin = Admin(username="admin", password="admin123")
        db.session.add(admin)
        db.session.commit()


# --------------------- ROUTES ---------------------
@app.route("/")
def home():
    return render_template("index.html")

# ----- User Register -----
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        fullname = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for("register"))

        new_user = User(fullname=fullname, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

# ----- User Login -----
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session["user_id"] = user.id
            session["fullname"] = user.fullname
            return redirect(url_for("book"))
        else:
            flash("Invalid email or password", "danger")
    return render_template("login.html")

# ----- Admin Login -----
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        admin = Admin.query.filter_by(username=username, password=password).first()
        if admin:
            session["admin"] = True
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid admin credentials", "danger")
    return render_template("admin_login.html")

# ----- Book Appointment -----
@app.route("/book", methods=["GET", "POST"])
def book():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        pet_name = request.form["pet_name"]
        date = request.form["date"]
        time = request.form["time"]
        reason = request.form["reason"]
        appointment = Appointment(
            user_id=session["user_id"],
            pet_name=pet_name,
            date=date,
            time=time,
            reason=reason,
            status="Pending"
        )
        db.session.add(appointment)
        db.session.commit()
        flash("Appointment booked successfully!", "success")
        return redirect(url_for("book"))

    user_appointments = Appointment.query.filter_by(user_id=session["user_id"]).all()
    return render_template("book.html", appointments=user_appointments)

# ----- Admin Dashboard -----
@app.route("/dashboard")
def dashboard():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    appointments = Appointment.query.all()
    return render_template("dashboard.html", appointments=appointments)

# ----- Update Appointment Status -----
@app.route("/update_status/<int:appointment_id>/<string:status>")
def update_status(appointment_id, status):
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.status = status
    db.session.commit()
    flash(f"Appointment {status}!", "info")
    return redirect(url_for("dashboard"))

# ----- Logout -----
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# --------------------- RUN APP ---------------------
if __name__ == "__main__":
    if not os.path.exists("petclinic.db"):
        with app.app_context():
            db.create_all()
    app.run(debug=True)
