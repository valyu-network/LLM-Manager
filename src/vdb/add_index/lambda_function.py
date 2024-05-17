import json
import boto3
import os
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

def check_collection_status(name):
    opensearch = boto3.client('opensearchserverless', region_name=os.environ.get('AWS_REGION'))
    full_name = 'LLManager-' + name
    response = opensearch.list_collections(
        collectionFilters={'name': full_name, 'status': 'ACTIVE'})
    active_collections = response['collectionSummaries']
    if len(active_collections) > 0:
        return active_collections[0]['id']
    return False

def _add_index(index_body, name):
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

    aws_vector.indices.create(name, body=index_body)

def run_index(name, dimension, index_body):
    if name and dimension:
        if not check_collection_status(name):
            return {
                'statusCode': 400,
                'body': json.dumps('Collection not found')
            }

        index_body = {
            'settings': {
                "index.knn": True
            },
            "mappings": {
                "properties": {
                name: {
                    "type": "knn_vector",
                    "dimension": dimension,
                    "method": {
                    "engine": "faiss",
                    "name": "hnsw",
                    "space_type": "l2"
                    }
                }
                }
            }
        }
        _add_index(index_body, name)
        return {
            'statusCode': 200,
            'body': json.dumps('VDB Index Created!')
        }
    elif index_body:
        if not check_collection_status(name):
            return {
                'statusCode': 400,
                'body': json.dumps('Collection not found')
            }
        _add_index(index_body, name)
        return {
            'statusCode': 200,
            'body': json.dumps('VDB Index Created!')
        }
    else:
        return {
            'statusCode': 400,
            'body': json.dumps('Missing required fields')
        }

def lambda_handler(event, context):
    body = json.loads(event['body'])
    name = body.get('name', None)
    dimension = body.get('dim', None)
    index_body = body.get('idx_body', None)
    try:
        return run_index(name, dimension, index_body)
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps(str(e))
        }
