#!/usr/bin/env python

import argparse
import boto3
import os
import random
import sys
import time
import json
import urllib2

def get_args():
  parser = argparse.ArgumentParser()
  parser.add_argument(
    "--source-region",
        action="store", required=False, metavar="SOURCE_AMI_REGION", dest="source_region", default="ap-southeast-2",
        help="The name of the region that contains the AMI to copy.")
  parser.add_argument(
    "--description",
        action="store", required=False, metavar="DESCRIPTION", dest="description", default="",
        help="A description for the new AMI in the destination region.")
  parser.add_argument(
    "--encrypted",
        required=False, action="store_true",
        help="Specifies whether the destination snapshots of the copied image should be encrypted.")
  parser.add_argument(
    "--kms-key-id",
        action="store", required=False, metavar="KMS_KEY_ID", dest="kms_key_id", default="",
        help="The full ARN of the AWS Key Management Service (AWS KMS) CMK to use when encrypting the snapshots of an image during a copy operation. This parameter is only required if you want to use a non-default CMK; if this parameter is not specified, the default CMK for EBS is used.")
  parser.add_argument(
    "--source-image-id",
        action="store", required=True, metavar="SOURCE_AMI_ID", dest="source_image_id",
        help="The ID of the AMI to copy.")
  parser.add_argument(
    "--name",
        action="store",
        help="The name of the new AMI in the destination region.")
  parser.add_argument(
    "--os",
        action="store", required=False, metavar="OS", dest="os", default="linux", choices=["linux", "windows"],
        help="The OS of the source image.")
  return parser.parse_args()

def boto3_client_ec2():
  return boto3.client('ec2')

def user_data_script():
  return """
  <powershell>
    # Check for the Version of Operating System
    $Cmd = Get-WmiObject -Class Win32_OperatingSystem | ForEach-Object -MemberName Caption
    $Get_OS = $Cmd -match '(\d+)'

    # Query and get the version number of the OS
    if ($Get_Os) {
      $Os_Type = $matches[1]
    }

    if ($Os_Type -eq '2012') {
      Write-Host "The operating system is $Os_Type"
      # Configuring the Launch Setting for win2k12
      $EC2SettingsFile = "C:\\Program Files\\Amazon\\Ec2ConfigService\\Settings\\Config.xml"
      $xml = [xml](get-content $EC2SettingsFile)
      $xmlElement = $xml.get_DocumentElement()
      $xmlElementToModify = $xmlElement.Plugins
      $enableElements = "Ec2SetPassword", `
        "Ec2SetComputerName", `
        "Ec2HandleUserData", `
        "Ec2DynamicBootVolumeSize"
      $xmlElementToModify.Plugin | Where-Object {$enableElements -contains $_.name} | Foreach-Object {$_.State="Enabled"}
      $xml.Save($EC2SettingsFile)

      # Sysprep Configuration setting for win2k12
      $EC2SettingsFile = "C:\\Program Files\\Amazon\\Ec2ConfigService\\Settings\\BundleConfig.xml"
      $xml = [xml](get-content $EC2SettingsFile)
      $xmlElement = $xml.get_DocumentElement()
      foreach ($element in $xmlElement.Property) {
        if ($element.Name -eq "AutoSysprep") {
          $element.Value = "Yes"
        }
      }
      $xml.Save($EC2SettingsFile)

    } elseif ($Os_Type -eq '2016') {
      Write-Host "The operating system is $Os_Type"
      # Configuring the Launch setting to enable the initialization for windows server 2016
      # Changes are made to LaunchConfig.json file
      $LaunchConfigFile = "C:\\ProgramData\\Amazon\\EC2-Windows\\Launch\\Config\\LaunchConfig.json"
      $jsoncontent = Get-Content $LaunchConfigFile | ConvertFrom-Json
      $jsoncontent.SetComputerName = 'true'
      $jsoncontent | ConvertTo-Json  | set-content $LaunchConfigFile

      # This script schedules the instance to initialize during the next boot.
      C:\ProgramData\Amazon\EC2-Windows\Launch\Scripts\InitializeInstance.ps1 -Schedule

      # The EC2Launch service runs Sysprep, a Microsoft tool that enables creation of customized Windows AMI that can be reused
      C:\ProgramData\Amazon\EC2-Windows\Launch\Scripts\SysprepInstance.ps1

    } else {
      echo "No Operating System Found"
    }
  </powershell>
  """

