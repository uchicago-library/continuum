from src.continuum.app import create_app
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

BASEDIR = os.getenv("BASEDIR")
DB = os.getenv("CONTINUUMDB")
TURTLE_FILE = os.getenv("CONTINUUM_TURTLE")
INDEX_DB = Path(DB).parent / "index.db"  # os.getenv("INDEX_DB")

app = create_app(
    db_path=DB, basedir=BASEDIR, turtle_file=TURTLE_FILE, index_db=INDEX_DB
)
