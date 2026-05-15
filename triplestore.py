from pyoxigraph import (
    NamedNode,
    Quad,
    Literal,
    Store,
    QuerySolutions,
    RdfFormat,
    QueryResultsFormat,
    QueryBoolean,
    QueryTriples,
)
from pathlib import Path
from werkzeug.security import generate_password_hash
from typing import Dict, Optional, TypedDict, List

import hashlib

import os
import shutil
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


class AuthenticationException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


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
    "continuum": "http://continuum.lib.uchicago.edu/ontology/",
    "cont": "http://continuum.lib.uchicago.edu/",
    "premis": "http://www.loc.gov/premis/rdf/v3/",
    "ebucore": "http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "edm": "http://www.europeana.eu/schemas/edm/",
}


ns = NS(PREFIXES)


def create_auth_graph(store: Store):
    """ """
    m = hashlib.sha256()
    user_graph = ns.cont.term("UserGraph")
    store.clear_graph(user_graph)
    username = os.getenv("CONTINUUMADMIN")
    pswrd = os.getenv("CONTINUUMKEY")
    m.update(username.encode("utf-8"))
    user_node = ns.cont.term("data/_User_" + m.hexdigest()[:16])

    store.add(Quad(user_node, ns.rdf.type, ns.continuum.User, user_graph))
    store.add(Quad(user_node, ns.continuum.userName, Literal(ADMIN), user_graph))
    store.add(
        Quad(
            user_node,
            ns.continuum.hashedPassword,
            Literal(generate_password_hash(ADMIN_KEY)),
            user_graph,
        )
    )
    return store


def fake_logger():
    def debug(s: str):
        print(s)

    def info(s: str):
        print(s)


def create_database(database: Path, logger=fake_logger):
    """Update the database"""

    # print(os.getcwd())
    turtle_time = os.path.getmtime(TURTLE_FILE)

    if database.exists():
        logger.info("Loading existing store")
        # store = Store(database)
        # store = Store.read_only(str(database))
        store = Store(str(database))
        logger.info("store loaded")
    else:
        store = Store(str(database))
        logger.info("loading store from ttl")
        with open(TURTLE_FILE, "r") as ttlp:
            store.bulk_load(ttlp, format=RdfFormat.TURTLE)
        logger.info("store loaded")
        store = create_auth_graph(store)
        store.optimize()
        store.flush()
        # store = Store.read_only(str(database))
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
    def __init__(self, database: Path, logger=fake_logger):
        self.store, self.turtle_time = create_database(database)
        self.logger = logger

    def query(self, query: str):
        results = self.store.query(query)

        # return self.store.query(query)
        match results:
            case QuerySolutions():
                return results.serialize(format=QueryResultsFormat.JSON)
            case QueryBoolean():
                return results.serialize(format=QueryResultsFormat.JSON)
            case QueryTriples():
                return results.serialize(format=RdfFormat.TURTLE)
            case _:
                pass
        return results.serialize(format=QueryResultsFormat.JSON)

    def update_query(self, query: str):
        return self.store.update(query)

    def update_cho(self, serialized_triples: str):
        temp_store = Store()
        temp_store.bulk_load(serialized_triples, format=RdfFormat.TURTLE)
        update_query = """
    PREFIX continuum: <http://continuum.lib.uchicago.edu/ontology/>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX ark: <http://ark.lib.uchicago.edu/>
    PREFIX edm: <http://www.europeana.eu/schemas/edm/>
    PREFIX premis: <http://www.loc.gov/premis/rdf/v3/>

    DELETE {
        ?arkNode continuum:hasHeadObject ?object .
    }
    WHERE {
        VALUES ?arkNode { %s }
        ?arkNode
            a edm:ProvidedCHO .
    }
        """ % "\n".join(
            [
                str(qwad.subject)
                for qwad in temp_store.quads_for_pattern(
                    None, ns.rdf.type, ns.edm.ProvidedCHO, None
                )
            ]
        )
        logger.debug("update query", update_query)

        self.store.update(update_query)
        self.store.bulk_load(serialized_triples, format=RdfFormat.TURTLE)

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
        self.logger.debug(f"arguments: {arguments}")
        query = """
    PREFIX continuum: <http://continuum.lib.uchicago.edu/ontology/>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX ark: <http://ark.lib.uchicago.edu/>
    PREFIX premis: <http://www.loc.gov/premis/rdf/v3/>

    SELECT ?ark ?path
    WHERE {
    VALUES ?ark { %s }
    ?arkNode continuum:hasArkID ?ark .
    ?file dcterms:isPartOf ?arkNode .
    #?file continuum:fileType %s .
    ?file  continuum:hasPath ?path .
    """ % (
            Literal(arguments["ark_id"]),
            arguments["type_node"],
        )

        version = arguments.get("version")
        if version == "head":

            query = query + "   ?arkNode continuum:hasHeadObject ?file . "
        elif version:
            query = query + "  ?file continuum:partOfVersion %s ." % Literal(
                arguments["version"]
            )
        page = arguments.get("page")
        if file_name := arguments.get("file_name"):
            if not page:

                query = query + "\n  ?file premis:originalName %s ." % Literal(
                    file_name
                )

            else:
                # if page:
                query = (
                    query
                    + "\n  ?file <http://www.loc.gov/premis/rdf/v3/originalName> %s ."
                    % Literal(page + "/" + file_name)
                )

        query = query + "\n }"
        self.logger.debug(f"find file path, query:  {query}")
        results = self.store.query(query)
        if not isinstance(results, QuerySolutions):
            raise Exception("Error in query")
        return [{"ark": res["ark"].value, "path": res["path"].value} for res in results]

    def fetch_user(self, username: str):
        """Fetch usernode and password"""
        if not username:
            raise AuthenticationException("No Username provided")
        query = """PREFIX continuum: <http://continuum.lib.uchicago.edu/ontology/>
        PREFIX cont: <http://continuum.lib.uchicago.edu/>

        SELECT ?usernode ?username ?pswrd
        WHERE {
            GRAPH cont:UserGraph {
                ?usernode
                    a continuum:User ;
                    continuum:userName ?username ;
                    continuum:hashedPassword ?pswrd ;
                .
                VALUES ?username { %s }
            }
        }
        """ % Literal(
            username
        )
        self.logger.debug(f"fetch user query: {query}")

        solution = next(self.store.query(query))
        usernode, username, pswrd = solution

        return usernode, username, pswrd

    def flush():
        self.store.flush()