def get_ec2_instance_status(instance_id, status):
  client = boto3_client_ec2()
  if status == 'running':
    print("Waiting for instance (%s) to become ready..." % instance_id)
    while True:
      response = client.describe_instances(DryRun=False, InstanceIds=[instance_id])
      try:
        if response['Reservations'][0]['Instances'][0]['State']['Name'] == status:
          break
        time.sleep(1)
      except:
        pass
    print("Waiting for instance (%s) to become healthy..." % instance_id)
    while True:
      response = client.describe_instance_status(DryRun=False, InstanceIds=[instance_id])
      try:
        if response['InstanceStatuses'][0]['SystemStatus']['Status'] == response['InstanceStatuses'][0]['InstanceStatus']['Status'] == 'ok':
          break
        time.sleep(1)
      except:
        pass
    print("Instance up and running!!")
    return
  elif status == 'stopped':
    print("Waiting for instance (%s) to stop..." % instance_id)
    while True:
      response = client.describe_instances(DryRun=False, InstanceIds=[instance_id])
      try:
        if response['Reservations'][0]['Instances'][0]['State']['Name'] == status:
          break
        time.sleep(1)
      except:
        pass
    return
  elif status == 'terminated':
    print("Waiting for instance (%s) to terminate..." % instance_id)
    while True:
      response = client.describe_instances(DryRun=False, InstanceIds=[instance_id])
      try:
        if response['Reservations'][0]['Instances'][0]['State']['Name'] == status:
          break
        time.sleep(1)
      except:
        pass
    return

def this_account():
  return boto3.client('sts').get_caller_identity().get('Account')

def account_of(image_id):
  client = boto3_client_ec2()
  response = client.describe_images(DryRun=False, ImageIds=[image_id])
  return response['Images'][0]['ImageLocation'].split('/')[0]

def copy_image(image_id, name, kms_key_id):
  client = boto3_client_ec2()

  print "Creating the AMI: %s" % name

  response = client.copy_image(
          Name=name,
          SourceImageId=image_id,
          DryRun=False,
          SourceRegion='ap-southeast-2',
          Encrypted=True,
          KmsKeyId=kms_key_id)

  encrypted_image_id = response['ImageId']
  wait_for_image_state(encrypted_image_id, 'available')

  return encrypted_image_id

def wait_for_image_state(image_id, desired_state, **kwargs):
  client = boto3_client_ec2()

  print "Waiting for AMI to become %s..." % desired_state

  while True:
    response = client.describe_images(DryRun=False, ImageIds=[image_id])
    state = response['Images'][0]['State']

    if state == desired_state:
      break
    else:
      print "state: %s" % state

    time.sleep(10)

def terminate_instance(instance_id):
  client = boto3_client_ec2()
  print("Terminating the source AWS instance...")
  response = client.terminate_instances(DryRun=False, InstanceIds=[instance_id])
  get_ec2_instance_status(instance_id, 'terminated')

def deregister_image(ami_id):
  client = boto3_client_ec2()
  print("Deregistering the AMI: %s" %ami_id)
  return client.deregister_image(DryRun=False, ImageId=ami_id)

def run_instance(image_id, iam_instance_profile, subnet_id, os_type):
  client = boto3_client_ec2()

  print "Launching a source AWS instance..."

  # FIXME.
  if os_type == "windows":
    user_data = str(user_data_script())
  else:
    user_data = ""

  # FIXME. Tags missing. It looks something like:
  #
  #   TagSpecifications=[
  #     {
  #       'ResourceType': 'instance'
  #       'Tags': [
  #         {
  #           'Key': 'string',
  #           'Value': 'string'
  #         },
  #       ]
  #     },
  #   ]
  #

  response = client.run_instances(ImageId=image_id,
        InstanceType='c4.2xlarge',
        IamInstanceProfile={'Name': iam_instance_profile},
        UserData=user_data,
        SubnetId=subnet_id,
        MinCount=1,
        MaxCount=1)

  instance_id = response['Instances'][0]['InstanceId']
  # create_tags(instance_id, **kwargs)
  get_ec2_instance_status(instance_id, 'running')
  return instance_id

def create_tags(instance_id, **kwargs):
  client = boto3_client_ec2()
  client.create_tags(
          DryRun=False,
          Resources=[instance_id],
          Tags=[{"Key": "Foo", "Value": "Bar"}])
  return

def stop_instance(instance_id):
  client = boto3_client_ec2()
  print("Stopping the source AWS instance...")
  response = client.stop_instances(DryRun=False, InstanceIds=[instance_id])
  get_ec2_instance_status(instance_id, 'stopped')

def create_image(instance_id, name):
  client = boto3_client_ec2()

  print "Creating the AMI: %s" % name

  response = client.create_image(
          InstanceId=instance_id,
          Name=name)

  unencrypted_image_id = response['ImageId']
  wait_for_image_state(unencrypted_image_id, 'available')

  return unencrypted_image_id

def main():
  if os.environ.get('BOTO_RECORD'):
    import placebo
    boto3.setup_default_session()
    session = boto3.DEFAULT_SESSION
    pill = placebo.attach(session, data_path='.')
    pill.record()

  args = get_args()
  try:
    if this_account() == account_of(args.source_image_id):
      encrypted_image_id = \
        copy_image(args.source_image_id, args.image_name, args.kms_key_id)
    else:
      instance_id = run_instance(args.source_image_id, args.iam_instance_profile,
        args.subnet_id, args.os_type)
      stop_instance(instance_id)
      unencrypted_image_id = \
        create_image(args.instance_id, args.image_name + "-unencrypted")
      terminate_instance(instance_id)
      encrypted_image_id = \
        copy_image(args.source_image_id, args.image_name, args.kms_key_id)
      deregister_image(unencrypted_image_id)
  except KeyboardInterrupt:
    sys.exit("User aborted script!")

if __name__ == '__main__':
  main()
