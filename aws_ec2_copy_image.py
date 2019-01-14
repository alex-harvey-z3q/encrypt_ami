#!/usr/bin/env python

import argparse
import boto3
import os
import random
import sys
import time

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
        action="store", required=True, metavar="SOURCE_AMI_ID", dest="source_ami_id",
        help="The ID of the AMI to copy.")
  parser.add_argument(
    "--name",
        action="store",
        help="The name of the new AMI in the destination region.")
  return parser.parse_args()

def copy_ec2_image(**kwargs):
  client = get_ec2_client()
  if os.environ.get('DATE_TIME'):
    kwargs['name'] += "-" + os.environ['DATE_TIME']
  if kwargs['encrypted']:
    kwargs['name'] = "encrypted-" + kwargs['name']
  sys.stdout.write("Creating the AMI: %s\n" %kwargs['name'])
  sys.stdout.flush()
  response = client.copy_image(DryRun=False, SourceRegion=kwargs['source_region'], SourceImageId=kwargs['source_ami_id'], Name=kwargs['name'], Description=kwargs['description'], Encrypted=kwargs['encrypted'], KmsKeyId=kwargs['kms_key_id'])
  sys.stdout.write("AMI: %s\n" %response['ImageId'])
  sys.stdout.flush()
  return response['ImageId'], kwargs

def create_ec2_image(instance_id, **kwargs):
  client = get_ec2_client()
  if os.environ.get('DATE_TIME'):
    kwargs['name'] += "-" + os.environ['DATE_TIME']
  kwargs['name'] = "unencrypted-" + kwargs['name']
  sys.stdout.write("Creating the AMI: %s\n" %kwargs['name'])
  sys.stdout.flush()
  response = client.create_image(DryRun=False, InstanceId = instance_id, Name=kwargs['name'])
  return response['ImageId'], kwargs

def create_ec2_tags(instance_id, **kwargs):
  client = get_ec2_client()
  client.create_tags(DryRun=False, Resources=[ instance_id ], Tags=[ { 'Key': 'Name', 'Value': 'encrypt-'+kwargs['name']+'-build' } ])
  client.create_tags(DryRun=False, Resources=[ instance_id ], Tags=[ { 'Key': 'CC', 'Value': 'AP074' } ])
  client.create_tags(DryRun=False, Resources=[ instance_id ], Tags=[ { 'Key': 'StopHour', 'Value': 'DoNotStop' } ])
  return

def deregister_ec2_image(ami_id):
  client = get_ec2_client()
  sys.stdout.write("Deregistering the AMI: %s\n" %ami_id)
  sys.stdout.flush()
  return client.deregister_image(DryRun=False, ImageId=ami_id)

def get_account_id():
  try:
    # We're running in an ec2 instance, get the account id from the
    # instance profile ARN
    return json.loads(urllib2.urlopen('http://169.254.169.254/latest/meta-data/iam/info/', None, 1).read())['InstanceProfileArn'].split(':')[4]
  except:
    try:
      # We're not on an ec2 instance but have api keys, get the account
      # id from the user ARN
      return boto3.client('iam').get_user()['User']['Arn'].split(':')[4]
    except:
      return False

def get_ec2_client():
  return boto3.client('ec2')

def get_ec2_image_account_id(ami_id):
  client = get_ec2_client()
  response = client.describe_images(DryRun=False, ImageIds=[ami_id])
  return response['Images'][0]['ImageLocation'].split('/')[0]

def get_ec2_image_status(ami_id, **kwargs):
  client = get_ec2_client()
  sys.stdout.write("Waiting for AMI to become ready...\n")
  sys.stdout.flush()
  while True:
    response = client.describe_images(DryRun=False, ImageIds=[ami_id])
    if response['Images'][0]['State'] == 'available':
      sys.stdout.write("AMI successfully created: %s\n" %ami_id)
      sys.stdout.flush()
      if os.environ.get('JOB_NAME'):
        filename = os.environ['JOB_NAME'] + "_ID.txt"
      else:
        filename = kwargs['name'].title() + "_AMI_ID.txt"
      fd = open(filename, 'w')
      fd.write(ami_id + "\n")
      fd.close()
      return 0
    sys.stdout.write("state: %s\n" %response['Images'][0]['State'])
    sys.stdout.flush()
    time.sleep(10)

