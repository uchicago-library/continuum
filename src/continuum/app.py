from flask import Flask, send_file
from .triplestore import (
    filter_file_types,
    FileArguments,
    # create_database,
    TripleStore,
)
from pathlib import Path

import os

from typing import Optional, Callable

store: TripleStore


def construct_file_arguments(
    logger: Callable,
    ark_id: str,
    file_name: Optional[str] = None,
    page: Optional[str] = None,
    version: Optional[str] = None,
):
    if file_name and file_name.startswith("000"):
        page = file_name
        file_name = None
    if file_name and file_name.startswith("v"):
        version = file_name
        file_name = page
        page = None

    # mime_type = "application/pdf" if file_name == "pdf" else None
    mime_type = None
    # if mime_type:
    #    file_name = None

    if file_name:
        fname, ext = os.path.splitext(file_name)
        if "vaf" in fname:
            type_node = filter_file_types("viewer")
            # print(type_node)
        elif "manifest" in fname:
            file_name = None
            type_node = filter_file_types("manifest")
        elif file_name == "pdf":
            file_name = None
            mime_type = "application/pdf"
            type_node = filter_file_types("preservation")
        elif file_name == "pres":
            type_node = filter_file_types("preservation")
            file_name = None
        elif file_name == "ocr":
            type_node = filter_file_types("supplemental")
            file_name = "file.txt"
        elif file_name == "mets":
            type_node = filter_file_types("supplemental")
            file_name = "file.mets.xml"
        elif file_name == "alto":
            type_node = filter_file_types("supplemental")
            file_name = "file.xml"
        else:
            type_node = filter_file_types(
                "preservation" if ext in (".pdf", ".tif", ".wav") else "supplemental"
            )
    else:
        type_node = filter_file_types("preservation")
    obj = FileArguments(
        ark_id=ark_id,
        type_node=type_node,
        version=version,
        file_name=file_name,
        page=page,
        mime_type=mime_type,
    )
    logger.debug("file arguments", str(obj))
    return obj


def create_app(
    test_config=None,
    turtle_file: str = "",
    db_path: str = "",
    basedir: Optional[str] = None,
):
    """ """
    # Initialize the triple store
    global store

    app = Flask(__name__)

    store = TripleStore(Path(db_path), app.logger, turtle_file)

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

    """
    Commenting out the file sizes
    @app.route("/size/<ark_id>/<file_name>")
    @app.route("/size/<ark_id>/<page>/<file_name>")
    @app.route("/size/<ark_id>/<page>/<file_name>/<version>")
    def get_size(
        ark_id: str,
        file_name: Optional[str] = None,
        page: Optional[str] = None,
        version="head",
    ):
        """ """
        file_obj = construct_file_arguments(
            ark_id, file_name=file_name, page=page, version=version
        )
        return "hello world"
    """

    @app.route("/file/<ark_id>")
    @app.route("/file/<ark_id>/<file_name>")
    @app.route("/file/<ark_id>/<page>/<file_name>")
    @app.route("/file/<ark_id>/<page>/<file_name>/<version>")
    def get_file(
        ark_id: str,
        file_name: Optional[str] = None,
        page: Optional[str] = None,
        version="head",
    ):
        """
        Used by the ark Resolver to return the file, if the file is not passed, URLs for the
        different files are returned.
        argv0 : ark_id
        argv1 : file_name | page | "pdf" | "pres"
        argv2 : file_name | version
        argv3 : version
        <ark_id>/<page>/<file_name>/<version>
        """
        # print(f"ark_id: {ark_id}, file_name: {file_name}, version: {version}")
        obj = construct_file_arguments(
            app.logger, ark_id, file_name=file_name, page=page, version=version
        )
        # print("file arguments", obj)
        image_obj, code = store.find_file_path(obj)
        # print("image obj", image_obj)
        match code:
            case 1:
                image_path = Path(image_obj[0]["path"])
                if basedir:
                    image_path = Path(basedir) / image_path

                if not image_path.is_file():
                    return f"error: Image not found on the server {image_path}", 400
                return send_file(image_path, as_attachment=False)
            case 0:
                return (
                    "The requested resource is unavailable. Please consult node-admins@lib.uchicago.edu for further information.",
                    403,
                )
            case 404:
                return (
                    "The requested resource was not found",
                    404,
                )
            case _:
                return (
                    "Error with the requested file",
                    code,
                )

    return app
