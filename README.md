# Multi-Agent Event Tracker System

A comprehensive event tracking platform powered by multiple intelligent agents for document processing, entity extraction, and event validation. The system combines OCR, NLP, and intelligent categorization to automate event management across university departments.

## 📋 Project Overview

The Multi-Agent Event Tracker is designed for Dayananda Sagar University (DSU) to:
- Process event-related documents using OCR and AI agents
- Extract event details (names, dates, venues, organizers)
- Automatically categorize events by type and department
- Validate and track events across multiple departments
- Generate comprehensive IQC (Internal Quality Control) reports

### Key Features

- **Multi-Agent Architecture**: Orchestrated OCR, NER, Categorizer, and Validator agents
- **Role-Based Access Control**: Student, Teacher, and IQC admin roles
- **Document Processing**: Support for PDF, PNG, JPG, JPEG, TIFF formats
- **Automated Entity Extraction**: Intelligent extraction of event metadata
- **Event Validation Workflow**: Two-tier approval system (Teacher → IQC)
- **Department-Wide Tracking**: Real-time progress monitoring
- **PDF Report Generation**: Professional IQC reports with department summaries

---

## 🏗️ Architecture

### System Components

\`\`\`
┌─────────────────────────────────────────────────────┐
│           Frontend (React Application)              │
│  - Student/Teacher/Admin Dashboards                 │
│  - Document Upload Interface                        │
│  - Event Validation UI                              │
│  - Real-time Progress Tracking                      │
└─────────────────┬───────────────────────────────────┘
                  │ REST API
┌─────────────────▼───────────────────────────────────┐
│         Flask Backend API Server                    │
│  - User Authentication & Authorization              │
│  - Document Management                              │
│  - Event CRUD Operations                            │
│  - Report Generation                                │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│        Multi-Agent Orchestration Layer              │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐               │
│  │ OCR Agent    │  │ NER Agent    │               │
│  │ - PaddleOCR  │  │ - spaCy/NLP  │               │
│  │ - Text Ext.  │  │ - Entity Ext.│               │
│  └──────────────┘  └──────────────┘               │
│                                                     │
│  ┌──────────────────┐  ┌────────────────┐        │
│  │ Categorizer Agent│  │Validator Agent │        │
│  │ - Classification │  │ - Validation   │        │
│  │ - Dept. Mapping  │  │ - Rule Checking│        │
│  └──────────────────┘  └────────────────┘        │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│     Database Layer (SQLite + SQLAlchemy ORM)        │
│  - Users & Authentication                           │
│  - Documents & Entities                             │
│  - Events & Validation Status                       │
└─────────────────────────────────────────────────────┘
\`\`\`

### Agent Responsibilities

- **OCR Agent** (`ocr_agent.py`): Extracts text from document images using PaddleOCR and summarizes content
- **NER Agent** (`ner_agent.py`): Performs Named Entity Recognition to extract event details (date, venue, organizer)
- **Categorizer Agent** (`categorizer_agent.py`): Classifies events into predefined categories and departments
- **Validator Agent** (`validator_agent.py`): Validates extracted data against business rules
- **Orchestrator Agent** (`orchestrator_agent.py`): Coordinates the entire processing pipeline

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.8+**
- **Node.js 14+** (for frontend)
- **pip** (Python package manager)
- **npm** or **yarn** (Node package manager)

### Backend Installation

#### 1. Clone and Navigate to Backend

\`\`\`bash
cd backend
\`\`\`

#### 2. Create Virtual Environment

\`\`\`bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
\`\`\`

#### 3. Install Dependencies

\`\`\`bash
pip install -r requirements.txt
\`\`\`

#### 4. Download spaCy Model (Required for NER)

\`\`\`bash
python -m spacy download en_core_web_sm
\`\`\`

#### 5. Initialize Database

\`\`\`bash
# Create database and tables
python -c "from main import app; app.app_context().push(); from models import db; db.create_all(); print('✅ Database initialized')"

# Seed initial users (optional)
# Default users: student1, teacher1, iqc (see config for passwords)
curl -X POST http://localhost:5000/api/init
\`\`\`

#### 6. Run Backend Server

\`\`\`bash
# Development
python main.py

# Production
gunicorn --bind 0.0.0.0:5000 --workers 4 main:app
\`\`\`

The backend API will be available at `http://localhost:5000`