def get_ec2_instance_status(instance_id, status):
  client = get_ec2_client()
  if status == 'running':
    sys.stdout.write("Waiting for instance (%s) to become ready...\n" %instance_id)
    sys.stdout.flush()
    while True:
      response = client.describe_instances(DryRun=False, InstanceIds=[ instance_id ])
      try:
        if response['Reservations'][0]['Instances'][0]['State']['Name'] == status:
          break
        time.sleep(1)
      except:
        pass
    sys.stdout.write("Waiting for instance (%s) to become healthy...\n" %instance_id)
    sys.stdout.flush()
    while True:
      response = client.describe_instance_status(DryRun=False, InstanceIds=[ instance_id ])
      try:
        if response['InstanceStatuses'][0]['SystemStatus']['Status'] == response['InstanceStatuses'][0]['InstanceStatus']['Status'] == 'ok':
          break
        time.sleep(1)
      except:
        pass
    sys.stdout.write("Instance up and running!!\n")
    sys.stdout.flush()
    return
  elif status == 'stopped':
    sys.stdout.write("Waiting for instance (%s) to stop...\n" %instance_id)
    sys.stdout.flush()
    while True:
      response = client.describe_instances(DryRun=False, InstanceIds=[ instance_id ])
      try:
        if response['Reservations'][0]['Instances'][0]['State']['Name'] == status:
          break
        time.sleep(1)
      except:
        pass
    return
  elif status == 'terminated':
    sys.stdout.write("Waiting for instance (%s) to terminate...\n" %instance_id)
    sys.stdout.flush()
    while True:
      response = client.describe_instances(DryRun=False, InstanceIds=[ instance_id ])
      try:
        if response['Reservations'][0]['Instances'][0]['State']['Name'] == status:
          break
        time.sleep(1)
      except:
        pass
    return

def get_ec2_subnet_ids(tag_name):
  client = get_ec2_client()
  response = client.describe_subnets(DryRun=False, Filters=[ { 'Name': 'tag:Name', 'Values': [ tag_name ] } ])
  return [subnet['SubnetId'] for subnet in response['Subnets']]

def launch_ec2_instance(**kwargs):
  client = get_ec2_client()
  sys.stdout.write("Launching a source AWS instance...\n")
  sys.stdout.flush()

  if os.environ.get('AWS_BACKEND_SUBNET_IDS'):
    subnet_id = random.choice(os.environ.get('AWS_BACKEND_SUBNET_IDS').split(','))
  else:
    subnet_id = random.choice(get_ec2_subnet_ids('*-BackEnd-*'))
  if kwargs['name'].startswith('cloud2-win2k'):

    # FIXME. This really belongs in its own function.
    user_data_script = """ <powershell>
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
    </powershell> """

    response = client.run_instances(DryRun=False, ImageId=kwargs['source_ami_id'], InstanceType='c4.2xlarge', MinCount=1, MaxCount=1, SubnetId=subnet_id, UserData=user_data_script)
  else:
    response = client.run_instances(DryRun=False, ImageId=kwargs['source_ami_id'], InstanceType='c4.2xlarge', MinCount=1, MaxCount=1, SubnetId=subnet_id)
  instance_id = response['Instances'][0]['InstanceId']
  sys.stdout.write("Instance ID: %s\n" %instance_id)
  create_ec2_tags(instance_id, **kwargs)
  get_ec2_instance_status(instance_id, 'running')
  return instance_id

def stop_ec2_instance(instance_id):
  client = get_ec2_client()
  sys.stdout.write("Stopping the source AWS instance...\n")
  sys.stdout.flush()
  response = client.stop_instances(DryRun=False, InstanceIds=[ instance_id ])
  get_ec2_instance_status(instance_id, 'stopped')

def terminate_ec2_instance(instance_id):
  client = get_ec2_client()
  sys.stdout.write("Terminating the source AWS instance...\n")
  sys.stdout.flush()
  response = client.terminate_instances(DryRun=False, InstanceIds=[ instance_id ])
  get_ec2_instance_status(instance_id, 'terminated')

def main():
  if os.environ.get('BOTO_RECORD'):
    import placebo
    boto3.setup_default_session()
    session = boto3.DEFAULT_SESSION
    pill = placebo.attach(session, data_path='.')
    pill.record()

  args = get_args()
  try:
    if get_account_id() == get_ec2_image_account_id(vars(args)['source_ami_id']):
      ami_id, kwargs = copy_ec2_image(**vars(args))
      get_ec2_image_status(ami_id, **kwargs)
    else:
      instance_id = launch_ec2_instance(**vars(args))
      stop_ec2_instance(instance_id)
      unencrypted_ami_id, kwargs = create_ec2_image(instance_id, **vars(args))
      get_ec2_image_status(unencrypted_ami_id, **kwargs)
      terminate_ec2_instance(instance_id)
      vars(args)['source_ami_id'] = unencrypted_ami_id 
      encrypted_ami_id, kwargs = copy_ec2_image(**vars(args))
      get_ec2_image_status(encrypted_ami_id, **kwargs)
      deregister_ec2_image(unencrypted_ami_id)
  except KeyboardInterrupt:
    sys.exit("User aborted script!")

if __name__ == '__main__':
  main()
