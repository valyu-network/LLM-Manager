import json
import boto3
import os


def lambda_handler(event, context):
    body = json.loads(event['body'])
    id = body['id']
    q = body['q']
    a = body['a']

    table = boto3.resource('dynamodb').Table(os.environ['TABLE_NAME'])
    response = table.get_item(Key={'id': id})
    chat = response['Item']['chat']
    chat.append({'q': q, 'a': a})
    table.update_item(Key={'id': id}, UpdateExpression='SET chat = :chat', ExpressionAttributeValues={':chat': chat})
    
    return {
        'statusCode': 200,
        'body': json.dumps('History Appended!')
    }