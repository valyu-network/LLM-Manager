import re


def lambda_handler(event, context):
    auth_header = event['authorizationToken']

    if not auth_header:
        return generate_policy('user', 'Deny', event['methodArn'])

    is_authorized = True

    if is_authorized:
        return generate_policy('user', 'Allow', event['methodArn'])
    else:
        return generate_policy('user', 'Deny', event['methodArn'])

def generate_policy(principal_id, effect, resource):
    policy = {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource
                }
            ]
        }
    }
    
    return policy