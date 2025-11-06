# 🧠 Multi-Agent AI Event Tracker

A Flask + React-based AI system that uses **multi-agent intelligence** and **OCR (PaddleOCR)** to extract and categorize event data from uploaded documents.  
It supports multiple roles — **Student**, **Teacher**, and **IQC Admin** — each with different permissions and dashboards.

---

## ⚙️ Tech Stack

**Backend:** Flask, SQLAlchemy, PaddleOCR, JWT Authentication  
**Frontend:** React, TailwindCSS, Chart.js  
**Database:** SQLite (default)  
**Roles:** Student | Teacher | IQC Admin  

---

## 🚀 Project Setup

### 🧩 Prerequisites

Make sure you have these installed:

- **Python 3.10+** (3.11 recommended)
- **Node.js 18+**
- **npm** or **yarn**
- **Git**

---

## 🖥️ Backend Setup (Flask)

1.  Navigate to the backend folder:
    ```bash
    cd backend
    ```
2.  (Optional but recommended) Create and activate a virtual environment:
    ```bash
    python -m venv venv
    venv\Scripts\activate    # On Windows
    # or
    source venv/bin/activate    # On macOS/Linux
    ```
3.  Install all required Python packages:
    ```bash
    pip install -r requirements.txt
    pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1.tar.gz
    ```
4.  Initialize the database (only needed once):
    ```bash
    flask db upgrade
    ```
5.  (Optional) Initialize default users (run this route once after backend starts):
    ```bash
    POST http://localhost:5000/api/init
    ```
6.  Run the Flask server:
    ```bash
    python main.py
    ```
    The backend will start at:
    ```
    http://localhost:5000
    ```

---

## 🌐 Frontend Setup (React)

1.  Open a new terminal and navigate to the frontend folder:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Start the frontend:
    ```bash
    npm start
    ```
    The React app will start at:
    ```
    http://localhost:3000
    ```

---

## 🔐 Default Login Credentials

| Role | Username | Password | Department |
| :--- | :--- | :--- | :--- |
| Student | student1 | student1 | AIML |
| Teacher | teacher1 | teacher1 | CSE(Core) |
| IQC Admin | iqc | adminpass | ALL |

---

## 🧩 Features

-   📄 Upload event reports (PDFs, images)
-   🤖 OCR-based text extraction using PaddleOCR
-   🧠 Multi-agent pipeline for information extraction, validation, and categorization
-   🧑‍🎓 Role-based access (Students, Teachers, IQC Admin)
-   📊 Progress tracker by department
-   🧾 CSV Report generation per department
-   🔒 JWT-secured REST API

---

## 🧰 Useful Commands

### Rebuild virtual environment
```bash
rmdir /s /q venv
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
````

### Regenerate database

```bash
flask db init
flask db migrate
flask db upgrade
```

### Clean project cache

```bash
git clean -fdx
```

-----

## 🧠 Troubleshooting

  - **Login fails:** Run `/api/init` once after backend setup to create default users.
  - **OCR errors:** Ensure PaddleOCR and PaddlePaddle are correctly installed:
    ```bash
    pip install paddleocr paddlepaddle
    ```
  - **Frontend 5000 CORS issue:** Confirm your frontend `package.json` includes:
    ```json
    "proxy": "http://localhost:5000"
    ```

-----

## 🌿 Git Collaboration Guide (For Team Members)

### 🔄 Pull the latest code

Before you start working, always pull the latest version:

```bash
git pull origin main
```

This ensures your local project is up to date with the main branch.

### 🌱 Create your own branch

Each teammate should create and work on their own branch, not directly on `main`.

```bash
git checkout -b yourname-feature
```

Example:

```bash
git checkout -b aman-frontend-fix
```

After finishing changes:

```bash
git add .
git commit -m "Added feature XYZ"
git push origin yourname-feature
```

### 🧩 Merging back to main (by Aman / Maintainer)

When your feature is ready, go to GitHub and open a **Pull Request (PR)** from your branch to `main`.
The maintainer (Aman) will review and merge it.

### 🧼 If you get errors while pulling:

If you modified files that also changed in `main`, Git will show a merge conflict.
Fix the files manually, then run:

```bash
git add .
git commit -m "Resolved conflicts"
git push
```

### 🌳 Simple Git Branch Flow

```
      main
        \
         \__ aman-frontend-fix
               \__ -> (commit, push)
                     \
                      -> Pull Request -> main (merged)
```

-----

## 🧾 License

This project is developed as part of a Pattern Recognition and Machine Learning case study by Aman Sheikh.
Free to use for educational purposes.

-----
