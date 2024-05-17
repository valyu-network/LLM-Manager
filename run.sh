#!/bin/bash
if [ ! -f .env ]; then
    echo "Error: .env file not found"
    exit 1
fi

source .env

if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ] || [ -z "$AWS_REGION" ]; then
    echo "Error: Required variables not set in .env file"
    exit 1
fi

echo "Configuring AWS credentials..."
aws configure set aws_access_key_id $AWS_ACCESS_KEY_ID
aws configure set aws_secret_access_key $AWS_SECRET_ACCESS_KEY
aws configure set region $AWS_REGION

echo "Installing layers..."
cd src/layers/boto3
pip install -r requirements.txt -t python/lib/python3.12/site-packages/
cd ../sagemaker
pip  install -r requirements.txt -t python/lib/python3.12/site-packages/
cd ../../..

echo "Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "Installing AWS CDK..."
npm install -g aws-cdk

echo "Deploying with CDK..."
cdk deploy --all --require-approval never
