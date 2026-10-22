#!/usr/bin/env bash
set -u
REGION="${AWS_REGION:-us-east-2}"
echo "AWS identity:"; aws sts get-caller-identity --query '{Account:Account,Arn:Arn}'
echo "EC2:"; aws ec2 describe-instances --region "$REGION" --query 'Reservations[].Instances[].{Id:InstanceId,State:State.Name}'
echo "Profiles:"; aws iam list-instance-profiles --query 'InstanceProfiles[].InstanceProfileName'
echo "NAT gateways:"; aws ec2 describe-nat-gateways --region "$REGION" --query 'NatGateways[].{Id:NatGatewayId,State:State}'
echo "EIP:"; aws ec2 describe-addresses --region "$REGION" --query 'Addresses[].AllocationId'
