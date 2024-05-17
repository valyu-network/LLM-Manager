import json
import boto3


def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        name = body['name']
        query = body['query']
        parameters = body.get('parameters', {})
        sagemaker = boto3.client('sagemaker')

        populate_defaults(parameters)

        response = sagemaker.list_endpoints(NameContains=f'LLManager-{name}-endpoint', StatusEquals='InService')
        active =  len(response['Endpoints']) > 0
        if not active:
            return {
                'statusCode': 400,
                'body': json.dumps('LLM not in service')
            }
        else:
            response = sagemaker.invoke_endpoint(
                EndpointName=f'LLManager-{name}-endpoint',
                ContentType='application/json',
                Accept='application/json',
                Body=json.dumps({"inputs": query, "parameters": parameters})
            )
            result = response[0]["generated_text"]
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps(str(e))
        }

def populate_defaults(parameters):
    if 'temprature' not in parameters:
        parameters['temperature'] = 0.1
    if 'top_p' not in parameters:
        parameters['top_p'] = 0.15
    if 'repitition_penalty' not in parameters:
        parameters['repitition_penalty'] = 1.1