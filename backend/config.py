import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY','dev-secret')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f"sqlite:///{BASE_DIR/'app.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', str(BASE_DIR/'static'/'uploads'))
    JWT_SECRET = os.environ.get('JWT_SECRET', 'jwt-secret-key')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    USE_ABSTRACT_AGENT = os.environ.get('USE_ABSTRACT_AGENT', 'false').lower() == 'true'  # Set to 'true' to enable Gemini abstract generation
    DEV_MODE = True  # Toggle off in production
