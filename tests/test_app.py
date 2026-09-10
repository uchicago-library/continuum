from continuum.app import construct_file_arguments
from pyoxigraph import NamedNode

##########################################################
#
# Tests for the construct_file_arguments
# This makes sure that files are being passed correctly
#
##########################################################


def test_part_number(app):
    args = construct_file_arguments(
        app.logger, "bwerwe", file_name="00000008", page=None, version=None
    )
    assert args["ark_id"] == "bwerwe"
    assert args["type_node"] == NamedNode(
        "https://continuum.lib.uchicago.edu/ontology/" + "Preservation"
    )
    assert args["version"] is None
    assert args["file_name"] is None
    assert args["page"] == "00000008"
    assert args["mime_type"] is None


def test_version_number(app):
    args = construct_file_arguments(
        app.logger, "bwerwe", file_name="v1", page=None, version=None
    )
    assert args["ark_id"] == "bwerwe"
    assert args["type_node"] == NamedNode(
        "https://continuum.lib.uchicago.edu/ontology/" + "Preservation"
    )
    assert args["version"] == "v1"
    assert args["file_name"] is None
    assert args["page"] is None
    assert args["mime_type"] is None


def test_vaf_file(app):
    args = construct_file_arguments(
        app.logger, "bwerwe", file_name="file.vaf.tif", page=None, version=None
    )
    assert args["ark_id"] == "bwerwe"
    assert args["type_node"] == NamedNode(
        "https://continuum.lib.uchicago.edu/ontology/" + "Viewer"
    )
    assert args["version"] is None
    assert args["file_name"] == "file.vaf.tif"
    assert args["page"] is None
    assert args["mime_type"] is None


def test_manifest_file(app):
    args = construct_file_arguments(
        app.logger, "bwerwe", file_name="file.manifest.json", page=None, version=None
    )
    assert args["ark_id"] == "bwerwe"
    assert args["type_node"] == NamedNode(
        "https://continuum.lib.uchicago.edu/ontology/" + "Manifest"
    )
    assert args["version"] is None
    assert args["file_name"] == "file.manifest.json"
    assert args["page"] is None
    assert args["mime_type"] is None


def test_pdf_file(app):
    args = construct_file_arguments(
        app.logger, "bwerwe", file_name="pdf", page=None, version=None
    )
    assert args["ark_id"] == "bwerwe"
    assert args["type_node"] == NamedNode(
        "https://continuum.lib.uchicago.edu/ontology/" + "Preservation"
    )
    assert args["version"] is None
    assert args["file_name"] is None
    assert args["page"] is None
    assert args["mime_type"] == "application/pdf"


def test_pres_file(app):
    args = construct_file_arguments(
        app.logger, "bwerwe", file_name="pres", page=None, version=None
    )
    assert args["ark_id"] == "bwerwe"
    assert args["type_node"] == NamedNode(
        "https://continuum.lib.uchicago.edu/ontology/" + "Preservation"
    )
    assert args["version"] is None
    assert args["file_name"] is None
    assert args["page"] is None
    assert args["mime_type"] is None


def test_ocr_file(app):
    args = construct_file_arguments(
        app.logger, "bwerwe", file_name="ocr", page=None, version=None
    )
    assert args["ark_id"] == "bwerwe"
    assert args["type_node"] == NamedNode(
        "https://continuum.lib.uchicago.edu/ontology/" + "Supplemental"
    )
    assert args["version"] is None
    assert args["file_name"] == "file.txt"
    assert args["page"] is None
    assert args["mime_type"] is None


def test_mets_file(app):
    args = construct_file_arguments(
        app.logger, "bwerwe", file_name="mets", page=None, version=None
    )
    assert args["ark_id"] == "bwerwe"
    assert args["type_node"] == NamedNode(
        "https://continuum.lib.uchicago.edu/ontology/" + "Supplemental"
    )
    assert args["version"] is None
    assert args["file_name"] == "file.mets.xml"
    assert args["page"] is None
    assert args["mime_type"] is None


def test_alto_file(app):
    args = construct_file_arguments(
        app.logger, "bwerwe", file_name="alto", page=None, version=None
    )
    assert args["ark_id"] == "bwerwe"
    assert args["type_node"] == NamedNode(
        "https://continuum.lib.uchicago.edu/ontology/" + "Supplemental"
    )
    assert args["version"] is None
    assert args["file_name"] == "file.xml"
    assert args["page"] is None
    assert args["mime_type"] is None


def test_preservation_file(app):
    args = construct_file_arguments(
        app.logger, "bwerwe", file_name=None, page=None, version=None
    )
    assert args["ark_id"] == "bwerwe"
    assert args["type_node"] == NamedNode(
        "https://continuum.lib.uchicago.edu/ontology/" + "Preservation"
    )
    assert args["version"] is None
    assert args["file_name"] is None
    assert args["page"] is None
    assert args["mime_type"] is None


def test_file_test(app):
    args = construct_file_arguments(
        app.logger, "bwerwe", file_name="file.tif", page=None, version=None
    )
    assert args["ark_id"] == "bwerwe"
    assert args["type_node"] == NamedNode(
        "https://continuum.lib.uchicago.edu/ontology/" + "Preservation"
    )
    assert args["version"] is None
    assert args["file_name"] == "file.tif"
    assert args["page"] is None
    assert args["mime_type"] is None


def test_filexml_test(app):
    args = construct_file_arguments(
        app.logger, "bwerwe", file_name="file.xml", page=None, version=None
    )
    assert args["ark_id"] == "bwerwe"
    assert args["type_node"] == NamedNode(
        "https://continuum.lib.uchicago.edu/ontology/" + "Supplemental"
    )
    assert args["version"] is None
    assert args["file_name"] == "file.xml"
    assert args["page"] is None
    assert args["mime_type"] is None
