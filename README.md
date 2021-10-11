
## Documentation for v 0.8

### 1. Copernicus Core Services Interface

#### 1.1 Rationale
Products of Copernicus Services can be accessed from various access points like DIASes or CDSAPI etc. These access points differ from each other according to which Copernicus Services are hosted on the access point, how can be searched and in the form of standard response. Copernicus Core Services Interface is intended to ease access for CURE applications and users to Earth Observation products, especially the Copernicus Data, from the Sentinel satellites,  the Copernicus Core Services ́datasets hosted by various providers such as Creodias, Mundi, Onda and others. 

#### 1.2 Copernicus Core Services Interface implementation

Copernicus Core Services Interface is a RESTfull application offering search API following OpenSearch specification.  By the API can be searched all registered catalogues.  All received feeds for a given search query are parsed and returned in a standardized form containing product metadata, geographic information and links for downloadable or mountable content. The application does not provide only the search over DIASes but allows to search in other resources like local and city open data APIs upon their registration into the CCSI. These APIs can be integrated into the CCSI in the semi-automatic process if follows the certain specification. For resource registration, users with certain permission are allowed to register new resources. 

#### 1.3 Supported protocol
Copernicus Core Services Interface support OpenSearch API protocol:
- with query options as Parameters
- with also query options as Search Terms

#### 1.4 Protocol standards
The OpenSearch protocol implemented in CCSI follows standards defined in the following documents:

