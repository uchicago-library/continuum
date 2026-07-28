from flask import Flask, send_file
from triplestore import (
    filter_file_types,
    FileArguments,
    create_database,
    TripleStore,
)
from pathlib import Path
from dotenv import load_dotenv
import os


from typing import Optional

load_dotenv()

BASEDIR = os.getenv("BASEDIR")

# BASEDIR = "/data/digital_collections_ocfl/ark_data/"
# DB = Path("/data/local/app_data/project.db")
DB = os.getenv("CONTINUUMDB")
# print(DB)

store: TripleStore


def create_app(test_config=None):
    """ """
    # Initialize the triple store
    global store
    store = TripleStore(Path(DB))

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
        argv1 : file_name | page
        argv2 : file_name
        <ark_id>/<page>/<file_name>/<version>
        """
        # print(f"ark_id: {ark_id}, file_name: {file_name}, version: {version}")
        if file_name and file_name.startswith("000"):
            page = file_name
            file_name = None
        if file_name and file_name.startswith("v"):
            version = file_name
            file_name = page
            page = None

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
        else:
            type_node = filter_file_types("preservation")
        obj = FileArguments(
            ark_id=ark_id,
            type_node=type_node,
            version=version,
            file_name=file_name,
            page=page,
        )
        print("file arguments", obj)
        image_obj = store.find_file_path(obj)
        print("image obj", image_obj)
        if len(image_obj) == 1:
            image_path = Path(image_obj[0]["path"])

            # print("ipath", ipath)
        elif len(image_obj) > 1:
            filtered_image = list(
                filter(lambda x: x["path"].endswith(".pdf"), image_obj)
            )
            print(f"filtered image: {filtered_image}")
            if len(filtered_image) != 1:
                print(f"error: image not found on the server {image_obj}")
                return (
                    "The requested resource is unavailable. Please consult node@lib.uchicago.edu for further information",
                    403,
                )
            image_path = filtered_image[0]["path"]
            # image_path = Path(BASEDIR) / filtered_image[0]["path"]
            # print(f"image path: {image_path}")
            # return send_file(image_path, as_attachment=False)
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
            # print("image path: ", image_path)
            #
        if not image_path.is_file():
            return f"error: Image not found on the server {image_path}", 400

        return send_file(image_path, as_attachment=False)
        # return (
        #    "The requested resource is currently restricted. Please consult node@lib.uchicago.edu for further information",
        #    403,
        # )

    return app


app = create_app()
