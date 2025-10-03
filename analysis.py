from rdflib import Graph, RDF, RDFS, DCAT, XSD, URIRef, Literal, Namespace
import requests
from pyshacl import validate
from datetime import datetime

DQV = Namespace('http://www.w3.org/ns/dqv#')
EX = Namespace('http://example.org/')
SH = Namespace ('http://www.w3.org/ns/shacl#')
DCT = Namespace('http://purl.org/dc/terms/')


def print_status(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"|{timestamp}| {message}")

def retrieve_datasets():
    url = 'https://datos.gob.es/virtuoso/sparql'
    query = """
        PREFIX dct: <http://purl.org/dc/terms/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dcat: <http://www.w3.org/ns/dcat#>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        
        DESCRIBE ?dataset ?distribution ?format ?media_type
        WHERE
        {
            ?dataset a dcat:Dataset ;
                dct:publisher ?publisher ;
                dcat:distribution ?distribution  .
            ?publisher foaf:name ?publisher_name.
            OPTIONAL {?distribution dct:format ?format }
            OPTIONAL {?distribution dcat:mediaType ?media_type }
            
            FILTER (CONTAINS (lcase(?publisher_name), "ministerio de sanidad"))
        }
    """

    headers = {
        "Accept": "text/turtle"
    }

    res = requests.get(url, params={"query": query}, verify=False, headers=headers)
    graph = Graph()
    graph.parse(data=res.text, format="ttl")

    return graph


def run_shacl_validation(graph):
    shapes = Graph()
    shapes.parse('input/shapes.ttl', format='ttl')

    conforms, shacl_report_graph, shacl_report_text = validate(
        graph,
        shacl_graph=shapes,
        abort_on_first=False,
        meta_shacl=False,
        advanced=True,
        debug=False
    )

    shacl_report_graph.serialize('output/shacl_report.ttl', format='ttl')
    return(shacl_report_graph)


def find_violation_nodes(shacl_report_graph, property):
    query = """
        PREFIX sh: <http://www.w3.org/ns/shacl#>
        PREFIX dcat: <http://www.w3.org/ns/dcat#>
        PREFIX dct: <http://purl.org/dc/terms/>
        SELECT DISTINCT ?node 
        WHERE {{
            ?s sh:focusNode ?node ;
            sh:resultPath {property}
        }}
    """
    res = list(shacl_report_graph.query(query.format(property=property)))
    return( [str(row['node']) for row in res] )


def url_accessibility(url):
    try:
        r = requests.head(str(url), allow_redirects=True, timeout=5)
        if r.status_code == 200:
            return True
        else: 
            return False
    except Exception:
        return False


def chekc_if_vocabulary(uri):
    headers = {'Accept': 'text/turtle'}
    g = Graph()
    res = requests.get(uri, headers=headers) # gets whole vocab, not only the triples for the resource
    g.parse(data=res.text, format='ttl')
    types = [str(o) for o in g.objects(URIRef(uri), RDF.type)] #its type indicates if its a controlled vocab or not
    if 'http://purl.org/dc/dcam/VocabularyEncodingScheme' in types:
        return True
    else:
        return False
    

def write_dataset_measures(graph, shacl_report_graph, dqv_report):
    violation_keywords = find_violation_nodes(shacl_report_graph, 'dcat:keyword')
    violation_theme = find_violation_nodes(shacl_report_graph, 'dcat:theme')

    for uri in graph.subjects(RDF.type, DCAT.Dataset):
        dqv_report.add((uri, RDF.type, DCAT.Dataset))
        for s, p, o in graph.triples((None, DCAT.distribution, None)):
            dqv_report.add((s, p, o))

        measurement_uri = URIRef(str(uri).replace('https://datos.gob.es/catalogo/', 'http://example.org/measurement-'))
        dqv_report.add((uri, DQV.hasQualityMeasurement, measurement_uri))
        dqv_report.add((measurement_uri, RDF.type, DQV.QualityMeasurement))
        dqv_report.add((measurement_uri, DQV.computedOn, uri))
        dqv_report.add((measurement_uri, DQV.isMeasurementOf, EX.datasetCompletenessMetric))
        
        value = 1
        if str(uri) in violation_keywords:
            value -= 0.5
            dqv_report.add((measurement_uri, RDFS.comment, Literal('Missing keywords (dcat:keyword).')))
        if str(uri) in violation_theme:
            value -= 0.5
            dqv_report.add((measurement_uri, RDFS.comment, Literal('Missing category (dcat:theme).')))

        dqv_report.add((measurement_uri, DQV.value, Literal(value, datatype=XSD.float)))
    return(dqv_report)


def write_dist_completeness_measures(graph, shacl_report_graph, dqv_report):
    violation_format = find_violation_nodes(shacl_report_graph, 'dct:format')
    violation_media_type = find_violation_nodes(shacl_report_graph, 'dcat:mediaType')

    for uri in graph.subjects(RDF.type, DCAT.Distribution):
        dqv_report.add((uri, RDF.type, DCAT.Distribution))
        measurement_uri = URIRef(str(uri).replace('https://datos.gob.es/catalogo/', 'http://example.org/completeness-measurement-'))
        dqv_report.add((uri, DQV.hasQualityMeasurement, measurement_uri))
        dqv_report.add((measurement_uri, RDF.type, DQV.QualityMeasurement))
        dqv_report.add((measurement_uri, DQV.computedOn, uri))
        dqv_report.add((measurement_uri, DQV.isMeasurementOf, EX.distributionCompletenessMetric))
        
        value = 1
        if str(uri) in violation_format:
            value -= 0.5
            dqv_report.add((measurement_uri, RDFS.comment, Literal('Missing format (dct:format).')))
        if str(uri) in violation_media_type:
            value -= 0.5
            dqv_report.add((measurement_uri, RDFS.comment, Literal('Missing media type (dcat:mediaType).')))

        dqv_report.add((measurement_uri, DQV.value, Literal(value, datatype=XSD.float)))
    return(dqv_report)


