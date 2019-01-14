# aws_ec2_copy_image

This script is for encrypting an Amazon AMI using either a simple [copy-image](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.copy_image) call, if the source and target accounts are the same; or by booting, stopping and then copying on the stopped AMI, and encrypting, otherwise.
