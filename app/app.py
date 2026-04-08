from flask import Flask, send_file
from .triplestore import (
    filter_file_types,
    FileArguments,
    find_file_path,
    create_database,
)
from pathlib import Path
import os

from typing import Optional


BASEDIR = "/home/sgoodwin/bin/GitProjects/continuum/testdata/"


def create_app(test_config=None):
    """ """
    create_database()
    app = Flask(__name__)

    @app.route("/")
    def say_hello():
        return "Hello World"

    """
    @app.before_request
    def tet():
        global STARTUP_COMPLETED
        if not STARTUP_COMPLETED:
            print("initializing database")
            create_database()
            STARTUP_COMPLETED = True

    """

    @app.route("/file/<ark_id>/<file_name>")
    @app.route("/file/<ark_id>/<file_name>/<version>")
    def get_file(ark_id: str, file_name: str, version="head"):
        """
        Used by the ark Resolver to return the file, if the file is not passed, URLs for the
        different files are returned.
        """
        print(f"ark_id: {ark_id}, file_name: {file_name}, version: {version}")

        if file_name:
            fname, ext = os.path.splitext(file_name)
            if "vaf" in fname:
                print(fname)
                type_node = filter_file_types("viewer")
                print(type_node)
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
            print("file arguments", obj)
            image_obj = find_file_path(obj)
            print("image obj", image_obj)
            if len(image_obj) == 1:
                ipath = image_obj[0]["path"]

                image_path = Path(
                    ipath.replace("/data/digital_collections_ocfl/ark_data/", BASEDIR)
                )
                print("image path: ", image_path)
                if not image_path.is_file():
                    return {"error": "Image not found on the server"}
                return send_file(image_path, as_attachment=True)
