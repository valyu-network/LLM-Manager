from datetime import datetime, timedelta, timezone
import json
import boto3
import os

def get_svc_names():
    client = boto3.client('sagemaker')

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ.get('TABLE_NAME'))
    response = table.scan()
    results = response.get('Items', [{}])

    response = client.list_endpoints(
        NameContains='-endpoint',
        StatusEquals='InService'
    )

    endpoints = response.get('Endpoints', [])
    svc_names = [endpoint.get('EndpointName').split('-endpoint')[0] for endpoint in endpoints]
    svc_names = [n.split('LLManager-')[1] for n in svc_names if n.startswith('LLManager-')]
    final = []
    for r in results:
        if r.get('id') in svc_names:
            final.append((r.get('id'), r.get('timeout'), r.get('threshold')))
    return final


def check_inactive(vars):
    svc_name, timeout, threshold = vars
    client = boto3.client('cloudwatch')

    response = client.get_metric_data(
        MetricDataQueries=[
            {
                'Id': 'foo',
                'MetricStat': {
                    'Metric': {
                        'Namespace': '/aws/sagemaker/Endpoints',
                        'MetricName': 'GPUUtilization',
                        'Dimensions': [
                            {
                                'Name': 'EndpointName',
                                'Value': f'LLManager-{svc_name}-endpoint'
                            },
                            {
                                'Name': 'VariantName',
                                'Value': 'dev'
                            }
                        ]
                    },
                    'Period': 60 * 15,
                    'Stat': 'Average', 
                    'Unit': 'Percent'
                },
                'ReturnData': True,
            },
        ],
        StartTime=datetime.now(timezone.utc) - timedelta(minutes=threshold),
        EndTime=datetime.now(timezone.utc),
    )

    inactive = all([v < threshold for v in response.get('MetricDataResults', [{}])[0].get('Values', [])])
    return inactive

def delete_inactive(svc_name, function_name):
    payload = {
        "name": svc_name,
    }
    client = boto3.client('lambda')
    # TODO: Check payload for delete function
    response = client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload),
    )
    print(f"Deleted LLM {svc_name}:", response.json())

def lambda_handler(event, context):
    function_name = os.environ.get('DELETE_FUNCTION_NAME')
    svc_names = get_svc_names()
    for svc_name in svc_names:
        if check_inactive(svc_name):
            delete_inactive(svc_name, function_name)