### Frontend Installation

#### 1. Navigate to Frontend Directory

\`\`\`bash
cd frontend
\`\`\`

#### 2. Install Dependencies

\`\`\`bash
npm install
\`\`\`

#### 3. Start Development Server

\`\`\`bash
npm start
\`\`\`

The frontend will open at `http://localhost:3000`

---

## 📚 API Documentation

### Authentication

All API endpoints (except `/api/init` and `/api/ping`) require JWT authentication.

**Login Endpoint:**
\`\`\`http
POST /api/auth/login
Content-Type: application/json

{
  "username": "student1",
  "password": "student1"
}
\`\`\`

**Response:**
\`\`\`json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "username": "student1",
    "role": "student",
    "department": "AIML"
  }
}
\`\`\`

### Key Endpoints

#### Documents

- `POST /api/upload` - Upload document (multipart/form-data)
- `GET /api/documents` - List documents (role-filtered)
- `GET /api/document/<id>` - Get document details with entities and events
- `GET /api/document/<id>/file` - Download original document

#### Events

- `GET /api/validate/events` - List pending validation events
- `POST /api/validate/<event_id>` - Validate and save event
- `GET /api/tracker` - Get department progress (IQC only)
- `GET /api/tracker/<dept>` - Get events by department and category
- `GET /api/tracker/<dept>/report` - Generate PDF report for department

#### User Management (IQC Admin)

- `POST /api/auth/add_user` - Create new user
- `GET /api/auth/users` - List all users
- `DELETE /api/auth/users/<id>` - Delete user
- `POST /api/auth/users/<id>/set_password` - Update user password

---

## 🗄️ Database Schema

### Users Table
\`\`\`sql
users
├── id (PK)
├── username (unique)
├── password_hash
├── plain_password (dev only)
├── role (student|teacher|iqc)
└── department
\`\`\`

### Documents Table
\`\`\`sql
documents
├── id (PK)
├── filename
├── uploaded_by
├── uploaded_at
├── status (uploaded|processing|needs_review|saved|failed)
├── raw_text
├── last_error
├── category
└── department
\`\`\`

### Events Table
\`\`\`sql
events
├── id (PK)
├── document_id (FK)
├── name
├── date
├── department
├── category
└── validated (boolean)
\`\`\`

### Extracted Entities Table
\`\`\`sql
extracted_entities
├── id (PK)
├── document_id (FK)
├── label (entity_type)
├── text
└── confidence
\`\`\`

---

## 🎯 User Roles & Workflows

### Student Role
- Upload event documents
- View their own uploaded documents
- View validated events from their department

### Teacher Role
- Validate events from their department
- Review document details before validation
- Access department-specific reports

### IQC Admin Role
- View and manage all documents and events
- Validate events from any department
- Create and manage user accounts
- Generate comprehensive IQC reports
- Track department progress via dashboard

---

## 🔧 Configuration

Edit `backend/config.py` to customize:

\`\`\`python
# Database URL (default: SQLite)
SQLALCHEMY_DATABASE_URI = "sqlite:///app.db"

# Upload folder for documents
UPLOAD_FOLDER = "static/uploads"

# JWT secret for token signing
JWT_SECRET = "your-secret-key"

# Enable development mode
DEV_MODE = True
\`\`\`

### Environment Variables

\`\`\`bash
# Optional - Override defaults
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///app.db
JWT_SECRET=your-jwt-secret
UPLOAD_FOLDER=static/uploads
\`\`\`

---

## 📊 Supported Event Categories

The system recognizes the following event categories:

1. **Seminar**
2. **Workshop / Hands-on / Training**
3. **Guest Lecture / Expert Talk**
4. **Conference / Symposium**
5. **Competition / Hackathon / Quiz**
6. **Orientation / Induction / Welcome**
7. **Research / Report / Paper Presentation**
8. **General / Department Activity**

---

## 📁 File Formats Supported

- **PDF** - Portable Document Format
- **PNG** - Raster image format
- **JPG/JPEG** - JPEG raster format
- **TIFF** - Tagged Image File Format

---

## 🧪 Testing

### Initialize Test Data

\`\`\`bash
curl -X POST http://localhost:5000/api/init
\`\`\`

### Test Login

\`\`\`bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"student1","password":"student1"}'
\`\`\`

### Test Document Upload

\`\`\`bash
TOKEN="your_jwt_token_here"
curl -X POST http://localhost:5000/api/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@event_document.pdf"
\`\`\`

---

## 🐛 Troubleshooting

### Issue: PaddleOCR Download Takes Long Time
**Solution**: PaddleOCR models are downloaded on first use. Set cache directory:
\`\`\`bash
export PADDLE_CACHE_HOME=/path/to/cache
\`\`\`

### Issue: spaCy Model Not Found
**Solution**: Ensure you've downloaded the model:
\`\`\`bash
python -m spacy download en_core_web_sm
\`\`\`

### Issue: Database Locked Error
**Solution**: SQLite has concurrency issues. For production, migrate to PostgreSQL:
\`\`\`bash
SQLALCHEMY_DATABASE_URI = "postgresql://user:pass@localhost/dbname"
\`\`\`

### Issue: CORS Errors
**Solution**: Backend CORS is configured for all origins. Update for production:
\`\`\`python
CORS(app, resources={r"/api/*": {"origins": ["https://yourdomain.com"]}})
\`\`\`

---

## 🚢 Deployment

### Backend Deployment (Gunicorn + Nginx)

1. **Install Gunicorn** (included in requirements.txt)

2. **Create Systemd Service** (`/etc/systemd/system/iqc-tracker.service`):
\`\`\`ini
[Unit]
Description=IQC Event Tracker Backend
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/path/to/backend
ExecStart=/path/to/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 main:app
Restart=always

[Install]
WantedBy=multi-user.target
\`\`\`

3. **Start Service**:
\`\`\`bash
sudo systemctl start iqc-tracker
sudo systemctl enable iqc-tracker
\`\`\`

### Frontend Deployment

1. **Build for Production**:
\`\`\`bash
npm run build
\`\`\`

2. **Deploy Build Folder** to your hosting service (Vercel, Netlify, AWS S3, etc.)

---

## 📝 License

This project is proprietary software for Dayananda Sagar University.

---

## 📞 Support

For issues or questions, contact the development team or create an issue in the repository.

---

## 📌 Version History

- **v1.0.0** (Current)
  - Multi-agent event processing pipeline
  - Role-based access control
  - PDF report generation
  - Real-time event tracking
  - Full REST API

---

## 🎓 Technology Stack

### Backend
- **Framework**: Flask 2.3.3
- **Database**: SQLite (SQLAlchemy ORM)
- **OCR**: PaddleOCR 2.7.0.2
- **NLP**: spaCy 3.7.2, Transformers 4.43.3
- **Auth**: PyJWT 2.8.0
- **PDF**: PyMuPDF, reportlab, fpdf
- **Server**: Gunicorn 20.1.0

### Frontend
- **Framework**: React 18.2.0
- **Routing**: React Router v6
- **Charts**: Chart.js + react-chartjs-2
- **HTTP Client**: Axios
- **Styling**: Tailwind CSS
- **Icons**: Lucide React

### Infrastructure
- **Database**: SQLite (dev) → PostgreSQL (production)
- **Web Server**: Nginx + Gunicorn
- **Message Queue**: Optional (Celery for async processing)
