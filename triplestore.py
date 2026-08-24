from pyoxigraph import NamedNode, Literal, Store, QuerySolutions, RdfFormat, Quad
from pathlib import Path
from typing import Dict, Optional, TypedDict, List, Callable
import shutil

import os
from dotenv import load_dotenv

load_dotenv()

TURTLE_FILE = os.getenv("CONTINUUM_TURTLE")

store: Store = Store()


class FileArguments(TypedDict):
    ark_id: str
    type_node: NamedNode
    version: str
    file_name: Optional[str]
    page: Optional[str]
    mime_type: Optional[str]


class Namespace(str):
    def __new__(cls, value: str):
        return str.__new__(cls, value)

    def term(self, local: str) -> NamedNode:
        return NamedNode(self + local)

    def __getattr__(self, local: str) -> NamedNode:
        if local.startswith("__"):
            raise AttributeError
        return self.term(local)


class NS:
    def __init__(self, prefixes: Dict[str, str]):
        self.dict = prefixes

    def get(self, namespace):
        return Namespace(self.dict[namespace])

    def __getattr__(self, namespace):
        return self.get(namespace)


PREFIXES = {
    "ark": "http://ark.lib.uchicago.edu/",
    "continuum": "https://continuum.lib.uchicago.edu/ontology/",
    "cont": "http://continuum.lib.uchicago.edu/",
    "premis": "http://www.loc.gov/premis/rdf/v3/",
    "ebucore": "http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
}


ns = NS(PREFIXES)


def load_store(database: Path, turtle_time: float, logger: Callable):
    """
    Create a new store, and add the timestamp to it
    """
    store = Store(str(database))
    logger.info("loading store from ttl")
    with open(TURTLE_FILE, "r") as ttlp:
        store.bulk_load(ttlp, format=RdfFormat.TURTLE)
    logger.info("store loaded")
    store.add(
        Quad(
            ns.cont.ContinuumServer,
            ns.continuum.timestamp,
            Literal(str(turtle_time), datatype=ns.xsd.double),
        )
    )
    store.optimize()
    store.flush()
    store = Store.read_only(str(database))
    return store


def create_database(database: Path, logger: Callable):
    """This creates the database connection.
    If No database exists, the database is created from a turtle file
    But if the dtabase does exist and is outdated, the database is deleted
    and a new database is created

    Update the database
    """

    # print(os.getcwd())
    turtle_time = os.path.getmtime(TURTLE_FILE)
    global store

    if database.exists():
        logger.info("Loading existing store")
        # store = Store(database)
        store = Store.read_only(str(database))
        logger.info("store loaded")
        startdt = sorted(
            [
                float(dt.value)
                for _, _, dt, _ in store.quads_for_pattern(
                    ns.cont.ContinuumServer, ns.continuum.timestamp, None
                )
            ],
            reverse=True,
        )

        if len(startdt) == 0 or startdt[0] < turtle_time:
            logger.info("Turtle Out of Date")
            shutil.rmtree(database)
            store = load_store(database, turtle_time)

    else:
        store = Store(database)
        logger.info("loading store from ttl")
        store = load_store(database, turtle_time)

    return store, turtle_time


def filter_file_types(file_type: str):
    """
    find the file type term
    """
    match file_type:
        case "manifest":
            return ns.continuum.Manifest
        case "preservation":
            return ns.continuum.Preservation
        case "viewer":
            return ns.continuum.Viewer
        case _:
            return ns.continuum.Supplemental


class TripleStore:
    def __init__(self, database: Path, logger: Callable):
        self.store, self.turtle_time = create_database(database, logger)
        self.logger = logger

    def find_file_path(self, arguments: FileArguments) -> List[Dict[str, str]]:
        """
        Find the file paths based on the arguments of the files
        Arguments:
        ark_node: NamedNode
        type_node: Optional[NamedNode]
        version: Optional[str]
        file_name: Optional[str]
        page: Optional[str]
        """
        # print(arguments)
        query = """
    PREFIX continuum: <https://continuum.lib.uchicago.edu/ontology/>
    PREFIX uchicago: <https://lib.uchicago.edu/>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX dc: <http://purl.org/dc/elements/1.1/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX ark: <http://ark.lib.uchicago.edu/>
    PREFIX edm: <http://www.europeana.eu/schemas/edm/>
    PREFIX premis: <http://www.loc.gov/premis/rdf/v3/>
    PREFIX ebucore: <http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#>

    SELECT ?ark ?path
    WHERE {
      VALUES ?ark { %s }
      ?arkNode continuum:hasArkID ?ark .
      # ?arkNode dc:rights ?rights .
      ?file dcterms:isPartOf ?arkNode .
      ?file continuum:fileType %s .
      ?file  continuum:hasPath ?path .
      ?file premis:basis/premis:allows uchicago:DownloadAllowed .
    """ % (
            Literal(arguments["ark_id"]),
            arguments["type_node"],
        )

        version = arguments.get("version")
        if version == "head":

            query = query + "    ?arkNode continuum:hasHeadObject ?file . "
        elif version:
            query = query + "      ?file continuum:partOfVersion %s ." % Literal(
                arguments["version"]
            )
        page = arguments.get("page")
        if page:
            query = query + "\n      ?file continuum:partNumber %s ." % Literal(page)
        if file_name := arguments.get("file_name"):
            if not page:
                query = query + "\n      ?file continuum:filename %s ." % Literal(
                    file_name
                )
            else:
                # if page:
                query = query + "\n      ?file continuum:filename %s ." % Literal(
                    page + "/" + file_name
                )
        if mime_type := arguments.get("mime_type"):
            query = query + "\n      ?file ebucore:hasMimeType %s ." % Literal(
                mime_type
            )

        query = query + "\n    }"

        self.logger.debug(f"Query For Path: \n {query}")
        results = self.store.query(query)
        if not isinstance(results, QuerySolutions):
            raise Exception("Error in query")
        return [{"ark": res["ark"].value, "path": res["path"].value} for res in results]
