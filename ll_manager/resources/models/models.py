from aws_cdk import (
    aws_dynamodb as dynamodb, 
    aws_lambda as lambda_, 
    aws_iam as iam, 
    aws_apigateway as apigw,
    aws_events as events,
    aws_events_targets as events_targets,
    Duration,
)
from constructs import Construct

class ModelResources(Construct):
    def __init__(self, scope: Construct, construct_id: str, basic_lambda_policy: iam.PolicyStatement, boto3_layer: lambda_.LayerVersion, 
                 authorizer: apigw.TokenAuthorizer, gateway: apigw.RestApi, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        model_table = self.create_table()
        
        permissive_table_statement = self.create_table_statement(model_table)
        
        model_resource = gateway.root.add_resource("model")

        # TODO: iam and sagemaker perms
        delete_lambda = self.delete_endpoint(basic_lambda_policy, boto3_layer, model_resource, model_table, permissive_table_statement, authorizer)

        # TODO: function invocation perms
        # TODO: Cloudwatch read perms
        # TODO: sagemaker list perms
        self.autodelete_system(basic_lambda_policy, boto3_layer, model_table, permissive_table_statement, delete_lambda)

        # TODO: iam and sagemaker perms, S3 perms?
        self.create_endpoint(basic_lambda_policy, model_resource, model_table, permissive_table_statement, authorizer)

        # TODO: iam and sagemaker perms
        self.query_endpoint(basic_lambda_policy, boto3_layer, model_resource, model_table, permissive_table_statement, authorizer)

        # TODO: iam and sagemaker perms
        self.status_endpoint(basic_lambda_policy, boto3_layer, model_resource, authorizer)

    def create_table_statement(self, model_table):
        permissive_table_statement = iam.PolicyStatement(
                actions=["dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:UpdateItem", "dynamodb:GetItem", "dynamodb:Scan"],
                resources=[model_table.table_arn],
                effect=iam.Effect.ALLOW,
            )
            
        return permissive_table_statement

    def create_table(self):
        model_table = dynamodb.Table(self, "ModelTable", partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING), 
                                   billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST, table_name="modelLifecycleTable")
                                   
        return model_table

    def status_endpoint(self, basic_lambda_policy, boto3_layer, model_resource, authorizer):
        model_status_policy = iam.PolicyDocument(statements=[basic_lambda_policy])
        model_status_role = iam.Role(self, "ModelStatusRole", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                                   inline_policies={"model_status_policy": model_status_policy})
        model_query_lambda = lambda_.Function(self, "ModelStatusLambda", runtime=lambda_.Runtime.PYTHON_3_11, code=lambda_.Code.from_asset("src/model/status"), 
                                            handler="lambda_function.lambda_handler", role=model_status_role, timeout=Duration.seconds(300), layers=[boto3_layer],
                                            memory_size=1024)
        lambda_integration = apigw.LambdaIntegration(model_query_lambda)
        model_resource.add_resource("status").add_method("POST", lambda_integration, authorizer=authorizer)

    def query_endpoint(self, basic_lambda_policy, boto3_layer, model_resource, model_table, permissive_table_statement, authorizer):
        model_query_policy = iam.PolicyDocument(statements=[basic_lambda_policy, permissive_table_statement])
        model_query_role = iam.Role(self, "ModelQueryRole", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                                  inline_policies={"model_query_policy": model_query_policy})
        model_query_lambda = lambda_.Function(self, "ModelQueryLambda", runtime=lambda_.Runtime.PYTHON_3_11, code=lambda_.Code.from_asset("src/model/query"), 
                                            handler="lambda_function.lambda_handler", role=model_query_role, timeout=Duration.seconds(300), layers=[boto3_layer])
        model_table.grant_read_write_data(model_query_lambda)
        lambda_integration = apigw.LambdaIntegration(model_query_lambda)
        model_resource.add_resource("query").add_method("POST", lambda_integration, authorizer=authorizer)

    def delete_endpoint(self, basic_lambda_policy, boto3_layer, model_resource, model_table, permissive_table_statement, authorizer):
        model_delete_policy = iam.PolicyDocument(statements=[basic_lambda_policy, permissive_table_statement])
        model_delete_role = iam.Role(self, "ModelDeleteRole", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                                   inline_policies={"model_delete_policy": model_delete_policy})
        model_delete_lambda = lambda_.Function(self, "ModelDeleteLambda", runtime=lambda_.Runtime.PYTHON_3_11, code=lambda_.Code.from_asset("src/model/delete"), 
                                             handler="lambda_function.lambda_handler", role=model_delete_role, layers=[boto3_layer], timeout=Duration.seconds(300))
        model_table.grant_read_write_data(model_delete_lambda)
        lambda_integration = apigw.LambdaIntegration(model_delete_lambda)
        model_resource.add_resource("delete").add_method("POST", lambda_integration, authorizer=authorizer)
        return model_delete_lambda

    def autodelete_system(self, basic_lambda_policy, boto3_layer, model_table, permissive_table_statement, delete_lambda):
        model_autodelete_lambda_policy = iam.PolicyDocument(statements=[basic_lambda_policy, permissive_table_statement])
        model_autodelete_lambda_role = iam.Role(self, "ModelAutodeleteLambdaRole", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                                              inline_policies={"model_autodelete_lambda_policy": model_autodelete_lambda_policy})
        model_autodelete_lambda = lambda_.Function(self, "ModelAutodeleteLambda", runtime=lambda_.Runtime.PYTHON_3_11, code=lambda_.Code.from_asset("src/model/autodelete"), 
                                                handler="lambda_function.lambda_handler", role=model_autodelete_lambda_role, layers=[boto3_layer], timeout=Duration.seconds(300),
                                                environment={"TABLE_NAME": model_table.table_name, "DELETE_FUNCTION_NAME": delete_lambda.function_name})
        model_table.grant_read_write_data(model_autodelete_lambda)
        
        rule = events.Rule(
            self, "Rule",
            schedule=events.Schedule.rate(Duration.minutes(5))
        )
        rule.add_target(events_targets.LambdaFunction(model_autodelete_lambda))

    def create_endpoint(self, basic_lambda_policy, model_resource, model_table, permissive_table_statement, authorizer):
        sagemaker_statement = iam.PolicyStatement(
            actions=[
                "sagemaker:ListModels",
                "sagemaker:ListEndpoints",
                "sagemaker:ListEndpointConfigs",
                "sagemaker:CreateModel",
                "sagemaker:CreateEndpointConfig",
                "sagemaker:CreateEndpoint"
            ],
            resources=["*"]
        )
        create_roles_statement = iam.PolicyStatement(
            actions=[
                "iam:CreateRole",
                "iam:AttachRolePolicy",
                "iam:GetRole"
            ],
            resources=["arn:aws:iam::*:role/LLManager-*"]
        )
        s3_access_statement = iam.PolicyStatement(
            actions=[
                "s3:Get*",
                "s3:List*",
                "s3:Describe*",
                "s3-object-lambda:Get*",
                "s3-object-lambda:List*"
            ],
            resources=["*"]
        )
        sagemaker_layer = lambda_.LayerVersion(self, "SagemakerLayer", code=lambda_.Code.from_asset("src/layers/sagemaker"),
                                               compatible_runtimes=[lambda_.Runtime.PYTHON_3_11])
        
        model_create_policy = iam.PolicyDocument(statements=[basic_lambda_policy, permissive_table_statement, sagemaker_statement, create_roles_statement, s3_access_statement])
        model_create_role = iam.Role(self, "ModelCreateRole", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                                   inline_policies={"model_create_policy": model_create_policy})
        model_create_lambda = lambda_.Function(self, "ModelCreateLambda", runtime=lambda_.Runtime.PYTHON_3_11, code=lambda_.Code.from_asset("src/model/create"), timeout=Duration.seconds(300),
                                             handler="lambda_function.lambda_handler", role=model_create_role, layers=[sagemaker_layer], environment={"TABLE_NAME": model_table.table_name})
        model_table.grant_read_write_data(model_create_lambda)
        lambda_integration = apigw.LambdaIntegration(model_create_lambda)
        model_resource.add_resource("create").add_method("POST", lambda_integration, authorizer=authorizer)
