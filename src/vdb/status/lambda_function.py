import json
import boto3
import os


def lambda_handler(event, context):
    body = json.loads(event['body'])
    name = body['name']
    opensearch = boto3.client('opensearchserverless', region_name=os.environ.get('AWS_REGION'))
    full_name = 'LLManager-' + name
    response = opensearch.list_collections(
        collectionFilters={'name': full_name, 'status': 'ACTIVE'})
    active_collections = response['collectionSummaries']
    if len(active_collections) > 0:
        return {
            'statusCode': 200,
            'body': json.dumps(True)
        }
    return {
        'statusCode': 200,
        'body': json.dumps(False)
    }