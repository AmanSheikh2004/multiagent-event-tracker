import os, datetime, jwt
from flask import Flask, request, jsonify, send_file
from flask_migrate import Migrate
from config import Config
from models import db, User, Document, ExtractedEntity, Event
from werkzeug.utils import secure_filename
from agents.orchestrator_agent import OrchestratorAgent
from functools import wraps
from flask_cors import CORS
from fpdf import FPDF
from io import BytesIO
import secrets
from werkzeug.security import generate_password_hash
from flask import send_file
from flask import send_from_directory, abort



ALLOWED_EXT = {'pdf', 'png', 'jpg', 'jpeg', 'tiff'}


def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(Config)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    db.init_app(app)
    migrate = Migrate(app, db)

    # ✅ Enable CORS for frontend requests (localhost:3000)
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    orchestrator = OrchestratorAgent()

    # ---------------- AUTH HELPERS ---------------- #
    def token_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = None
            if 'Authorization' in request.headers:
                auth = request.headers['Authorization']
                if auth.startswith("Bearer "):
                    token = auth.split(" ")[1]
            elif 'token' in request.args:
                token = request.args.get('token')

            if not token:
                return jsonify({'message': 'Token is missing'}), 401

            try:
                data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=['HS256'])
                user = User.query.filter_by(username=data['sub']).first()
                if not user:
                    return jsonify({'message': 'User not found'}), 401
                request.user = user
            except Exception as e:
                return jsonify({'message': 'Token invalid', 'error': str(e)}), 401

            # ✅ Pass user explicitly into the wrapped function
            return f(user, *args, **kwargs)
        return decorated



    def role_required(roles):
        def decorator(f):
            @wraps(f)
            def wrapped(*args, **kwargs):
                user = getattr(request, 'user', None)
                if not user or user.role not in roles:
                    return jsonify({'message': 'Forbidden'}), 403
                return f(*args, **kwargs)
            return wrapped
        return decorator

    @app.route('/api/ping')
    def ping():
        return jsonify({'message':'pong'})

    @app.route('/api/auth/login', methods=['POST'])
    def login():
        data = request.json or {}
        username = data.get('username'); password = data.get('password')
        if not username or not password:
            return jsonify({'message':'username and password required'}), 400
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return jsonify({'message':'Invalid credentials'}), 401
        token = jwt.encode({'sub': user.username, 'role': user.role, 'exp': datetime.datetime.utcnow()+datetime.timedelta(hours=8)}, app.config['JWT_SECRET'], algorithm='HS256')
        return jsonify({'token': token, 'user': {'username': user.username, 'role': user.role, 'department': user.department}})

    @app.route('/api/init', methods=['POST'])
    def init_data():
        if User.query.count() == 0:
            u1 = User(username='student1', role='student', department='AIML'); u1.set_password('student1')
            u2 = User(username='teacher1', role='teacher', department='CSE(Core)'); u2.set_password('teacher1')
            u3 = User(username='iqc', role='iqc', department='ALL'); u3.set_password('adminpass')
            db.session.add_all([u1,u2,u3]); db.session.commit()
        return jsonify({'message':'initialized'})

    @app.route('/api/upload', methods=['POST'])
    @token_required
    @role_required(['student','teacher'])
    def upload(current_user):
        if 'file' not in request.files:
            return jsonify({'message':'no file'}), 400

        f = request.files['file']
        if f.filename == '':
            return jsonify({'message':'empty filename'}), 400

        ext = f.filename.rsplit('.', 1)[-1].lower()
        if ext not in ALLOWED_EXT:
            return jsonify({'message':'file type not allowed'}), 400

        filename = secure_filename(f.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        f.save(path)

        # ✅ Mark status as pending review
        doc = Document(filename=filename, uploaded_by=request.user.username, status='needs_review')
        db.session.add(doc)
        db.session.commit()

        # Trigger orchestration
        orchestrator.process_document(doc.id)

        print(f"[Upload] Document {filename} marked as 'needs_review' for validation.")
        return jsonify({'message': 'uploaded', 'document_id': doc.id})


    @app.route('/api/documents', methods=['GET'])
    @token_required
    def get_documents(current_user):
        query = Document.query

        # 🧠 Filter by role
        if current_user.role == 'student':
            query = query.filter_by(uploaded_by=current_user.username)
        elif current_user.role == 'teacher':
            query = query.filter_by(department=current_user.department)
        elif current_user.role == 'iqc':
            pass  # IQC sees all

        documents = query.order_by(Document.uploaded_at.desc()).all()

        return jsonify([{
            "id": d.id,
            "filename": d.filename,
            "status": d.status,
            "uploaded_at": d.uploaded_at.isoformat(),
            "uploaded_by": d.uploaded_by,
            "department": d.department
        } for d in documents])


    @app.route('/api/document/<int:doc_id>', methods=['GET'])
    @token_required
    def doc_detail(current_user, doc_id):
        d = Document.query.get_or_404(doc_id)
        ents = [{'label':e.label,'text':e.text,'confidence':e.confidence} for e in d.entities]
        evs = [{'id':ev.id,'name':ev.name,'date':ev.date.isoformat() if ev.date else None,'department':ev.department,'category':ev.category,'validated':ev.validated} for ev in d.events]
        return jsonify({'document':{'id':d.id,'filename':d.filename,'status':d.status,'raw_text':d.raw_text}, 'entities':ents, 'events':evs})

    @app.route('/api/validate/<int:event_id>', methods=['POST'])
    @token_required
    @role_required(['teacher','iqc'])
    def validate_event(current_user, event_id):
        data = request.json or {}
        ev = Event.query.get_or_404(event_id)
        ev.name = data.get('name', ev.name)
        date_str = data.get('date', None)
        if date_str:
            try:
                ev.date = datetime.date.fromisoformat(date_str)
            except:
                pass
        ev.department = data.get('department', ev.department)
        ev.category = data.get('category', ev.category)
        ev.validated = True
        db.session.commit()
        return jsonify({'message':'validated'})


    @app.route('/api/report/<dept>', methods=['GET'])
    @token_required
    def report(current_user, dept):
        import csv, io
        events = Event.query.filter_by(department=dept).all()
        si = io.StringIO()
        writer = csv.writer(si)
        writer.writerow(['name','date','category','validated'])
        for e in events:
            writer.writerow([e.name, e.date.isoformat() if e.date else '', e.category, e.validated])
        output = io.BytesIO()
        output.write(si.getvalue().encode('utf-8'))
        output.seek(0)
        return send_file(output, as_attachment=True, download_name=f'{dept}_report.csv', mimetype='text/csv')
    
    @app.route("/api/validate/events", methods=["GET"])
    @token_required
    @role_required(["teacher", "iqc"])
    def list_pending_events(current_user):
        try:
            user = request.user

            # 🧑‍🏫 Teachers → See only events from their department that are unvalidated
            if user.role == "teacher":
                events = Event.query.filter_by(validated=False, department=user.department).all()
            
            # 🧑‍💼 IQC → See all unvalidated events from all departments
            elif user.role == "iqc":
                events = Event.query.filter_by(validated=False).all()
            
            else:
                return jsonify({"message": "Forbidden"}), 403

            event_list = []
            for e in events:
                event_list.append({
                    "id": e.id,
                    "name": e.name,
                    "date": e.date.isoformat() if e.date else None,
                    "category": e.category,
                    "department": e.department,
                    "document_id": e.document_id,
                    "uploaded_by": e.document.uploaded_by if e.document else "Unknown",
                    "validated": e.validated
                })

            return jsonify({"events": event_list}), 200

        except Exception as e:
            print("[Error] Event fetch failed:", e)
            return jsonify({"message": "Error fetching events", "error": str(e)}), 500

            
    @app.route('/api/document/<int:doc_id>/file', methods=['GET'])
    @token_required
    def document_file(current_user, doc_id):
        d = Document.query.get_or_404(doc_id)
        filename = d.filename
        upload_dir = app.config.get('UPLOAD_FOLDER', 'uploads')
        try:
            return send_from_directory(upload_dir, filename, as_attachment=False)
        except Exception as e:
            print("File send error:", e)
            abort(404)

    @app.route('/', defaults={'path':''})
    def index(path=''):
        return jsonify({'message':'API Running'})
    
    @app.route('/api/tracker', methods=['GET'])
    @token_required
    @role_required(['iqc'])
    def iqc_tracker(current_user):
        try:
            departments = {
                "AIML": 10,
                "CSE(Core)": 10,
                "ISE": 10,
                "ECE": 10,
                "AERO": 10
            }

            result = {}

            for dept, fixed_total in departments.items():
                validated = Event.query.filter_by(department=dept, validated=True).count()

                # ✅ progress = validated / fixed_total
                progress = round((validated / fixed_total) * 100, 2) if fixed_total > 0 else 0
                result[dept] = {
                    "validated": validated,
                    "total": fixed_total,
                    "progress": progress
                }

            return jsonify(result), 200

        except Exception as e:
            print("[Tracker Error]", e)
            return jsonify({"message": "Error generating tracker data", "error": str(e)}), 500


    @app.route('/api/tracker/<dept>', methods=['GET'])
    @token_required
    @role_required(['iqc', 'teacher', 'student'])
    def department_details(current_user, dept):
        try:
            categories = ["Seminar", "Workshop", "Competitions", "General Event"]
            events = Event.query.filter_by(department=dept, validated=True).all()

            # Group events by category
            grouped = {cat: [] for cat in categories}
            for e in events:
                cat = e.category.strip() if e.category else "General Event"
                if cat not in grouped:
                    grouped[cat] = []
                grouped[cat].append({
                    "id": e.id,
                    "name": e.name,
                    "date": e.date.isoformat() if e.date else None,
                    "category": e.category,
                    "validated": e.validated
                })

            return jsonify({"department": dept, "events_by_category": grouped}), 200

        except Exception as e:
            print("[Department Details Error]", e)
            return jsonify({"message": "Error fetching department details", "error": str(e)}), 500

    @app.route('/api/tracker/<dept>/report', methods=['GET'])
    @token_required
    @role_required(['iqc', 'teacher'])
    def generate_dept_report(current_user, dept):
        try:
            # Path to DSU logo
            logo_path = os.path.join(os.getcwd(), "static", "dsu_logo.png")

            # Fetch validated events
            categories = ["Seminar", "Workshop", "Competitions", "General Event"]
            events = Event.query.filter_by(department=dept, validated=True).all()

            grouped = {cat: [] for cat in categories}
            for e in events:
                cat = e.category.strip() if e.category else "General Event"
                if cat not in grouped:
                    grouped[cat] = []
                grouped[cat].append(e)

            # -------------------- PDF Creation --------------------
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()

            # 🏫 Header Section
            if os.path.exists(logo_path):
                pdf.image(logo_path, 10, 8, 25)

            pdf.set_xy(40, 10)
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, "DAYANANDA SAGAR UNIVERSITY", ln=True, align="C")
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 8, f"Department of {dept}", ln=True, align="C")
            pdf.set_font("Arial", "B", 13)
            pdf.cell(0, 8, "Internal Quality Control (IQC) Report", ln=True, align="C")

            # Blue line
            pdf.set_draw_color(0, 102, 204)
            pdf.set_line_width(1)
            pdf.line(10, 35, 200, 35)
            pdf.ln(12)

            # Info
            pdf.set_font("Arial", "", 12)
            today = datetime.date.today().strftime("%d-%m-%Y")
            pdf.cell(0, 8, "HOD: ____________________", ln=True)
            pdf.cell(0, 8, f"Date Generated: {today}", ln=True)
            pdf.cell(0, 8, f"Total Validated Events: {len(events)}", ln=True)
            pdf.ln(10)

            # 🧾 Category Sections
            for cat, cat_events in grouped.items():
                pdf.set_font("Arial", "B", 13)
                pdf.set_fill_color(230, 230, 250)
                pdf.cell(0, 10, f"Category: {cat}", ln=True, fill=True)
                pdf.set_font("Arial", "B", 11)
                pdf.set_fill_color(220, 220, 220)
                pdf.cell(120, 8, "Event Title", border=1, fill=True)
                pdf.cell(40, 8, "Date", border=1, ln=True, fill=True)
                pdf.set_font("Arial", "", 11)

                if not cat_events:
                    pdf.cell(0, 8, "No events in this category.", ln=True)
                else:
                    for e in cat_events:
                        name = (e.name[:60] + "...") if len(e.name) > 60 else e.name
                        date = e.date.strftime("%d-%m-%Y") if e.date else "N/A"
                        pdf.cell(120, 8, name, border=1)
                        pdf.cell(40, 8, date, border=1, ln=True)
                pdf.ln(8)

            # 🧠 Summary
            pdf.ln(8)
            pdf.set_font("Arial", "B", 13)
            pdf.cell(0, 10, "IQC Review Summary", ln=True)
            pdf.set_draw_color(0, 102, 204)
            pdf.set_line_width(0.5)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(8)
            pdf.set_font("Arial", "", 11)
            pdf.cell(0, 8, f"Total Events: {len(events)}", ln=True)
            pdf.cell(0, 8, "Pending Validation: __________", ln=True)
            pdf.cell(0, 8, "IQC Reviewer: ____________________", ln=True)
            pdf.cell(0, 8, "Signature: ____________________", ln=True)
            pdf.cell(0, 8, "Date: ____________________", ln=True)
            pdf.ln(5)

            # Footer
            pdf.set_y(-20)
            pdf.set_font("Arial", "I", 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 10, "Generated by IQC Portal - DSU", 0, 0, "C")

            # ✅ Output safely
            try:
                pdf_bytes = pdf.output(dest="S").encode("latin-1", "replace")
            except Exception as enc_err:
                print("[Encoding Fallback Triggered]", enc_err)
                pdf_bytes = pdf.output(dest="S").encode("utf-8", "replace")

            pdf_stream = BytesIO(pdf_bytes)

            return send_file(pdf_stream,
                            mimetype="application/pdf",
                            as_attachment=True,
                            download_name=f"{dept}_IQC_Report.pdf")

        except Exception as err:
            print("[Report Generation Error]", err)
            return jsonify({"message": "Failed to generate report", "error": str(err)}), 500


    # ------------------ USER MANAGEMENT (IQC ADMIN) ------------------ #


    def _generate_temp_password(length=10):
        return secrets.token_urlsafe(length)[:length]

    @app.route('/api/auth/add_user', methods=['POST'])
    @token_required
    @role_required(['iqc'])
    def add_user(current_user):
        try:
            data = request.get_json() or {}
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()
            role = data.get('role', '').strip()
            department = data.get('department', '').strip()

            if not username or not password or not role:
                return jsonify({"message": "Missing required fields"}), 400

            # ✅ Check for any existing (possibly undeleted) record
            existing = User.query.filter_by(username=username).first()
            if existing:
                print(f"⚠️ Removing existing user '{username}' before re-creation...")
                db.session.delete(existing)
                db.session.commit()

            # ✅ Create fresh user
            user = User(username=username, role=role, department=department)
            user.set_password(password)  # sets both password_hash + plain_password
            db.session.add(user)
            db.session.commit()

            print(f"✅ Created user '{username}' ({role} - {department}) successfully.")
            return jsonify({
                "message": f"User '{username}' created successfully",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "department": user.department,
                    "plain_password": user.plain_password
                }
            }), 201

        except Exception as e:
            print("[Add User Error]", e)
            db.session.rollback()
            return jsonify({"message": "Failed to create user", "error": str(e)}), 500



    @app.route('/api/auth/users', methods=['GET'])
    @token_required
    @role_required(['iqc'])
    def api_list_users(current_user):
        users = User.query.all()
        return jsonify({
            "users": [
                {
                    "id": u.id,
                    "username": u.username,
                    "role": u.role,
                    "department": u.department,
                    "plain_password": u.plain_password or "N/A"
                } for u in users
            ]
        }), 200



    @app.route('/api/auth/users/<int:user_id>', methods=['DELETE'])
    @token_required
    @role_required(['iqc'])
    def api_delete_user(current_user, user_id):
        user = User.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found"}), 404
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "User deleted successfully"}), 200


    @app.route('/api/auth/users/<int:user_id>/set_password', methods=['POST'])
    @token_required
    @role_required(['iqc'])
    def api_set_password(current_user, user_id):
        data = request.get_json() or {}
        new_password = data.get('password')

        if not new_password:
            return jsonify({"message": "Password is required"}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found"}), 404

        user.set_password(new_password)
        db.session.commit()

        return jsonify({"message": f"Password updated for {user.username}"}), 200


    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
