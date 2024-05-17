import json
import boto3
import os


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
    sagemaker = boto3.client('sagemaker')
    iam = boto3.client('iam')

    status = ModelStatus(name)
    if status.endpoint_in_service():
        sagemaker.delete_endpoint(EndpointName=f'LLManager-{name}-endpoint')
    elif status.check_endpoint_created():
        return {
            'statusCode': 400,
            'body': json.dumps('Please wait for model to create fully before deleting')
        }   
    else:
        return {
            'statusCode': 200,
            'body': json.dumps('Model Does Not Exist!')
        }
    if status.check_endpoint_config_created():
        sagemaker.delete_endpoint_config(EndpointConfigName=f'LLManager-{name}-endpoint-config')
    if status.check_model_created():
        sagemaker.delete_model(ModelName=f'LLManager-{name}-model')
    if status.execution_role_arn():
        iam.detach_role_policy(RoleName=f'LLManager-{name}-role', PolicyArn='arn:aws:iam::aws:policy/AmazonSageMakerFullAccess')    
        iam.detach_role_policy(RoleName=f'LLManager-{name}-role', PolicyArn='arn:aws:iam::aws:policy/AmazonS3FullAccess')
        iam.delete_role(RoleName=f'LLManager-{name}-role')

    return {
        'statusCode': 200,
        'body': json.dumps('Model Deleted!')
    }