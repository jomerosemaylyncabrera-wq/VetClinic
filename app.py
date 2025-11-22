from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "petclinic_secret_key"

# Database setup
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///petclinic.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "static/doctorpics"
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2MB max upload size
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
db = SQLAlchemy(app)

# Ensure photo directory exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# MODELS
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100))
    address = db.Column(db.String(100))
    appointments = db.relationship("Appointment", backref="user", lazy=True)

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    specialty = db.Column(db.String(80), nullable=False)
    photo_url = db.Column(db.String(255), nullable=True)
    schedule = db.Column(db.String(255), nullable=False)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.id"), nullable=False)
    pet_name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default="Pending")
    reason = db.Column(db.String(255))
    doctor = db.relationship("Doctor", backref="appointments")

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)

# ----- INITIAL DATA -----
def init_data():
    db.create_all()
    if not Admin.query.filter_by(username="admin").first():
        admin = Admin(username="admin", password="admin123")
        db.session.add(admin)
    if Doctor.query.count() == 0:
        demo_doctors = [
            Doctor(name="Dr. Jamie Vet", specialty="Cats & Dogs", photo_url="/static/doctor1.png", schedule="Mon-Fri 9am-3pm"),
            Doctor(name="Dr. Sam Rabbit", specialty="Rabbits & Small Pets", photo_url="/static/doctor2.png", schedule="Tue-Thu 10am-4pm"),
            Doctor(name="Dr. Liz Fish", specialty="Aquatic Animals", photo_url="/static/doctor3.png", schedule="Wed-Sat 1pm-6pm")
        ]
        db.session.add_all(demo_doctors)
    db.session.commit()

with app.app_context():
    init_data()

# ---- ROUTES ----
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]
        contact = request.form.get("contact", "")
        address = request.form.get("address", "")
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for("register"))
        new_user = User(name=name, email=email, password=password, contact=contact, address=address)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session["user_id"] = user.id
            session["user_name"] = user.name
            flash("Welcome!", "success")
            return redirect(url_for("pet_owner_dashboard"))
        else:
            flash("Invalid email or password", "danger")
    return render_template("login.html")

@app.route("/pet_owner_dashboard")
def pet_owner_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    current_user = User.query.get(session["user_id"])
    doctors = Doctor.query.all()
    appointments = Appointment.query.filter_by(user_id=current_user.id).order_by(Appointment.date.desc()).all()

    return render_template("pet_owner_dashboard.html",
        current_user=current_user,
        doctors=doctors,
        appointments=appointments
    )

@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    if request.method == "POST":
        user.name = request.form["fullname"]
        user.email = request.form["email"]
        user.contact = request.form.get("contact", "")
        user.address = request.form.get("address", "")
        db.session.commit()
        flash("Profile updated!", "success")
        return redirect(url_for("pet_owner_dashboard"))
    return render_template("edit_profile.html", current_user=user)

@app.route("/book", methods=["GET", "POST"])
def book():
    if "user_id" not in session:
        return redirect(url_for("login"))

    doctors = Doctor.query.all()
    selected_doctor_id = request.args.get("doctor_id")  # pre-select doctor if clicked from dashboard

    if request.method == "POST":
        pet_name = request.form["pet_name"]
        doctor_id = request.form["doctor_id"]
        date = request.form["date"]
        time = request.form["time"]
        reason = request.form["reason"]

        appointment = Appointment(
            user_id=session["user_id"],
            doctor_id=doctor_id,
            pet_name=pet_name,
            date=date,
            time=time,
            reason=reason,
            status="Pending"
        )
        db.session.add(appointment)
        db.session.commit()
        flash("Appointment booked successfully!", "success")
        return redirect(url_for("pet_owner_dashboard"))

    return render_template("book.html", doctors=doctors, selected_doctor_id=selected_doctor_id)

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

@app.route("/dashboard")
def dashboard():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    appointments = Appointment.query.order_by(Appointment.date.desc()).all()
    # Pass doctors to the dashboard template so the template can render the doctors list
    doctors = Doctor.query.all()
    return render_template("dashboard.html", appointments=appointments, doctors=doctors)

@app.route("/add_doctor", methods=["GET", "POST"])
def add_doctor():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        name = request.form["name"]
        specialty = request.form["specialty"]
        schedule = request.form["schedule"]

        photo_url = None
        if "photo" in request.files and request.files["photo"].filename != "":
            file = request.files["photo"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                # Avoid overwrite
                i = 1
                orig_filename = filename
                while os.path.exists(filepath):
                    name_part, ext_part = os.path.splitext(orig_filename)
                    filename = f"{name_part}_{i}{ext_part}"
                    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    i += 1
                file.save(filepath)
                photo_url = f"/static/doctorpics/{filename}"
            else:
                flash("Invalid image file type. Allowed types: png, jpg, jpeg, gif.", "danger")
                return redirect(url_for("add_doctor"))

        new_doctor = Doctor(name=name, specialty=specialty, schedule=schedule, photo_url=photo_url)
        db.session.add(new_doctor)
        db.session.commit()
        flash("Doctor added successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("add_doctor.html")

@app.route("/update_status/<int:appointment_id>/<string:status>")
def update_status(appointment_id, status):
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.status = status
    db.session.commit()
    flash(f"Appointment {status}!", "info")
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    if not os.path.exists("petclinic.db"):
        with app.app_context():
            init_data()
    app.run(debug=True)