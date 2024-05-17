import os
import boto3
import json

class ModelStatus:
    def __init__(self, name):
        self.sagemaker = boto3.client("sagemaker", region_name=os.environ.get('AWS_REGION'))
        self.iam = boto3.client("iam", region_name=os.environ.get('AWS_REGION'))
        self.name = name

    def endpoint_in_service(self):
        response = self.sagemaker.list_endpoints(NameContains=f'{self.name}-endpoint', StatusEquals='InService')
        return len(response['Endpoints']) > 0

    def check_model_created(self):
        response = self.sagemaker.list_models(NameContains=f'{self.name}-model')
        return len(response['Models']) > 0

    def check_endpoint_config_created(self):
        response = self.sagemaker.list_endpoint_configs(NameContains=f'{self.name}-endpoint-config')
        return len(response['EndpointConfigs']) > 0

    def check_endpoint_created(self):
        response = self.sagemaker.list_endpoints(NameContains=f'{self.name}-endpoint')
        return len(response['Endpoints']) > 0

    def execution_role_arn(self):
        try:
            result = self.iam.get_role(RoleName=f'{self.name}-role')
            return result['Role']['Arn']
        except self.iam.exceptions.NoSuchEntityException:
            return False

def lambda_handler(event, context):
    body = json.loads(event['body'])
    name = body['name']

    status = ModelStatus(name)
    is_up = status.endpoint_in_service()

    return {
        'statusCode': 200,
        'body': json.dumps({
            'is_up': is_up
        })
    }