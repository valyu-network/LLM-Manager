from aws_cdk import (
    aws_lambda as lambda_,
    Stack,
    aws_apigateway as apigw,
    aws_iam as iam,
)
from constructs import Construct

from ll_manager.resources.history.history import HistoryResources
from ll_manager.resources.models.models import ModelResources
from ll_manager.resources.vdb.vdb import VdbResources

class LlManagerStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        boto3_layer = lambda_.LayerVersion(self, "Boto3Layer", code=lambda_.Code.from_asset("src/layers/boto3"), 
                                           compatible_runtimes=[lambda_.Runtime.PYTHON_3_11])
        
        basic_lambda_statement = iam.PolicyStatement(
                actions=["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                resources=["arn:aws:logs:*:*:*"],
                effect=iam.Effect.ALLOW,
            )

        auth_policy = iam.PolicyDocument(statements=[basic_lambda_statement])
        lambda_role = iam.Role(self, "LambdaRole", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"), 
                               inline_policies={"auth_policy": auth_policy})
        auth_lambda = lambda_.Function(self, "AuthLambda", runtime=lambda_.Runtime.PYTHON_3_11, code=lambda_.Code.from_asset("src/auth"), 
                                       handler="lambda_function.lambda_handler", role=lambda_role, layers=[boto3_layer])
        
        api = apigw.RestApi(self, "LlManagerApi", rest_api_name="LlManager API", deploy_options=apigw.StageOptions(stage_name="dev"))
        authorizer = apigw.TokenAuthorizer(self, "LlManagerAuthorizer", handler=auth_lambda)

        hist = HistoryResources(self, "HistoryResources", basic_lambda_statement, boto3_layer, authorizer, api)
        vdb = VdbResources(self, "VdbResources", basic_lambda_statement, boto3_layer, authorizer, api)
        model = ModelResources(self, "ModelResources", basic_lambda_statement, boto3_layer, authorizer, api)
