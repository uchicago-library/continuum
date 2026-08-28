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
            store = load_store(database, turtle_time, logger)

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

    def get_collections(self):
        print("hello?")
        query = """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX continuum: <https://continuum.lib.uchicago.edu/ontology/>

        SELECT ?collection
        WHERE {
        ?collectionNode
            a continuum:Collection ;
            rdfs:label ?collection ;
            .
        }
        """
        results = self.store.query(query)
        return [{"Collection": res["collection"].value} for res in results]

    def get_arks(self):
        self.logger.debug("In Arks")
        query = """
        PREFIX edm: <http://www.europeana.eu/schemas/edm/>
        PREFIX continuum: <https://continuum.lib.uchicago.edu/ontology/>

        SELECT ?ark
        WHERE {
            ?arkNode
                a edm:ProvidedCHO ;
                continuum:hasArkID ?ark ;
            .
        }
        """
        results = self.store.query(query)
        return [
            {"Ark": res["ark"].value.replace(PREFIXES["ark"], "")} for res in results
        ]

    def get_local_ids(self):
        query = """

        PREFIX edm: <http://www.europeana.eu/schemas/edm/>
        PREFIX continuum: <https://continuum.lib.uchicago.edu/ontology/>

        SELECT ?localId
        WHERE {
            ?ark
                a edm:ProvidedCHO ;
                continuum:originalIdentifier ?localId ;
            .
        }
        """
        results = self.store.query(query)
        return [{"local-id": res["localId"].value} for res in results]

    def format_main_table_results(self, query: str):
        """
        Query needs to have the arguments 'collection', 'ark', and 'local-id'
        provide the query and format it for the results"""
        self.logger.debug("Format Main table Query: {query}")
        results = self.store.query(query)
        if not isinstance(results, QuerySolutions):
            raise Exception(f"Error in Query {query}")
        # print(results)
        return [
            {
                "collection": res["collection"].value if res["collection"] else "",
                "ark": res["ark"].value,
                "local-id": res["local_id"].value,
            }
            for res in results
        ]

    def find_ark(self, ark_id: str):
        # print("In find ark")
        """
        if ark_id.startswith("ark:61001/"):
            ark_node = NamedNode(PREFIXES["ark"] + ark_id)
        elif ark_id.startswith("ark:/61001/"):
            ark_node
        else:
            ark_node = NamedNode(f"{PREFIXES['ark']}ark:61001/{ark_id}")
        """
        query = """
        PREFIX continuum: <https://continuum.lib.uchicago.edu/ontology/>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX edm: <http://www.europeana.eu/schemas/edm/>
        PREFIX ark: <http://ark.lib.uchicago.edu/ark:61001/>
        SELECT ?collection ?ark ?local_id
        WHERE{
            VALUES ?ark { %s }
            ?arkNode
                a edm:ProvidedCHO ;
                continuum:hasArkID ?ark ;
                continuum:originalIdentifier ?local_id ;
            .
            OPTIONAL {
              ?arkNode
                dcterms:isPartOf/rdfs:label ?coll .
            }
            BIND(IF(BOUND(?coll),  "None", ?coll) AS ?collection)
        }
        """ % Literal(ark_id.replace("ark:61001/", "").replace("ark:/61001/", ""))
        print(query)
        return self.format_main_table_results(query)

    def find_local_id(self, local_id: str):
        """find an ark by the local id"""
        local_node = Literal(local_id)
        query = """
        PREFIX continuum: <https://continuum.lib.uchicago.edu/ontology/>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX ark: <http://ark.lib.uchicago.edu/ark:61001/>
        PREFIX edm: <http://www.europeana.eu/schemas/edm/>

        SELECT ?collection ?ark ?local_id
        WHERE{
            VALUES ?local_id { %s }
            ?arkNode
                a edm:ProvidedCHO ;
                continuum:originalIdentifier ?local_id ;
                continuum:hasArkID ?ark ;
                #dcterms:isPartOf/rdfs:label ?collection ;
            .
            OPTIONAL {
              ?arkNode
                dcterms:isPartOf/rdfs:label ?coll .
            }
            BIND(IF(BOUND(?coll),  "None", ?coll) AS ?collection)

            #BIND(REPLACE(STR(?arkNode), str(ark:), "") AS ?ark)
        }
        """ % local_node
        print(f"query: {query}")
        return self.format_main_table_results(query)

    def find_collection(self, collection: str):
        """find all of the items in a collection"""
        collection_node = Literal(collection)
        query = """
        PREFIX continuum: <https://continuum.lib.uchicago.edu/ontology/>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX ark: <http://ark.lib.uchicago.edu/ark:61001/>

        SELECT ?collection ?ark ?local_id
        WHERE {
            VALUES ?collection { %s }
            ?collectionNode
                a continuum:Collection ;
                rdfs:label ?collection ;
                ^dcterms:isPartOf ?arkNode ;
            .
            ?arkNode
                continuum:originalIdentifier ?local_id ;
                continuum:hasArkID ?ark ;
            .
            #BIND(REPLACE(STR(?arkNode), str(ark:), "") AS ?ark)
        }
        """ % collection_node
        # print(f"query: {query}")
        return self.format_main_table_results(query)

    def search_for_term(self, column: str, term: str):
        """ """
        print(f"in search for term: {column}:: {term}")
        match column.lower():
            case "ark":
                return self.find_ark(term)
            case "collection":
                return self.find_collection(term)
            case "local-id":
                print(term)
                return self.find_local_id(term)
            case _:
                return {"Error": f"No column named {column}, for term: {term}"}

    def retrieve_file_data(self, ark_id: str):
        """ """
        file_query = """
    PREFIX continuum: <https://continuum.lib.uchicago.edu/ontology/>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?file ?file_type ?path ?version ?created ?url
    WHERE {
    VALUES ?ark { %s }
    ?arkNode
            continuum:hasArkID ?ark .
    ?file
        continuum:fileType ?file_type ;
        continuum:hasPath ?path ;
        continuum:partOfVersion ?version ;
        continuum:filename ?filename ;
        dcterms:created ?created ;
        dcterms:isPartOf ?arkNode ;
        .
        BIND(CONCAT("/file/", ?ark, "/", ?filename, "/", ?version) AS ?url)
    }
        """ % Literal(ark_id)

        # print(file_query)

        results = self.store.query(file_query)
        if not isinstance(results, QuerySolutions):
            raise Exception("Error In query")
        res: Dict[str, List[Dict[str, str]]] = {}
        for r in results:
            version = r["version"].value
            res.setdefault(version, []).append(
                {
                    "file_type": r["file_type"].value,
                    "path": r["path"].value,
                    "created": r["created"].value,
                    "url": r["url"].value,
                }
            )
        # print(res)
        return res

    def retrieve_ark_data(self, ark_id: str):
        ark_query = """
    PREFIX continuum: <https://continuum.lib.uchicago.edu/ontology/>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX ark: <http://ark.lib.uchicago.edu/>

    SELECT
        ?ark
        ?head
        (GROUP_CONCAT(DISTINCT STR(?local); separator="|") AS ?local_id)
        (GROUP_CONCAT(DISTINCT STR(?coll); separator="|") AS ?collection)
        (GROUP_CONCAT(DISTINCT STR(?modified); separator="|") AS ?mods)
    WHERE {
    VALUES ?arkId { %s }
    ?ark
        continuum:head ?head ;
        continuum:hasArkID ?arkId ;
        continuum:originalIdentifier ?local ;
        dcterms:modified ?modified ;
        .
        OPTIONAL {
        ?ark
            dcterms:isPartOf/rdfs:label ?coll ;
        .
        }
    }
    GROUP BY ?ark ?head
        """ % Literal(ark_id)
        self.logger.debug(f"ark_query: {ark_query}")

        results = self.store.query(ark_query)
        # self.logger.debug([r for r in results])
        if not isinstance(results, QuerySolutions):
            raise Exception("Error in query")
        return [
            {
                "ark": r["ark"].value,
                "head": r["head"].value,
                "local_id": r["local_id"].value.split("|"),
                "collection": (
                    r["collection"].value.split("|") if r["collection"] else ""
                ),
                "modified": r["mods"].value.split("|"),
            }
            for r in results
        ]

    def retrieve_object_data(
        self,
        ark_id: str,
    ) -> Dict[str, str]:
        """
        Grab all of the Information about an Object
        """

        ark_object = self.retrieve_ark_data(ark_id)
        self.logger.debug(f"ark object:  {ark_object}")
        file_object = self.retrieve_file_data(ark_id)
        self.logger.debug(f"file_object: {file_object}")

        return {"ark": ark_object, "file": file_object}
