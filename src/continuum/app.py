from flask import Flask, send_file, render_template, request
from .triplestore import (
    filter_file_types,
    FileArguments,
    # create_database,
    TripleStore,
)
from .search import search_index, create_index
from pathlib import Path

# import json
from dotenv import load_dotenv
import os


from typing import Optional, Callable

load_dotenv()

BASEDIR = os.getenv("BASEDIR")

# BASEDIR = "/data/digital_collections_ocfl/ark_data/"
# DB = Path("/data/local/app_data/project.db")
DB = os.getenv("CONTINUUMDB")
# print(DB)

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
    logger.debug(f"file arguments {str(obj)}")
    return obj


def create_app(test_config=None):
    """ """
    # Initialize the triple store
    global store

    app = Flask(__name__)

    store = TripleStore(Path(DB), app.logger)
    create_index(store, app.logger)

    """
    @app.route("/")
    def say_hello():
        return "Hello World"
    """

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
        # app.logger.debug(f"ark_id: {ark_id}, file_name: {file_name}, version: {version}")
        obj = construct_file_arguments(
            app.logger, ark_id, file_name=file_name, page=page, version=version
        )
        # app.logger.debug("file arguments", obj)
        image_obj = store.find_file_path(obj)
        # app.logger.debug("image obj", image_obj)
        if len(image_obj) == 1:
            image_path = Path(image_obj[0]["path"])

        else:
            return (
                "The requested resource is unavailable. Please consult node@lib.uchicago.edu for further information",
                403,
            )

        if BASEDIR:
            # relative_path = Path(image_path).relative_to(
            #    "/data/digital_collections_ocfl/ark_data/"
            # )

            # image_path = Path(BASEDIR) / relative_path
            image_path = Path(BASEDIR) / image_path
            # image_path = Path(
            #    ipath.replace("/data/digital_collections_ocfl/ark_data/", BASEDIR)
            # )
            #
        if not image_path.is_file():
            return f"error: Image not found on the server {image_path}", 400

        return send_file(image_path, as_attachment=False)
        # return (
        #    "The requested resource is currently restricted. Please consult node@lib.uchicago.edu for further information",
        #    403,
        # )

    @app.route("/")
    def read_route(
        term: Optional[str] = None,
        field: Optional[str] = None,
    ):
        if group := request.args.get("group"):
            match group:
                case "Collections":
                    data = store.get_collections()
                case "Arks":
                    data = store.get_arks()
                case "Local Identifiers":
                    data = store.get_local_ids()
                case _:
                    return "error"
            app.logger.debug("data", data)
            return render_template("index.html", data=data)

        if not (field := request.args.get("field")):
            return render_template("index.html")

        if term := request.args.get("term"):
            app.logger.debug(f"Term: {term}")
            data = store.search_for_term(field, term)
            app.logger.debug(f"Data: {data}")
            return render_template("index.html", data=data)  # , context={"data": data})

        return render_template("index.html")  # , context={"data": data})

    @app.route("/items/<id>")
    def read_item(id: str):
        # ark_node = ns.ark.term(id if id.startswith("ark:61001/") else f"ark:61001/{id}")

        app.logger.debug("items id", id)
        object_data = store.retrieve_object_data(id)
        data = {"id": id, "data": object_data}
        return render_template("item.html", data=data)

    @app.route("/search", methods=["POST"])
    def process_search_term():
        body = request.json
        # app.logger.debug("search body:", json.dumps(body))
        if (term := body.get("term")) and (field := body.get("field")):
            document = search_index(field, term)
            res = [
                {
                    "ark": r.text,
                    "id": r.ark,
                    "local-id": r.local_id,
                    "collection": r.collection,
                }
                for r in document
            ]
            return res

    return app
