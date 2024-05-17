import os
import json
import boto3

def query_model(name, data):
    lambda_ = boto3.client('lambda')
    model_lambda = os.environ.get('MODEL_LAMBDA')
    response = lambda_.invoke(
        FunctionName=model_lambda,
        InvocationType='RequestResponse',
        Payload=json.dumps({'name': name, 'query': data})
    )
    embeddings = json.loads(response['Payload'].read())
    return data, embeddings

def lambda_handler(event, context):
    body = json.loads(event['body'])
    s3_src_bucket = body['s3_src_bucket']
    s3_src_key = body['s3_src_key']
    s3_dest_bucket = body['s3_dest_bucket']
    s3_dest_key = body['s3_dest_key']
    model_name = body['model']

    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=s3_src_bucket, Key=s3_src_key)
    data = response['Body'].read().decode('utf-8')
    pages = data.split('\n')
    embeddings = []
    metadata = []
    for page in pages:
        query, embedding = query_model(model_name, page)
        metadata.append(query)
        embeddings.append(embedding)
    result = {
        'metadata': metadata,
        'embeddings': embeddings
    }
    s3.put_object(Bucket=s3_dest_bucket, Key=s3_dest_key, Body=json.dumps(result))

    return {
        'statusCode': 200,
        'body': json.dumps('VDB Embed!')
    }