| Document ID  | Document Name  |Issue  | Link  |
| -------------|:-------------: | -----:| -----:|
|              | OpenSearch     | 1.1   | [http://www.opensearch.org/Home](http://www.opensearch.org/Home)|
|OGC 10-157r3  |Earth Observation Metadata Profile of Observations & Measurements|1.0|[link](https://portal.opengeospatial.org/files/?artifact_id=47040)
|OGC 10-032r8|OGC OpenSearch Geo and Time Extensions|1.0|[link](http://www.opengis.net/doc/IS/opensearchgeo/1.0)|
|OGC 10-026r8 |OGC OpenSearch Extension for Earth Observation|1.0|[link](http://docs.opengeospatial.org/is/13-026r8/13-026r8.html)

#### 1.5. Access 
Copernicus Core Services Interface access in the current version is open, and the querying access point can be reached through HTTP queries.

### 2 OpenSearch API
This chapter is dedicated to the description of the implementation of OpenSearch specification within the Copernicus Core Services Interface.  In this chapter is described the API endpoints structure, search parameters, building of queries and standard responses.

#### 2.1 Building an OpenSearch endpoint URI
Copernicus Core Services Interface is queryable with OpenSearch queries through HTTP GET requests. CCSI has two basic variations of Open Search URIs addressing the resource/products exposed by the Open Search Service:
- URI addressing all catalogues/resources registered in CCSI:
```<hostname>/<path>/<response from>/search?```
- URI addressing specific catalogue or resource registered in CCSI:
```<hostname>/<path>/<recourse>/<response from>/search?```


where: 

```<hostname>/<path>```  is service root

```<response from>``` is the requested format of responses and has two options json or atom. 

URI for response in atom format:```<hostname>/<path>/atom/search?```

URI for response in json format:```<hostname>/<path>/json/search?```

```<recourse>``` is a unique name of a registered catalog or resource. Together with the rest of URI define the endpoint specific for selected catalogue/resource. This endpoint accept only catalogue/resource specific parameters

#### 2.2 OpenSearch Description Document
Implemented OpenSearch protocol is self-descriptive. Each endpoint exposes its own description document (OSDD). Description document provides definition of available collections and parameters and their possible values.

URI for all description document describing search parameter for querying all catalogues/resources is a form:

```<hostname>/<path>/<response from>/search/description.xml``` 

This description document provide register of all parameters that are accept by global endpoint

URI for all description document describing search parameter for querying specific catalogues/resources is in a form:

``` <hostname>/<path>/<response from>/<recourse>/search/description.xml``` 

This description document provides a register of recourse specific parameters that are accepted by endpoint.

#### 2.3 OpenSearch query parameters
Parameters are limited to a short list of metadata filters. 

##### 2.3.1 Filtering catalogues and resources
Copernicus Core Services Interface providing access to various catalogues and resources. Selection of particular resources is provided by parameters:
- *recourse:* Recourse is a metadata filter used for selection of catalogues and resources. Is an option parameter that acquires only certain values. These values are identical with resource 's unique name defining each endpoint. Parameter is a multi-value parameter when multiple values are separated by “,”.  
- *collection:* Recourse is a metadata filter used for selection of collection. Certain collection can be provided by different recourses.  Is an option parameter that acquires only certain values. One resource can have a multiple collections.  Parameter is a multi-value parameter when multiple values are separated by “,”.  

##### 2.3.2 Temporal filtering
Date metadata can be filtered through temporal filtering. It provided by two parameters:
- timestart
- timeend

Expected format of parameter is in form “yyyy-mm-ddThh:nn:ss” that can be 
 	shortened for more time precise elements.
 	
```<hostname>/<path>/<recourse>/<response from>/search?timestart=2020-12-18T12:00:00```

alternatively

```<hostname>/<poth>/<recourse>/<response from>/search?timestart=2020-12-18```

##### 2.3.3 Geographical filtering
Geographical metadata can be filtered by parameters:

*geometry*

Geometry parameter accepts geometry in WKT format coordinates in decimal degrees (EPSG:4326). Accepted geometries are: polygon, linestring, point

```<hostname>/<path>/<recourse>/<response from>/search?geometry=POLYGON((-4.53 29.85,26.75 29.85,26.75 46.80,-4.53 46.80,-4.53 29.85))```

*bbox*

Bbox parameter filter data base on geographical bounding box. Coordinates are expected in decimal degrees (EPSG:4326) in order west, south, east, north. e.g. bbox=-61.3,14.3,-60.8,14.9

```<hostname>/<path>/<recourse>/<response from>/search?bbox=-61.3,14.3,-60.8,14.9```

*lat, lon, radius*

Lat, Lon, Radius parameters have to be provided together.  Lat, Lon parameters are expected in decimal degrees (EPSG:4326). Radius as a float in meters

```<hostname>/<path>/<recourse>/<response from>/search?lat=-61.3&lon=14.3&radius=1000```

##### 2.3.4 Filtering for specific product

Specific product can be selected by providing productid 

```<hostname>/<path>/<recourse>/<response from>/search?productid=z_cams_c_ecmf_20200616120000_prod_fc_sfc_062_gtco3```

##### 2.3.5 Entries filtering
Received entries for given query can be filtered by parameters:

*maxrecords*

Maxrecord parameter defines the number of entries per page. expected type is integer. Default value is 50

```<hostname>/<path>/<recourse>/<response from>/search?maxrecords=50```

*startindex*

Startindex parameter defines from which index the entries will be returned. Minimum value is 1

```<hostname>/<path>/<recourse>/<response from>/search?startindex=5```


##### 2.3.6 Entries sorting

Temporary disabled

##### 2.3.7 Special parameters
*custom*

Copernicus Core Services Interface is intended to provide access to various catalogues/resources. The exposed parameters for filtering and specification of products provided by single recourse may differ from others. This resource specific parameters are registered with the prefix "custom:" e.g. parameter for the specification of orbitderection is labelled as custom:orbitdirection. List of custom parameters and their specification, pattern, optional or default values is accessible via description dokuments.

```<hostname>/<path>/<recourse>/<response from>/search?custom:orbitdirection= descending```

*solr*

Some registered catalogues/resources allow use of Apache Lucene free text search. Parameter solr is a boolean parameter that defines the searchterm following the  free text search convention. If  solr=true, search query is injected only into the resources that supports free text search. Default value is false

```<hostname>/<path>/<recourse>/<response from>/search?searchterm=(platformname:Sentinel-1 AND producttype:SLC AND sensoroperationalmode:SM)&solr=true```
     
##### 2.3.8 Query string format
Query string accepted by CCSI OpenSearch API:
is expected in form parameter=value 

```.../<response from>/search?searchterm=value```

query string is not case sensitive. Accepted response arguments are converted to lowercase
multiple parameters a separated by “&” letter

```.../<response from>/search?searchterm=value&productid=value```

is accepted multiple choice parameters i.e parameters with multiple values. Multiple values are separated by “,” letter

```.../<response from>/search?collection=cams,clms```

##### 2.3.9 OpenSearch search terms
Parameter searchterm can query all the non-standard queryable keywords. Together with parameter solr can also content free text search query.  










