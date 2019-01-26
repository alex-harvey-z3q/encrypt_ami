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
  if 'AWS_DEFAULT_REGION' not in os.environ:
    raise "Expected to find default region in $AWS_DEFAULT_REGION"

  parser = argparse.ArgumentParser()
  parser.add_argument(
    "--source-image-id",
        action="store", required=True, metavar="SOURCE_AMI_ID", dest="source_image_id",
        help="The ID of the AMI to copy")
  parser.add_argument(
    "--name",
        action="store", required=True, metavar="NAME", dest="image_name",
        help="The name of the new AMI in the destination region")
  parser.add_argument(
    "--kms-key-id",
        action="store", required=True, metavar="KMS_KEY_ID", dest="kms_key_id",
        help="The full ARN of the KMS CMK to use when encrypting the snapshots of an image during a copy operation")
  parser.add_argument(
    "--iam-instance-profile",
        action="store", required=False, metavar="IAM_INSTANCE_PROFILE", dest="iam_instance_profile", default="",
        help="The IAM Instance Profile name e.g. MyInstanceProfile")
  parser.add_argument(
    "--subnet-id",
        action="store", required=False, metavar="SUBNET_ID", dest="subnet_id", default="",
        help="The subnet ID to launch the image in")
  parser.add_argument(
    "--os-type",
        action="store", required=False, metavar="OS_TYPE", dest="os_type", default="linux", choices=["linux", "windows"],
        help="The OS of the source image")
  return parser.parse_args()

class AMIEncrypter():

  def __init__(self):

    if os.environ.get('BOTO_RECORD'):
      import placebo
      boto3.setup_default_session()
      session = boto3.DEFAULT_SESSION
      pill = placebo.attach(session, data_path='.')
      pill.record()

    self.client = boto3.client('ec2')

  def encrypt(self,
      source_image_id, image_name, kms_key_id, iam_instance_profile,
      subnet_id, os_type):

    try:
      if self.this_account() == self.account_of(source_image_id):
        encrypted_image_id = self.copy_image(source_image_id, image_name, kms_key_id)

      else:
        instance_id = self.run_instance(source_image_id, iam_instance_profile, subnet_id, os_type)
        self.stop_instance(instance_id)
        unencrypted_image_id = self.create_image(instance_id, image_name + "-unencrypted")
        self.terminate_instance(instance_id)
        encrypted_image_id = self.copy_image(source_image_id, image_name, kms_key_id)
        self.deregister_image(unencrypted_image_id)

    except KeyboardInterrupt:
      sys.exit("User aborted script!")

  def build_user_data(self, os_type):
    if os_type == 'windows':
      return ""
    else:
      return """
    <powershell>
      $Cmd = Get-WmiObject -Class Win32_OperatingSystem | ForEach-Object -MemberName Caption

      $Get_OS = $Cmd -match '(\d+)'
      if ($Get_OS) {
        $Os_Type = $matches[1]
      }

      Write-Host "The operating system is $Os_Type"

      if ($Os_Type -eq '2012') {
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
        Write-Host "Don't know what to do for OS type $Os_Type"
      }
    </powershell>
    """

  def this_account(self):
    return boto3.client('sts').get_caller_identity().get('Account')

  def account_of(self, image_id):
    response = self.client.describe_images(DryRun=False, ImageIds=[image_id])
    return response['Images'][0]['ImageLocation'].split('/')[0]

  def copy_image(self, image_id, name, kms_key_id):
    print "Creating the AMI: %s" % name

    response = self.client.copy_image(
            Name=name,
            SourceImageId=image_id,
            DryRun=False,
            SourceRegion=os.environ.get('AWS_DEFAULT_REGION'),
            Encrypted=True,
            KmsKeyId=kms_key_id)

    encrypted_image_id = response['ImageId']
    self.wait_for_image_state(encrypted_image_id, 'available')

    return encrypted_image_id

  def create_image(self, instance_id, name):
    print "Creating the AMI: %s" % name

    response = self.client.create_image(
            InstanceId=instance_id,
            Name=name)

    unencrypted_image_id = response['ImageId']
    self.wait_for_image_state(unencrypted_image_id, 'available')

    return unencrypted_image_id

  def deregister_image(self, image_id):
    print "Deregistering the AMI: %s" % image_id
    return self.client.deregister_image(DryRun=False, ImageId=image_id)

  def wait_for_image_state(self, image_id, desired_state, **kwargs):
    print "Waiting for AMI to become %s..." % desired_state

    while True:
      response = self.client.describe_images(DryRun=False, ImageIds=[image_id])
      state = response['Images'][0]['State']

      if state == desired_state:
        break
      else:
        print "state: %s" % state

      time.sleep(10)

  def wait_for_instance_status(self, instance_id, desired_state, desired_status=''):
    print "Waiting for instance (%s) to become %s..." % (instance_id, desired_state)

    while True:
      response = self.client.describe_instances(DryRun=False, InstanceIds=[instance_id])
      state = response['Reservations'][0]['Instances'][0]['State']['Name']
      if state == desired_state:
        break
      print "state: %s" % state
      time.sleep(5)

    if not desired_status:
      return

    print "Waiting for instance (%s) to become %s..." % (instance_id, desired_status)

    while True:
      response = self.client.describe_instance_status(DryRun=False, InstanceIds=[instance_id])
      status = response['InstanceStatuses'][0]['SystemStatus']['Status']
      if status == desired_status:
        break
      print "state: %s" % status
      time.sleep(5)

    return

  def run_instance(self, image_id, iam_instance_profile, subnet_id, os_type):
    user_data = build_user_data(os_type)

    print "Launching a source AWS instance..."

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

    response = self.client.run_instances(ImageId=image_id,
          InstanceType='c4.2xlarge',
          IamInstanceProfile={'Name': iam_instance_profile},
          UserData=user_data,
          SubnetId=subnet_id,
          MinCount=1,
          MaxCount=1)

    instance_id = response['Instances'][0]['InstanceId']
    # create_tags(instance_id, **kwargs)
    self.wait_for_instance_status(instance_id, 'running', 'ok')
    return instance_id

  # def create_tags(instance_id, **kwargs):
  #   self.client.create_tags(
  #           DryRun=False,
  #           Resources=[instance_id],
  #           Tags=[{"Key": "Foo", "Value": "Bar"}])
  #   return

  def stop_instance(self, instance_id):
    print("Stopping the source AWS instance...")
    response = self.client.stop_instances(DryRun=False, InstanceIds=[instance_id])
    self.wait_for_instance_status(instance_id, 'stopped')

  def terminate_instance(self, instance_id):
    print("Terminating the source AWS instance...")
    response = self.client.terminate_instances(DryRun=False, InstanceIds=[instance_id])
    self.wait_for_instance_status(instance_id, 'terminated')

args = get_args()
ami_encrypter = AMIEncrypter()
ami_encrypter.encrypt(
  args.source_image_id,
  args.image_name,
  args.kms_key_id,
  args.iam_instance_profile,
  args.subnet_id,
  args.os_type)
