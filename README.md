# encrypt_ami

[![Build Status](https://img.shields.io/travis/alexharv074/encrypt_ami.svg)](https://travis-ci.org/alexharv074/encrypt_ami)

## Overview

This repo contains scripts written in both Python and AWS CLI for encrypting an Amazon AMI using either a simple [copy-image](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.copy_image) call, if the source and target accounts are the same; or by booting, stopping and then copying on the stopped AMI, and encrypting, otherwise.

## Using the scripts

### share_ami.sh

The Share AMI script is for sharing an AMI from the source account to one or more destination accounts.

```text
Usage: share_ami.sh [-h] SOURCE_IMAGE_ID TARGET_ACCOUNT[,TARGET_ACCOUNT2...]
```

### encrypt_ami.sh

The Bash version is `encrypt_ami.sh`.

```text
Usage: encrypt_ami.sh [-h] SOURCE_IMAGE_ID IMAGE_NAME KMS_KEY_ID OS_TYPE [SUBNET_ID IAM_INSTANCE_PROFILE TAGS]
```

### encrypt_ami.py

The Python version is `encrypt_ami.py`.

```text
usage: encrypt_ami.py [-h] --source-image-id SOURCE_AMI_ID --name NAME
                      --kms-key-id KMS_KEY_ID
                      [--iam-instance-profile IAM_INSTANCE_PROFILE]
                      [--subnet-id SUBNET_ID] [--os-type OS_TYPE]

optional arguments:
  -h, --help            show this help message and exit
  --source-image-id SOURCE_AMI_ID
                        The ID of the AMI to copy
  --name NAME           The name of the new AMI in the destination region
  --kms-key-id KMS_KEY_ID
                        The full ARN of the KMS CMK to use when encrypting the
                        snapshots of an image during a copy operation
  --iam-instance-profile IAM_INSTANCE_PROFILE
                        The IAM Instance Profile name e.g. MyInstanceProfile
  --subnet-id SUBNET_ID
                        The subnet ID to launch the image in
  --os-type OS_TYPE     The OS of the source image
```

## Running the tests

To run the tests:

```text
Usage:
  make <target>

Targets:
  help        Display this help
  shunit2     Run the shunit2 tests for the Bash code
  pyunit      Run the Python Unittest tests for the Python code
  all         Run everything
  docs        Regenerate the README
```
