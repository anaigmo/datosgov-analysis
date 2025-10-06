# Parcial FAIR analysis of datasets in datos.gov

The resources in this repository analyse datasets extracted from [datos.gov.es](https://datos.gob.es/en/sparql), particularly the ones published by the Ministry of Health (Ministerio de Sanidad), and analyse them in terms of some aspects of the FAIR principles. The report of this analysis is based on SHACL validation and is modelled according to the [Data Quality Vocabulary](https://www.w3.org/TR/vocab-dqv/). 

The following aspects of the datasets have been analysed:
* Findability:
    1. Are keyworkds provided?
    2. Are categories provided?
* Accessibility:
    1. Is accessible the URL provided as "dcat:accessURL"?
    2. Is accessible the URL provided as "dcat:downloadURL"?
* Interoperability:
    1. Is the format of the distribution associated to the dataset provided?
    2. Is the media type of the distribution associated to the dataset provided?
    3. Do the formats and media types provided come from a controlled vocabulary?

## Structure of the repository
* `python_app/`: folder containing the script and resources needed to run the validation in docker.
* `input/`: input files needed to run the script.
    * `shapes.ttl`: SHACL shapes for analysing the dataset's metadata.
    * `metrics.ttl`: Metrics defined to describe the results of the analysis.
* `output/`: output files produced in the analysis that the script performs.
    * `shacl_report.ttl`: Intermediate repor with the results of the SHACL validation.
    * `dqv_report.ttl`: Final analysis report described with the [Data Quality Vocabulary](https://www.w3.org/TR/vocab-dqv/).
* `analysis.ipynb`: testing environment with the development of the script in the format of Jupyter Notebook.
* `analysis.py`: Python script to run the dataset analysis. It takes the files `input/shapes.ttl` and `inpit/metrics.ttl`, and produces the `shacl_report.ttl` intermediate report, and the final report `dqv_report.ttl`. 
* `requirements.txt`: Python packages that need to be installed in order to run the script
* `docker-compose.yml`: Docker compose file for executing the docker containers. 

## How to run

The analysis can be run as a python script, or with Docker. 

### Docker

It is required to have installed Docker and Docker compose. The docker-compose consists of two services:
* **loader**: Python image that runs the script, produdes the report and sends it to fuseki.
* **fuseki**: [Jena fuseki]((https://hub.docker.com/r/stain/jena-fuseki)) triplestore where the final report is uploaded and available for consumption in http://localhost:3030

The command to run it is:
```
docker compose up
```

The script is run as soon as the container is up, and sends the data to the triplestore once it's finished. The process takes about 3-5 min. After that, the analysis report can be queried in the Fuseki endpoint available in http://localhost:3030. 

### Python 

A version of the script that does not upload the resulting report to a triplestore is also available. To run it this way, it is needed to have Python installed, and the requirements for the script. 

```
pip install -r requirements.txt
python analysis.py
```

The report is produced in `output/dqv_report.ttl`, which is a Turtle file ready to be uploaded to any triplestore. A version of the script is also available in a Jupyter Notebook, `analysis.ipynb`.


## Attributions
Author and contact information:
* Ana Iglesias (ana.iglesias.molina@gmail.com)


