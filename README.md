# 🧠 Multi-Agent AI Event Tracker (Final Build)

An AI-powered document intelligence system built using **Flask + React**, integrating multiple specialized agents for automatic **OCR**, **NER**, **categorization**, and **validation** of uploaded academic event reports and project documents.

This system supports intelligent extraction of text from both **scanned PDFs and digital reports**, automatically identifies the **event type, department, and abstract**, and stores results in a structured database.

---

## ⚙️ Tech Stack

**Backend:** Flask, SQLAlchemy, PaddleOCR, spaCy, JWT Authentication  
**Frontend:** React, TailwindCSS, Chart.js  
**Database:** SQLite (default, extensible to PostgreSQL/MySQL)  
**AI Agents:** OCR | NER | Categorizer | Validator  
**Roles:** Student | Teacher | IQC Admin  

---

## 🚀 Setup Guide

### 🧩 Prerequisites

Before you begin, make sure you have:

- 🐍 **Python 3.10+** (3.11 recommended)
- ⚙️ **Node.js 18+**
- 📦 **npm** or **yarn**
- 🧭 **Git**

---

## 🖥️ Backend Setup (Flask)

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # for PowerShell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install the spaCy English model:
   ```bash
   pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1.tar.gz
   ```

5. Initialize or upgrade your database:
   ```bash
   flask db upgrade
   ```

6. (Optional) Initialize default users:
   ```bash
   POST http://localhost:5000/api/init
   ```

7. Start the backend server:
   ```bash
   python main.py
   ```
   The backend will run at:  
   👉 `http://localhost:5000`

---

## 🌐 Frontend Setup (React)

1. Open a new terminal and go to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the frontend:
   ```bash
   npm start
   ```
   Access the app at:  
   👉 `http://localhost:3000`

---

## 🔑 Default Login Credentials

| Role | Username | Password | Department |
|------|-----------|-----------|-------------|
| Student | student1 | student1 | AIML |
| Teacher | teacher1 | teacher1 | CSE(Core) |
| IQC Admin | iqc | adminpass | ALL |

---

## 🤖 AI Multi-Agent Pipeline

| Step | Agent | Function |
|------|--------|-----------|
| 1️⃣ | **OCR Agent** | Extracts text from PDFs or images using PaddleOCR (hybrid for digital + scanned) |
| 2️⃣ | **NER Agent** | Extracts event details (name, date, venue, organizer, department) |
| 3️⃣ | **Categorizer Agent** | Classifies document into Workshop / Conference / Report / etc. |
| 4️⃣ | **Validator Agent** | Checks field completeness & format (e.g., missing abstract/date) |
| 5️⃣ | **Database** | Persists document, event, and extracted entities |

---

## 🧩 Key Features

- 📄 Upload event or project reports (PDF / Image)
- 🧠 Hybrid OCR using **PaddleOCR** (auto-detects text layer)
- 💡 Intelligent NER (named entity recognition via spaCy)
- 🗂️ Event categorization (e.g., Workshop, Competition, Research Report)
- 🧾 Abstract extraction and validation
- 👨‍🏫 Multi-role dashboard (Student, Teacher, IQC Admin)
- 📊 Department-wise progress tracking
- 🔒 JWT-based authentication
- 📦 CSV report generation

---

## 🧰 Common Commands

### Rebuild Environment
```bash
rmdir /s /q venv
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### Database Reset
```bash
flask db init
flask db migrate
flask db upgrade
```

### Clean Cache / Build
```bash
git clean -fdx
```

---

## 🧠 Troubleshooting

| Problem | Solution |
|----------|-----------|
| **OCR too slow** | Reduce DPI in `ocr_agent.py` (`pix = page.get_pixmap(dpi=100)`) |
| **OCR init failed** | Run `pip install paddleocr paddlepaddle` manually |
| **spaCy model missing** | Reinstall with the model tar.gz link above |
| **CORS / Proxy issue** | Ensure frontend `package.json` has `"proxy": "http://localhost:5000"` |
| **Login fails** | Run `/api/init` endpoint to recreate default users |

---

## 🌿 Git Workflow (Team Collaboration)

1. Pull latest code:
   ```bash
   git pull origin main
   ```
2. Create your branch:
   ```bash
   git checkout -b aman-feature
   ```
3. After edits:
   ```bash
   git add .
   git commit -m "Updated OCR and orchestrator pipeline"
   git push origin aman-feature
   ```
4. Open a Pull Request on GitHub for review & merge.

---

## 🧾 License

Developed by **Aman Sheikh**  
as part of a *Pattern Recognition and Machine Learning* case study.  
Free to use for academic and educational purposes.
