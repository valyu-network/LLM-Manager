import os
import boto3
import json


def lambda_handler(event, context):
    body = json.loads(event['body'])
    name = body['name']
    full_name = 'LLManager-' + name
    opensearch = boto3.client('opensearchserverless', region_name=os.environ.get('AWS_REGION'))
    response = opensearch.list_collections(collectionFilters={'name': full_name})
    collections = response['collectionSummaries']
    for collection in collections:
        opensearch.delete_collection(id=collection['id'])
    return {
        'statusCode': 200,
        'body': json.dumps('VDB Deleted!')
    }
