import aws_cdk as core
import aws_cdk.assertions as assertions

from ll_manager.ll_manager_stack import LlManagerStack

# example tests. To run these tests, uncomment this file along with the example
# resource in ll_manager/ll_manager_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = LlManagerStack(app, "ll-manager")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
