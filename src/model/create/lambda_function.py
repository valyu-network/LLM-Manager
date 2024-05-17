import json
import os
import boto3
from sagemaker import script_uris
from sagemaker import image_uris 
from sagemaker import model_uris
from sagemaker import environment_variables
from sagemaker.jumpstart.notebook_utils import list_jumpstart_models


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


class CreateModel:
    def __init__(self):
        self.sagemaker = boto3.client("sagemaker", region_name=os.environ.get('AWS_REGION'))
        self.iam = boto3.client("iam", region_name=os.environ.get('AWS_REGION'))

    def create(self, name, model, instance_type=None, bucket=None, key=None, env_vars=None, docker_img=None):
        model, instance_type = self._resolve_instance_type(model, instance_type)
        if not model or not instance_type:
            raise Exception("Model not known!")
        if not bucket and not key and not env_vars and not docker_img:
            bucket, key, env_vars, docker_img = self._get_jumpstart_model_data(model, instance_type)
        
        status = ModelStatus(name)
        if not status.execution_role_arn():
            self._create_execution_role()

        if not status.check_model_created():
            self._create_model(name, docker_img, bucket, key, env_vars)

        if not status.check_endpoint_config_created():
            self._create_endpoint_config(name, instance_type)

        if not status.check_endpoint_created():
            self._create_endpoint(name)

    def _resolve_instance_type(self, model_id, instance_type):
        if instance_type:
            return (model_id, instance_type)
        else:
            match model_id:
                case "mistral-7b":
                    return "huggingface-llm-mistral-7b", "ml.g5.2xlarge"
                case "mixtral-8x7b":
                    return "huggingface-llm-mixtral-8x7b", "ml.g5.48xlarge"
                case "llama-2-7b":
                    return "meta-textgeneration-llama-2-7b", "ml.g5.2xlarge"
                case "llama-2-70b":
                    return "meta-textgeneration-llama-2-70b", "ml.g5.48xlarge"
                case _:
                    return None, None

    def _get_jumpstart_model_data(self, model_name, instance_type):
        models = list_jumpstart_models()
        if model_name not in models:
            raise Exception("Model not known!")
        region = os.environ.get('AWS_REGION')
        model_version = "*"
        scope = "inference"

        inference_image_uri = image_uris.retrieve(region=region, framework=None,
                                                model_id=model_name, model_version=model_version,
                                                image_scope=scope, instance_type=instance_type)
        inference_model_uri = model_uris.retrieve(model_id=model_name, model_version=model_version, model_scope=scope)
        env_vars = environment_variables.retrieve_default(region=region, model_id=model_name, model_version="*")

        bucket_name = inference_model_uri.split("/")[2]
        bucket_key = "/".join(inference_model_uri.split("/")[3:])
        docker_image = inference_image_uri

        return bucket_name, bucket_key, env_vars, docker_image

    def _create_execution_role(self):
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "sagemaker.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        self.iam.create_role(
            RoleName=f'LLManager-{self.name}-role',
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Custom SageMaker execution role'
        )
        self.iam.attach_role_policy(
            RoleName=f'LLManager-{self.name}-role',
            PolicyArn='arn:aws:iam::aws:policy/AmazonSageMakerFullAccess'
        )
        self.iam.attach_role_policy(
            RoleName=f'LLManager-{self.name}-role',
            PolicyArn='arn:aws:iam::aws:policy/AmazonS3FullAccess'
        )

    def _create_model(self, name, img, bucket, key, env_vars):
        trys = 0
        while trys < 5:
            try:
                response = self.sagemaker.create_model(
                    ModelName=f'LLManager-{name}-model',
                    PrimaryContainer={
                        'ContainerHostname': f'LLManager-{name}-model',
                        'Image': img,
                        'Mode': 'SingleModel',
                        'Environment': env_vars,
                        'ModelDataSource': {
                            'S3DataSource': {
                                'S3Uri': 's3://' + bucket + '/' + key,
                                'S3DataType': 'S3Prefix',
                                'CompressionType': 'None'
                            }
                        }
                    },
                    ExecutionRoleArn=self._execution_role_arn()
                )
                print("Model Created with ARN", response['ModelArn'])
                return
            except Exception as e:
                trys += 1

    def _create_endpoint_config(self, name, instance_type):
        response = self.sagemaker.create_endpoint_config(
            EndpointConfigName=f'LLManager-{name}-endpoint-config',
            ProductionVariants=[
                {
                    'VariantName': 'dev',
                    'ModelName': f'LLManager-{name}-model',
                    'InitialInstanceCount': 1,
                    'InstanceType': instance_type,
                    "InitialVariantWeight": 1.0
                },
            ],
        )

    def _create_endpoint(self, name):
        response = self.sagemaker.create_endpoint(
            EndpointName=f'LLManager-{name}-endpoint',
            EndpointConfigName=f'LLManager-{name}-endpoint-config',
        )


def lambda_handler(event, context):
    body = json.loads(event['body'])
    name = body['name']
    model = body['model']
    instance_type = body.get('instance_type', None)
    bucket = body.get('bucket', None)
    key = body.get('key', None)
    env_vars = body.get('env_vars', None)
    docker_img = body.get('docker_img', None)

    try:
        cm = CreateModel()
        cm.create(name, model, instance_type, bucket, key, env_vars, docker_img)

        addTimeout(body, name)

        return {
            'statusCode': 200,
            'body': json.dumps('Model Created!')
        }
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps(str(e))
        }


def addTimeout(body, name):
    enableTimeout = body.get('enableTimeout', False)
    threshold = body.get('timeoutGPUThreshold', 0.05)
    timeout = body.get('timeout', 300)
    if enableTimeout:
        tableName = os.environ.get('TABLE_NAME')
        table = boto3.resource('dynamodb').Table(tableName)
        table.put_item(Item={'id': name, 'timeout': timeout, 'threshold': threshold})