import json
import os
import boto3
import uuid


def lambda_handler(event, context):
    body = json.loads(event['body'])
    q = body['q']
    a = body['a']

    table = boto3.resource('dynamodb').Table(os.environ['TABLE_NAME'])
    id = str(uuid.uuid4())
    chat = [{'q': q, 'a': a}]
    record = {'id': id, 'chat': chat}
    table.put_item(Item=record)

    return {
        'statusCode': 200,
        'body': json.dumps({
            'id': id
        })
    }