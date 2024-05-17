from aws_cdk import (
    aws_dynamodb as dynamodb, 
    aws_lambda as lambda_, 
    aws_iam as iam, 
    aws_apigateway as apigw
)
from constructs import Construct

class HistoryResources(Construct):
    def __init__(self, scope: Construct, construct_id: str, basic_lambda_policy: iam.PolicyStatement, 
                 boto3_layer: lambda_.LayerVersion, authorizer: apigw.TokenAuthorizer, gateway: apigw.RestApi, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        hist_table = self.create_table()
        
        permissive_table_statement, readonly_table_statement = self.create_table_statement(hist_table)

        history_resource = gateway.root.add_resource("history")

        self.get_endpoint(basic_lambda_policy, boto3_layer, history_resource, hist_table, readonly_table_statement, authorizer)

        self.add_new_endpoint(basic_lambda_policy, boto3_layer, history_resource, hist_table, permissive_table_statement, authorizer)

        self.append_endpoint(basic_lambda_policy, boto3_layer, history_resource, hist_table, permissive_table_statement, authorizer)

    def create_table_statement(self, hist_table):
        permissive_table_statement = iam.PolicyStatement(
                actions=["dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:UpdateItem", "dynamodb:GetItem", "dynamodb:Scan"],
                resources=[hist_table.table_arn],
                effect=iam.Effect.ALLOW,
            )
        
        read_only_table_statement = iam.PolicyStatement(
                actions=["dynamodb:GetItem", "dynamodb:Scan"],
                resources=[hist_table.table_arn],
                effect=iam.Effect.ALLOW,
            )
            
        return permissive_table_statement, read_only_table_statement

    def create_table(self):
        hist_table = dynamodb.Table(self, "HistTable", partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING), 
                                   billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST, table_name="chatHistoryTable")
                                   
        return hist_table

    def append_endpoint(self, basic_lambda_policy, boto3_layer, history_resource, hist_table, readonly_table_statement, authorizer):
        history_append_policy = iam.PolicyDocument(statements=[basic_lambda_policy, readonly_table_statement])
        history_append_role = iam.Role(self, "HistoryAppendRole", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                                  inline_policies={"history_append_policy": history_append_policy})
        history_append_lambda = lambda_.Function(self, "HistoryAppendLambda", runtime=lambda_.Runtime.PYTHON_3_11, code=lambda_.Code.from_asset("src/history/append"), 
                                            handler="lambda_function.lambda_handler", role=history_append_role, layers=[boto3_layer])
        history_append_lambda.add_environment("TABLE_NAME", hist_table.table_name)
        hist_table.grant_read_write_data(history_append_lambda)
        lambda_integration = apigw.LambdaIntegration(history_append_lambda)
        history_resource.add_resource("append").add_method("POST", lambda_integration, authorizer=authorizer)

    def add_new_endpoint(self, basic_lambda_policy, boto3_layer, history_resource, hist_table, permissive_table_statement, authorizer):
        history_new_policy = iam.PolicyDocument(statements=[basic_lambda_policy, permissive_table_statement])
        history_new_role = iam.Role(self, "HistoryNewRole", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                                   inline_policies={"history_new_policy": history_new_policy})
        history_new_lambda = lambda_.Function(self, "HistoryNewLambda", runtime=lambda_.Runtime.PYTHON_3_11, code=lambda_.Code.from_asset("src/history/new"), 
                                             handler="lambda_function.lambda_handler", role=history_new_role, layers=[boto3_layer])
        history_new_lambda.add_environment("TABLE_NAME", hist_table.table_name)
        hist_table.grant_read_write_data(history_new_lambda)
        lambda_integration = apigw.LambdaIntegration(history_new_lambda)
        history_resource.add_resource("new").add_method("POST", lambda_integration, authorizer=authorizer)

    def get_endpoint(self, basic_lambda_policy, boto3_layer, history_resource, hist_table, permissive_table_statement, authorizer):
        history_get_policy = iam.PolicyDocument(statements=[basic_lambda_policy, permissive_table_statement])
        history_get_role = iam.Role(self, "HistoryGetRole", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                                   inline_policies={"history_get_policy": history_get_policy})
        history_get_lambda = lambda_.Function(self, "HistoryGetLambda", runtime=lambda_.Runtime.PYTHON_3_11, code=lambda_.Code.from_asset("src/history/get"), 
                                             handler="lambda_function.lambda_handler", role=history_get_role, layers=[boto3_layer])
        history_get_lambda.add_environment("TABLE_NAME", hist_table.table_name)
        hist_table.grant_read_write_data(history_get_lambda)
        lambda_integration = apigw.LambdaIntegration(history_get_lambda)
        history_resource.add_resource("get").add_method("POST", lambda_integration, authorizer=authorizer)

        
