import json
import boto3
import os


def lambda_handler(event, context):
    body = json.loads(event['body'])
    id = body['id']

    table = boto3.resource('dynamodb').Table(os.environ['TABLE_NAME'])

    response = table.get_item(Key={'id': id})
    chat = response['Item']['chat']

    return {
        'statusCode': 200,
        'body': json.dumps(chat)
    }