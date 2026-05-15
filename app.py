from flask import Flask, send_file, request, jsonify
from triplestore import (
    filter_file_types,
    FileArguments,
    create_database,
    TripleStore,
)
from pathlib import Path
from dotenv import load_dotenv
import os

from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

import atexit
from typing import Optional

load_dotenv()

BASEDIR = os.getenv("BASEDIR")

# BASEDIR = "/data/digital_collections_ocfl/ark_data/"
# DB = Path("/data/local/app_data/project.db")
DB = os.getenv("CONTINUUMDB")
# print(DB)
#

STARTUP_COMPLETED = False
store: TripleStore

# store = TripleStore(Path(DB))
#
#


def create_app(test_config=None):
    """ """
    # Initialize the triple store
    # global store
    # store = TripleStore(Path(DB))

    app = Flask(__name__)
    auth = HTTPBasicAuth()

    @auth.verify_password
    def verify_password(username, password):
        """
        Only use this for routes protected and used on the local network
        """
        username, usernode, pswrd = store.fetch_user(username)
        if check_password_hash(pswrd.value, password):
            return usernode

    @app.route("/")
    def say_hello():
        return "Hello World"

    @app.before_request
    def tet():
        global store
        global STARTUP_COMPLETED
        if not STARTUP_COMPLETED:
            app.logger.debug("initializing database")
            # store, _ = create_database(Path(DB))
            store = TripleStore(Path(DB), logger=app.logger)
            STARTUP_COMPLETED = True

    @app.route("/file/<ark_id>/<file_name>")
    @app.route("/file/<ark_id>/<file_name>/<version>")
    def get_file(ark_id: str, file_name: str, version="head"):
        """
        Used by the ark Resolver to return the file, if the file is not passed, URLs for the
        different files are returned.
        """
        app.logger.debug(
            f"ark_id: {ark_id}, file_name: {file_name}, version: {version}"
        )

        if file_name:
            fname, ext = os.path.splitext(file_name)
            if "vaf" in fname:
                # print(fname)
                type_node = filter_file_types("viewer")
                # print(type_node)
            else:
                type_node = filter_file_types(
                    "preservation"
                    if ext in (".pdf", ".tif", ".wav")
                    else "supplemental"
                )
            obj = FileArguments(
                ark_id=ark_id,
                type_node=type_node,
                version=version,
                file_name=file_name,
                page=None,
            )
            # print("file arguments", obj)
            image_obj = store.find_file_path(obj)
            # print("image obj", image_obj)
            if len(image_obj) == 1:
                image_path = Path(image_obj[0]["path"])

                # print("ipath", ipath)
                if BASEDIR:
                    relative_path = Path(image_path).relative_to(
                        "/data/digital_collections_ocfl/ark_data/"
                    )

                    image_path = Path(BASEDIR) / relative_path
                # image_path = Path(
                #    ipath.replace("/data/digital_collections_ocfl/ark_data/", BASEDIR)
                # )
                # print("image path: ", image_path)
                if not image_path.is_file():
                    return f"error: Image not found on the server {image_path}", 400
                return send_file(image_path, as_attachment=False)
            return "file not found", 400

    @app.route("/protected/<method>", methods=["POST"])
    @auth.login_required
    def update_triples(method: str):
        global store
        if request.method != "POST":
            return "not found"
        if method == "backup":
            # run back up
            return "backup successful"
        file = request.files["file"]
        content = file.read().decode("utf-8")

        match method:
            case "file":
                # print("content", content)
                store.update_cho(content)
            case "rq":
                return store.query(content)
            case "ru":
                return store.update_qeury(content)
            case _:
                return jsonify({"message": "error in update method"})
        return "all good"

    return app


# defining function to run on shutdown
def close_running_threads():
    print("Threads complete, ready to finish")
    global store
    # store.flush()
    # del store.store
    # del store


# Register the function to be called on exit
atexit.register(close_running_threads)
# start your process

app = create_app()