def write_dist_availability_measures(graph, shacl_report_graph, dqv_report):
    violation_nodes_acc = find_violation_nodes(shacl_report_graph, 'dcat:accessURL')
    violation_nodes_down = find_violation_nodes(shacl_report_graph, 'dcat:downloadURL')

    for dist_uri in graph.subjects(RDF.type, DCAT.Distribution):
        down_measure_uri = URIRef(str(dist_uri).replace('https://datos.gob.es/catalogo/', 'http://example.org/download-accessibility-measurement-'))
        acc_measure_uri = URIRef(str(dist_uri).replace('https://datos.gob.es/catalogo/', 'http://example.org/access-accessibility-measurement-'))
        
        for uri in graph.objects(dist_uri, DCAT.downloadURL):
            if dist_uri in violation_nodes_down: # if captured in shape, malformed URL
                is_accesible = False
            is_accesible = url_accessibility(uri)
            dqv_report.add((dist_uri, DQV.hasQualityMeasurement, down_measure_uri))
            dqv_report.add((down_measure_uri, RDF.type, DQV.QualityMeasurement))
            dqv_report.add((down_measure_uri, DQV.computedOn, dist_uri))
            dqv_report.add((down_measure_uri, DQV.isMeasurementOf, EX.downloadURLAvailabilityMetric))
            dqv_report.add((down_measure_uri, DQV.value, Literal(is_accesible, datatype=XSD.boolean)))

        for uri in graph.objects(dist_uri, DCAT.accessURL):
            if dist_uri in violation_nodes_acc: # if captured in shape, malformed URL
                is_accesible = False
            is_accesible = url_accessibility(uri)
            dqv_report.add((dist_uri, DQV.hasQualityMeasurement, acc_measure_uri))
            dqv_report.add((acc_measure_uri, RDF.type, DQV.QualityMeasurement))
            dqv_report.add((acc_measure_uri, DQV.computedOn, dist_uri))
            dqv_report.add((acc_measure_uri, DQV.isMeasurementOf, EX.accessURLAvailabilityMetric))
            dqv_report.add((acc_measure_uri, DQV.value, Literal(is_accesible, datatype=XSD.boolean)))
    return(dqv_report)


def write_dist_interoperability_measures(graph, shacl_report_graph, dqv_report):
    for dist_uri in graph.subjects(RDF.type, DCAT.Distribution):
        format_measure_uri = URIRef(str(dist_uri).replace('https://datos.gob.es/catalogo/', 'http://example.org/format-interop-measurement-'))
        mt_measure_uri = URIRef(str(dist_uri).replace('https://datos.gob.es/catalogo/', 'http://example.org/mediatype-interop-measurement-'))
        
        for uri in graph.objects(dist_uri, URIRef('http://purl.org/dc/terms/format')):    
            dqv_report.add((dist_uri, DQV.hasQualityMeasurement, format_measure_uri))
            dqv_report.add((format_measure_uri, RDF.type, DQV.QualityMeasurement))
            dqv_report.add((format_measure_uri, DQV.computedOn, dist_uri))
            dqv_report.add((format_measure_uri, DQV.isMeasurementOf, EX.formatInControlledVocabularyMetric))
            format_type = [str(o) for o in list(graph.objects(uri, RDF.type))][0]
            is_vocabulary = chekc_if_vocabulary(format_type)
            dqv_report.add((format_measure_uri, DQV.value, Literal(is_vocabulary, datatype=XSD.boolean)))

        for uri in graph.objects(dist_uri, DCAT.mediaType):   
            dqv_report.add((dist_uri, DQV.hasQualityMeasurement, mt_measure_uri))
            dqv_report.add((mt_measure_uri, RDF.type, DQV.QualityMeasurement))
            dqv_report.add((mt_measure_uri, DQV.computedOn, dist_uri))
            dqv_report.add((mt_measure_uri, DQV.isMeasurementOf, EX.mediaTypeInControlledVocabularyMetric))
            mt_type = [str(o) for o in list(graph.objects(uri, RDF.type))][0]
            is_vocabulary = chekc_if_vocabulary(mt_type)
            dqv_report.add((mt_measure_uri, DQV.value, Literal(is_vocabulary, datatype=XSD.boolean)))
    return(dqv_report)

def generate_dqv_report(graph, shacl_report_graph):
    dqv_report = Graph()
    dqv_report.parse('./input/metrics.ttl', format='ttl')
    
    dqv_report = write_dataset_measures(graph, shacl_report_graph, dqv_report)
    dqv_report = write_dist_completeness_measures(graph, shacl_report_graph, dqv_report)
    dqv_report = write_dist_availability_measures(graph, shacl_report_graph, dqv_report)
    dqv_report = write_dist_interoperability_measures(graph, shacl_report_graph, dqv_report)

    dqv_report.serialize('output/dqv_report.ttl', format='ttl')

if __name__ == "__main__":
    print_status("Retrieving datasets")
    graph = retrieve_datasets()

    print_status("Running SHACL validation")
    shacl_report_graph = run_shacl_validation(graph)

    print_status("Writing report")
    generate_dqv_report(graph, shacl_report_graph)

    print_status("All done, find the report in the folder 'output/'")