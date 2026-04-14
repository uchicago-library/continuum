from pyoxigraph import NamedNode, Literal, Store, QuerySolutions, RdfFormat
from pathlib import Path
from typing import Dict, Optional, TypedDict, List

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
}


ns = NS(PREFIXES)


def create_database(database: Path):

    # print(os.getcwd())

    if database.exists():
        print("Loading existing store")
        # store = Store(database)
        store = Store.read_only(str(database))
        print("store loaded")
    else:
        store = Store(database)
        print("loading store from ttl")
        with open(TURTLE_FILE, "r") as ttlp:
            store.bulk_load(ttlp, format=RdfFormat.TURTLE)
        print("store loaded")
        store.optimize()
        store.flush()
        store = Store.read_only(str(database))
    return store


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
    def __init__(self, database: Path):
        self.store = create_database(database)

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
        # print(query)
        results = self.store.query(query)
        if not isinstance(results, QuerySolutions):
            raise Exception("Error in query")
        return [{"ark": res["ark"].value, "path": res["path"].value} for res in results]
