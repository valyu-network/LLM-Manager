from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection
import os
import json
import boto3

def check_collection_status(name):
    opensearch = boto3.client('opensearchserverless', region_name=os.environ.get('AWS_REGION'))
    full_name = 'LLManager-' + name
    response = opensearch.list_collections(
        collectionFilters={'name': full_name, 'status': 'ACTIVE'})
    active_collections = response['collectionSummaries']
    if len(active_collections) > 0:
        return active_collections[0]['id']
    return False

def lambda_handler(event, context):
    # extract params
    body = json.loads(event['body'])
    name = body['name']
    index = body['index']
    s3_src_bucket = body['s3_src_bucket']
    s3_src_key = body['s3_src_key']

    # pull data from S3
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=s3_src_bucket, Key=s3_src_key)
    data = response['Body'].read().decode('utf-8')
    
    # Extract embeddings and data from S3
    embeddings = data['embeddings']
    metadata = data['metadata']
    
    # Set up AOSS connection
    region = os.environ.get('AWS_REGION')
    service = 'aoss'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)
    id = check_collection_status(name)
    url = f'https://{id}.us-east-1.aoss.amazonaws.com'
    aws_vector = OpenSearch(
        hosts = [url],
        http_auth = awsauth,
        use_ssl = True,
        verify_certs = True,
        http_compress = True,
        connection_class = RequestsHttpConnection
    )

    # Upload embeddings and metadata to OpenSearch
    for embedding, metadata_item in zip(embeddings, metadata):
        doc = {
            'embedding': embedding,
            'metadata': metadata_item
        }
        aws_vector.index(index=index, body=doc)

    return {
        'statusCode': 200,
        'body': json.dumps('Successfully uploaded embeddings and metadata to OpenSearch serverless collection.')
    }
