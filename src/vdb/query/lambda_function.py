import boto3
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection
import os
import json

def get_embedding(name, query):
    lambda_ = boto3.client('lambda')
    model_lambda = os.environ.get('MODEL_LAMBDA')
    response = lambda_.invoke(
        FunctionName=model_lambda,
        InvocationType='RequestResponse',
        Payload=json.dumps({'name': name, 'query': query})
    )
    embedding = json.loads(response['Payload'].read())
    return embedding

def lambda_handler(event, context):
    # Extract params
    body = json.loads(event['body'])
    name = body['name']
    index = body['index']
    query = body['query']

    # Get embedding
    query_embedding = get_embedding(name, query)

    # Set up AOSS connection
    region = os.environ.get('AWS_REGION')
    service = 'aoss'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)
    id = check_collection_status(name)
    url = f'https://{id}.us-east-1.aoss.amazonaws.com'
    aws_vector = OpenSearch(
        hosts=[url],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        http_compress=True,
        connection_class=RequestsHttpConnection
    )

    # Query the vector database
    query = {
        "size": 10,
        "query": {
            "knn": {
                "embedding": {
                    "vector": query_embedding,
                    "k": 10
                }
            }
        }
    }
    response = aws_vector.search(index=index, body=query)

    # Extract results
    results = []
    for hit in response['hits']['hits']:
        metadata = hit['_source']['metadata']
        results.append(metadata)

    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }

def check_collection_status(name):
    opensearch = boto3.client('opensearchserverless', region_name=os.environ.get('AWS_REGION'))
    full_name = 'LLManager-' + name
    response = opensearch.list_collections(
        collectionFilters={'name': full_name, 'status': 'ACTIVE'})
    active_collections = response['collectionSummaries']
    if len(active_collections) > 0:
        return active_collections[0]['id']
    return False