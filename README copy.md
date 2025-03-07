## Prerequisites
This section talks about things that are needed to run this program

### Models
In Azure we need that a embedding model (text-embedding-ada-002) and a large language model (ChatGPT 4o) are deployed. And also that a AI Foundry hub is deployed in Azure environment.

### Other
 - AI Search Resource is deployed
 - Blob Storage container is created

 ### environmental variables
 Here is a list of environmental variables that need to be set in order for the program to run
 - RESOURCE_URI - AI Foundry resource hub URI
 - AZURE_API_KEY - AI search apikey
 - OAI_API_KEY - OPEN AI api key that is found in AI Foundry
 - CONNECTION_STR - connection string to the blob storage
 - SERVICE_NAME - name of the ai search service
 - MODEL_NAME - name of the deployed embeded model 
 - BLOB_CONTAINER_NAME - Blob storage container name
 - INDEXER_NAME - name of the indexer that is called upon
 - DEPLOYMENT_ID - id of the embed model

change the example.env file to .env

## Creating other necessary assets
NB! The sequence matters here. Creation sequence should be index, dataasource, skillset, indexer
Firstly install necessary libraries
```sh
pip install -r requierments.txt
```

### Creating index
To create an index firstly make sure that the INDEX_NAME variable is set and then on the commandline run:

```sh
python create_index.py
```

### Creating datasource
To create an datasource firstly make sure that the DATASOURCE_NAME variable is set and then on the commandline run:

```sh
python create_datasource.py
```

### Creating skillset
To create an skillset firstly make sure that the SKILLSET_NAME variable is set and then on the commandline run:

```sh
python create_skillset.py
```

### Creating indexer
To create an index firstly make sure that the INDEXER_NAME variable is set and then on the commandline run:

```sh
python create_indexer.py
```
## Running docker

Firstly run build command.
```sh
docker build -t rit-project .
```

Then run the run command
```sh
docker run --rm rit-project
```

## TODOs
 - Deletion of documents
 - Code Refactor
