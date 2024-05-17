import json
from aws_cdk import (
    aws_dynamodb as dynamodb, 
    aws_lambda as lambda_, 
    aws_iam as iam, 
    aws_apigateway as apigw,
    aws_opensearchserverless as opensearch,
)
from constructs import Construct
import os

class VdbResources(Construct):
    def __init__(self, scope: Construct, construct_id: str, basic_lambda_policy: iam.PolicyStatement, boto3_layer: lambda_.LayerVersion, 
                 authorizer: apigw.TokenAuthorizer, gateway: apigw.RestApi, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vdb_table = self.create_table()
        
        permissive_table_statement = self.create_table_statement(vdb_table)
        
        vdb_resource = gateway.root.add_resource("vdb")

        self.add_endpoint(basic_lambda_policy, boto3_layer, vdb_resource, vdb_table, permissive_table_statement, authorizer)

        self.create_endpoint(basic_lambda_policy, boto3_layer, vdb_resource, vdb_table, permissive_table_statement, authorizer)

        self.delete_endpoint(basic_lambda_policy, boto3_layer, vdb_resource, vdb_table, permissive_table_statement, authorizer)

        self.embed_endpoint(basic_lambda_policy, boto3_layer, vdb_resource, vdb_table, permissive_table_statement, authorizer)

        self.query_endpoint(basic_lambda_policy, boto3_layer, vdb_resource, vdb_table, permissive_table_statement, authorizer)

        self.status_endpoint(basic_lambda_policy, boto3_layer, vdb_resource, authorizer)

        self.add_index_endpoint(basic_lambda_policy, boto3_layer, vdb_resource, authorizer)

    def add_endpoint(self, basic_lambda_policy, boto3_layer, vdb_resource, vdb_table, permissive_table_statement, authorizer):
        vdb_add_lambda_policy = iam.PolicyDocument(statements=[basic_lambda_policy, permissive_table_statement])
        vdb_add_lambda_role = iam.Role(self, "VdbAddLambdaRole", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                                        inline_policies={"vdb_add_lambda_policy": vdb_add_lambda_policy})
        vdb_add_lambda = lambda_.Function(self, "VdbAddLambda", runtime=lambda_.Runtime.PYTHON_3_11, code=lambda_.Code.from_asset("src/vdb/add"), 
                                          handler="lambda_function.lambda_handler", role=vdb_add_lambda_role, layers=[boto3_layer])
        vdb_table.grant_read_write_data(vdb_add_lambda)
        lambda_integration = apigw.LambdaIntegration(vdb_add_lambda)
        vdb_resource.add_resource("add").add_method("POST", lambda_integration, authorizer=authorizer)

    def create_table_statement(self, vdb_table):
        permissive_table_statement = iam.PolicyStatement(
                actions=["dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:UpdateItem", "dynamodb:GetItem", "dynamodb:Scan"],
                resources=[vdb_table.table_arn],
                effect=iam.Effect.ALLOW,
            )
            
        return permissive_table_statement

    def create_table(self):
        vdb_table = dynamodb.Table(self, "VdbTable", partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING), 
                                   billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST, table_name="vdbLifecycleTable")
                                   
        return vdb_table

    def status_endpoint(self, basic_lambda_policy, boto3_layer, vdb_resource, authorizer):
        vdb_status_policy = iam.PolicyDocument(statements=[basic_lambda_policy])
        vdb_status_role = iam.Role(self, "VdbStatusRole", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                                   inline_policies={"vdb_status_policy": vdb_status_policy})
        vdb_query_lambda = lambda_.Function(self, "VdbStatusLambda", runtime=lambda_.Runtime.PYTHON_3_11, code=lambda_.Code.from_asset("src/vdb/status"), 
                                            handler="lambda_function.lambda_handler", role=vdb_status_role, layers=[boto3_layer])
        lambda_integration = apigw.LambdaIntegration(vdb_query_lambda)
        vdb_resource.add_resource("status").add_method("POST", lambda_integration, authorizer=authorizer)

    def query_endpoint(self, basic_lambda_policy, boto3_layer, vdb_resource, vdb_table, permissive_table_statement, authorizer):
        vdb_query_policy = iam.PolicyDocument(statements=[basic_lambda_policy, permissive_table_statement])
        vdb_query_role = iam.Role(self, "VdbQueryRole", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                                  inline_policies={"vdb_query_policy": vdb_query_policy})
        vdb_query_lambda = lambda_.Function(self, "VdbQueryLambda", runtime=lambda_.Runtime.PYTHON_3_11, code=lambda_.Code.from_asset("src/vdb/query"), 
                                            handler="lambda_function.lambda_handler", role=vdb_query_role, layers=[boto3_layer])
        vdb_table.grant_read_write_data(vdb_query_lambda)
        lambda_integration = apigw.LambdaIntegration(vdb_query_lambda)
        vdb_resource.add_resource("query").add_method("POST", lambda_integration, authorizer=authorizer)

    def embed_endpoint(self, basic_lambda_policy, boto3_layer, vdb_resource, vdb_table, permissive_table_statement, authorizer):
        vdb_embed_policy = iam.PolicyDocument(statements=[basic_lambda_policy, permissive_table_statement])
        vdb_embed_role = iam.Role(self, "VdbEmbedRole", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                                  inline_policies={"vdb_embed_policy": vdb_embed_policy})
        vdb_embed_lambda = lambda_.Function(self, "VdbEmbedLambda", runtime=lambda_.Runtime.PYTHON_3_11, code=lambda_.Code.from_asset("src/vdb/embed"), 
                                            handler="lambda_function.lambda_handler", role=vdb_embed_role, layers=[boto3_layer])
        vdb_table.grant_read_write_data(vdb_embed_lambda)
        lambda_integration = apigw.LambdaIntegration(vdb_embed_lambda)
        vdb_resource.add_resource("embed").add_method("POST", lambda_integration, authorizer=authorizer)

    def delete_endpoint(self, basic_lambda_policy, boto3_layer, vdb_resource, vdb_table, permissive_table_statement, authorizer):
        vdb_delete_policy = iam.PolicyDocument(statements=[basic_lambda_policy, permissive_table_statement])
        vdb_delete_role = iam.Role(self, "VdbDeleteRole", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                                   inline_policies={"vdb_delete_policy": vdb_delete_policy})
        vdb_delete_lambda = lambda_.Function(self, "VdbDeleteLambda", runtime=lambda_.Runtime.PYTHON_3_11, code=lambda_.Code.from_asset("src/vdb/delete"), 
                                             handler="lambda_function.lambda_handler", role=vdb_delete_role, layers=[boto3_layer])
        vdb_table.grant_read_write_data(vdb_delete_lambda)
        lambda_integration = apigw.LambdaIntegration(vdb_delete_lambda)
        vdb_resource.add_resource("delete").add_method("POST", lambda_integration, authorizer=authorizer)

    def create_endpoint(self, basic_lambda_policy, boto3_layer, vdb_resource, vdb_table, permissive_table_statement, authorizer):
        vdb_create_policy = iam.PolicyDocument(statements=[basic_lambda_policy, permissive_table_statement])
        vdb_create_role = iam.Role(self, "VdbCreateRole", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                                   inline_policies={"vdb_create_policy": vdb_create_policy})
        vdb_create_lambda = lambda_.Function(self, "VdbCreateLambda", runtime=lambda_.Runtime.PYTHON_3_11, code=lambda_.Code.from_asset("src/vdb/create"), 
                                             handler="lambda_function.lambda_handler", role=vdb_create_role, layers=[boto3_layer])
        vdb_table.grant_read_write_data(vdb_create_lambda)
        lambda_integration = apigw.LambdaIntegration(vdb_create_lambda)
        vdb_resource.add_resource("create").add_method("POST", lambda_integration, authorizer=authorizer)

    def create_opensearch_config(self):
        network_security_policy = [{
                "Rules": [
                {
                    "Resource": [
                    f"collection/fLLManager-*"
                    ],
                    "ResourceType": "collection"
                },
                {
                    "Resource": [
                    f"collection/LLManager-*"
                    ],
                    "ResourceType": "dashboard"
                }
                ],
                "AllowFromPublic": True
            }
        ]
        encryption_security_policy = {
            "Rules": [
                {
                    "ResourceType": "collection",
                    "Resource": [
                        f"collection/LLManager-*"
                    ]
                }
            ],
            "AWSOwnedKey": True
        }
        data_access_policy = [{
            "Rules": [
                {
                    "Resource": [
                    f"collection/LLManager-*"
                    ],
                    "Permission": [
                    "aoss:CreateCollectionItems",
                    "aoss:DeleteCollectionItems",
                    "aoss:UpdateCollectionItems",
                    "aoss:DescribeCollectionItems"
                    ],
                    "ResourceType": "collection"
                },
                {
                    "Resource": [
                    f"index/LLManager-*/*"
                    ],
                    "Permission": [
                    "aoss:CreateIndex",
                    "aoss:DeleteIndex",
                    "aoss:UpdateIndex",
                    "aoss:DescribeIndex",
                    "aoss:ReadDocument",
                    "aoss:WriteDocument"
                    ],
                    "ResourceType": "index"
                }
                ],
            "Principal": [
                os.environ.get('USER_ARN')
            ],
            "Description": "Easy data policy"
        }]

        opensearch.create_security_policy(
            name="LLManager-policy",
            policy=json.dumps(network_security_policy),
            type='network'
        )
        opensearch.create_security_policy(
            name="LLManager-policy",
            policy=json.dumps(encryption_security_policy),
            type='encryption'
        )
        opensearch.create_access_policy(
            name="LLManager-policy",
            policy=json.dumps(data_access_policy)
        )

    def add_index_endpoint(self, basic_lambda_policy, boto3_layer, vdb_resource, authorizer):
        vdb_add_index_policy = iam.PolicyDocument(statements=[basic_lambda_policy])
        vdb_add_index_role = iam.Role(self, "VdbAddIndexRole", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                                      inline_policies={"vdb_add_index_policy": vdb_add_index_policy})
        vdb_add_index_lambda = lambda_.Function(self, "VdbAddIndexLambda", runtime=lambda_.Runtime.PYTHON_3_11, code=lambda_.Code.from_asset("src/vdb/add_index"), 
                                                handler="lambda_function.lambda_handler", role=vdb_add_index_role, layers=[boto3_layer])
        lambda_integration = apigw.LambdaIntegration(vdb_add_index_lambda)
        vdb_resource.add_resource("add_index").add_method("POST", lambda_integration, authorizer=authorizer)
