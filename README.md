# serdif

The Semantic Environmental and Rare disease Data Integration Framework (SERDIF) seeks to enable the data linkage between health events and environmental data for health data researchers. 

## Latest working version: offline-version

* **Offline-version:** [Docker](https://github.com/navarral/serdif/tree/main/offline-version)
* **Example user interface:** [https://serdif.fht.org/](https://serdif.fht.org/)

## Summary
SERDIF is combination of methods and tools based on the use of World Wide Web Consortium (W3C) standards to model graph data: the Resource Description Framework ([RDF](https://www.w3.org/TR/rdf11-concepts/)), the RDF query language SPARQL [SPARQL](https://www.w3.org/TR/sparql11-query/) and the databases to store RDF graphs.

1. The Knowledge Graph (KG) component is where environmental data and health data is linked together through location and time using [RDF](https://www.w3.org/TR/rdf11-concepts/) and [SPARQL queries](https://www.w3.org/TR/sparql11-query/). 
2. The Methodology is a series of steps that guides the researcher in linking particular events with environmental data using Semantic Web technologies.
3. The User Interface (UI) component is designed from a user-centric perspective to support health data researchers access, explore and export the linked health-environmental data with appropriate visualisations, and by facilitating the query formulation for non-Semantic Web experts.

The data linkage takes place at a query level where the geographic location ([GeoSPARQL](https://www.ogc.org/standards/geosparql)) and time window ([xsd:dateTime](https://www.w3.org/TR/xmlschema11-2/) are used as the common aspects to link the data for each event.



## Evaluation

The usability and potential usefulness of the SERDIF framework has been evaluated following an interative  user-centred design that included three phases. The KG and UI documentation for each of the phases is made available in `phase-1/`, `phase-2/` and `phase-3/`.

## Publications associated with each of the phases

* **phase-1**: A. Navarro-Gallinad, F. Orlandi and D. O’Sullivan, Enhancing Rare Disease Research with Semantic Integration of Environmental and Health Data, in: The 10th International Joint Conference on Knowledge Graphs, IJCKG’21, Association for Computing Machinery, New York, NY, USA, 2021, pp. 19–27. ISBN 978-1-4503-9565-6.[https://doi.org/10.1145/3502223.3502226](https://doi.org/10.1145/3502223.3502226)

* **phase-2**: A. Navarro-Gallinad, F. Orlandi, J. Scott, M. Little and D. O’Sullivan, Evaluating the usability of a semantic environmental health data framework: approach and study. Semantic Web Journal 11(1) (2022), Publisher: IOS Press. [https://doi.org/10.3233/SW-223212](https://doi.org/10.3233/SW-223212)


* **phase-3**: Navarro-Gallinad, A., Orlandi, F., Scott, J. et al. Enabling data linkages for rare diseases in a resilient environment with the SERDIF framework. npj Digital Medicine 7, 274 (2024). [https://doi.org/10.1038/s41746-024-01267-6](https://doi.org/10.1038/s41746-024-01267-6)

## Contact
This space is administered by:  

**Albert Navarro-Gallinad**  
*PhD Student in Computer Science*  
[ADAPT Centre for Digital Content](https://www.adaptcentre.ie/) in [Trinity College Dublin](https://www.tcd.ie/)
Dublin, Ireland  
<anavarro@tcd.ie>  

GitHub: [navarral](https://github.com/navarral)

ORCID: [0000-0002-2336-753X](https://orcid.org/0000-0002-2336-753X)   
