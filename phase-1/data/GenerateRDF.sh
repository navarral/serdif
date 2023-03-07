#!/bin/sh
echo "-----------------------------------"
echo "Mapping weather data - (2min)"
echo "-----------------------------------"
java -Xmx4112m -jar r2rml-v1.2.3b/r2rml.jar mapping/map_MetDataHly.properties
echo ""
echo "-----------------------------------"
echo "Mapping weather metadata"
echo "-----------------------------------"
java -jar r2rml-v1.2.3b/r2rml.jar mapping/map_MetMetadata.properties
echo ""
echo "-----------------------------------"
echo "Mapping Air Quality data - (2min)"
echo "-----------------------------------"
java -Xmx4112m -jar r2rml-v1.2.3b/r2rml.jar mapping/map_EpaAirQDataHly.properties
echo ""
echo "-----------------------------------"
echo "Mapping Air Quality metadata "
echo "-----------------------------------"
java -jar r2rml-v1.2.3b/r2rml.jar mapping/map_EpaAirQMetadata.properties
echo ""
echo "-----------------------------------"
echo "Mapping clinical data"
echo "-----------------------------------"
java -jar r2rml-v1.2.3b/r2rml.jar mapping/mapSerdif_Events.properties
echo ""
echo "-----------------------------------"
echo "RDF ready at the data/rdf folder"
echo "-----------------------------------"
