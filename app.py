from src.continuum.app import create_app
from dotenv import load_dotenv
import os

load_dotenv()

BASEDIR = os.getenv("BASEDIR")
DB = os.getenv("CONTINUUMDB")
TURTLE_FILE = os.getenv("CONTINUUM_TURTLE")

app = create_app(db_path=DB, basedir=BASEDIR, turtle_file=TURTLE_FILE)
