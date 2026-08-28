from pocketsearch import Schema, PocketSearch, PocketWriter, PocketReader
from pocketsearch import Text
from pyoxigraph import QuerySolutions, Store
from typing import Callable
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()

INDEX_DB = Path(os.getenv("CONTINUUMDB")).parent / "index.db"


class SearchContents(Schema):
    text = Text(index=True)
    collection = Text(index=True)
    local_id = Text(index=True)
    # ark = Text(is_id_field=True)
    ark = Text(index=True)


# INDEX = QuickPocket(schema=SearchContents)
# INDEX = PocketSearch(schema=SearchContents)
# INDEX = PocketSearch()


def create_index(store: Store, logger: Callable):
    logger.info("creating indexes")
    search_index_query = """
        PREFIX continuum: <https://continuum.lib.uchicago.edu/ontology/>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX ark: <http://ark.lib.uchicago.edu/ark:61001/>
        PREFIX edm: <http://www.europeana.eu/schemas/edm/>

        SELECT ?arkNode ?ark ?collection ?localId
        WHERE {
            ?arkNode
                a edm:ProvidedCHO ;
                continuum:hasArkID ?ark ;
                continuum:originalIdentifier ?localId ;
            .
            OPTIONAL {
            ?arkNode
                dcterms:isPartOf/rdfs:label ?coll ;
                .
            }
            BIND(IF(BOUND(?coll), ?coll, "") AS ?collection)
            #BIND(REPLACE(STR(?arkNode), STR(ark:), "") AS ?ark)
        }
    """

    results = store.store.query(search_index_query)
    if not isinstance(results, QuerySolutions):
        raise Exception(f"Error in Query: {search_index_query}")
    with PocketWriter(db_name=str(INDEX_DB), schema=SearchContents) as writer:
        writer.delete_all()
        for result in results:
            try:
                writer.insert(
                    # file_name=result["arkNode"].value,
                    text=result["ark"].value,
                    ark=result["ark"].value,
                    collection=result["collection"].value,
                    # objid=result["ark"].value,
                    # collection=result["collection"].value,
                    local_id=result["localId"].value,
                )
            except PocketSearch.DatabaseError as e:
                logger.error(e, result)


# def update_index(store: Store):
#    INDEX.delete_all()
#    create_index(store)


def search_index(field: str, term: str):
    """
    provide the results of a search index term
    """
    with PocketReader(
        db_name=str(INDEX_DB),
        schema=SearchContents,
    ) as preader:
        match field:
            case "ark":
                return preader.autocomplete(text=term)
            case "collection":
                return preader.autocomplete(collection=term)
            case "local-id":
                return preader.autocomplete(local_id=term)
            case _:
                return preader.autocomplete(text=term)  # return document
