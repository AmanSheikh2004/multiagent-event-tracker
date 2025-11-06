import os, datetime, jwt
from flask import Flask, request, jsonify, send_file
from flask_migrate import Migrate
from config import Config
from models import db, User, Document, ExtractedEntity, Event
from werkzeug.utils import secure_filename
from agents.orchestrator_agent import OrchestratorAgent
from functools import wraps
from flask_cors import CORS
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
            # ✅ Accept token from headers or URL
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

            return f(*args, **kwargs)
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
    def upload():
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
    def list_docs():
        user = request.user
        if user.role=='iqc':
            docs = Document.query.order_by(Document.uploaded_at.desc()).all()
        else:
            docs = Document.query.filter_by(uploaded_by=user.username).order_by(Document.uploaded_at.desc()).all()
        out = [{'id':d.id,'filename':d.filename,'status':d.status,'uploaded_at':d.uploaded_at.isoformat()} for d in docs]
        return jsonify(out)

    @app.route('/api/document/<int:doc_id>', methods=['GET'])
    @token_required
    def doc_detail(doc_id):
        d = Document.query.get_or_404(doc_id)
        ents = [{'label':e.label,'text':e.text,'confidence':e.confidence} for e in d.entities]
        evs = [{'id':ev.id,'name':ev.name,'date':ev.date.isoformat() if ev.date else None,'department':ev.department,'category':ev.category,'validated':ev.validated} for ev in d.events]
        return jsonify({'document':{'id':d.id,'filename':d.filename,'status':d.status,'raw_text':d.raw_text}, 'entities':ents, 'events':evs})

    @app.route('/api/validate/<int:event_id>', methods=['POST'])
    @token_required
    @role_required(['teacher','iqc'])
    def validate_event(event_id):
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

    @app.route('/api/tracker', methods=['GET'])
    @token_required
    def tracker():
        depts = ['AIML','CSE(Core)']
        out = {}
        for dept in depts:
            events = Event.query.filter_by(department=dept).all()
            total = len(events)
            cat_counts = {}
            for ev in events:
                cat_counts[ev.category] = cat_counts.get(ev.category,0)+1
            out[dept] = {'total': total, 'by_category': cat_counts, 'events':[{'name':e.name,'date': e.date.isoformat() if e.date else None,'category':e.category} for e in events]}
        return jsonify(out)

    @app.route('/api/report/<dept>', methods=['GET'])
    @token_required
    def report(dept):
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
    def list_pending_events():
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
    def document_file(doc_id):
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

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
