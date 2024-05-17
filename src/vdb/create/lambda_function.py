import os
import boto3
import json


def _create_collection(full_name):
    opensearch = boto3.client('opensearchservice', region_name=os.environ.get('AWS_REGION'))
    opensearch.create_collection(
        name=full_name,
        standbyReplicas='DISABLED',
        type='VECTORSEARCH'
    )

def _collection_is_up(full_name):
    opensearch = boto3.client('opensearchserverless', region_name=os.environ.get('AWS_REGION'))
    response = opensearch.list_collections(collectionFilters={'name': full_name})
    collections = response['collectionSummaries']
    return len(collections) > 0



def lambda_handler(event, context):
    body = json.loads(event['body'])
    name = body['name']

    full_name = 'LLManager-' + name
    if not _collection_is_up(full_name):
        _create_collection(full_name, full_name) 

    return {
        'statusCode': 200,
        'body': json.dumps('VDB Create!')
    }
