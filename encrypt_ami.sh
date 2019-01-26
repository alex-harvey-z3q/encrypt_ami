#!/usr/bin/env bash

usage() {
  echo "Usage: $0 [-h] SOURCE_IMAGE_ID \
IMAGE_NAME \
KMS_KEY_ID \
OS_TYPE \
[SUBNET_ID \
IAM_INSTANCE_PROFILE \
TAGS]"
  exit 1
}

build_user_data() {
  local os_type=$1
  [ "$os_type" != "windows" ] && return
  cat <<'EOF'
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
EOF
}

this_account() {
  aws sts get-caller-identity \
    --query Account --output text
}

account_of() {
  local image_id=$1
  aws ec2 describe-images --image-id $image_id \
    --query 'Images[].OwnerId' --output text
}

copy_image() {
  local image_id=$1
  local name=$2
  local kms_key_id=$3

  local encrypted_image_id

  echo "Creating the AMI: $name"

  set -x
  encrypted_image_id=$(aws ec2 copy-image \
    --name $name \
    --source-image-id $image_id \
    --source-region ap-southeast-2 \
    --encrypted \
    --kms-key-id $kms_key_id \
    --query ImageId \
    --output text)
  set +x

  wait_for_image_state $encrypted_image_id 'available'

  echo $encrypted_image_id > encrypted_image_id
}

create_image() {
  local instance_id=$1
  local name=$2
  local unencrypted_image_id

  echo "Creating the AMI: $name"

  set -x
  unencrypted_image_id=$(aws ec2 create-image --instance-id $instance_id \
    --name $name --query ImageId --output text)
  set +x

  wait_for_image_state $unencrypted_image_id 'available'
  echo $unencrypted_image_id > unencrypted_image_id
}

deregister_image() {
  local image_id=$1
  echo "Deregistering the AMI: $image_id"

  set -x
  aws ec2 deregister-image --image-id $image_id
  set +x
}

wait_for_image_state() {
  local image_id=$1
  local desired_state=$2
  local state

  echo "Waiting for AMI to become $desired_state..."

  while true ; do
    state=$(aws ec2 describe-images --image-id $image_id \
      --query 'Images[].State' --output text)
    [ "$state" == "$desired_state" ] && break
    echo "state: $state"
    sleep 10
  done
}

wait_for_instance_status() {
  local instance_id=$1
  local desired_state=$2
  local desired_status=$3

  local state
  local statu # $status is a built-in.

  echo "Waiting for instance ($instance_id) to become $desired_state..."

  while true ; do
    state=$(aws ec2 describe-instances --instance-ids $instance_id \
      --query 'Reservations[].Instances[].State.Name' --output text)
    [ "$state" == "$desired_state" ] && break
    echo "state: $state"
    sleep 5
  done

  [ -z "$desired_status" ] && return

  echo "Waiting for instance ($instance_id) to become $desired_status..."

  while true ; do
    statu=$(aws ec2 describe-instance-status --instance-ids $instance_id \
      --query 'InstanceStatuses[].InstanceStatus.Status' --output text)
    [ "$statu" == "$desired_status" ] && break
    echo "state: $statu"
    sleep 5
  done
}

run_instance() {
  local image_id=$1
  local iam_instance_profile=$2
  local subnet_id=$3
  local os_type=$4

  local user_data
  local instance_id

  user_data=$(build_user_data $os_type)

  echo "Launching a source AWS instance..."

  instance_id=$(aws ec2 run-instances --image-id $image_id \
    --instance-type 'c4.2xlarge' \
    --subnet-id $subnet_id \
    --iam-instance-profile "Name=$iam_instance_profile" \
    --user-data "$user_data" \
    --tag-specifications "ResourceType=instance,Tags=${tags}" \
    --query 'Instances[].InstanceId' \
    --output text)

  wait_for_instance_status $instance_id 'running' 'ok'

  echo $instance_id > instance_id
}

stop_instance() {
  local instance_id=$1

  echo "Stopping the source AWS instance..."

  aws ec2 stop-instances --instance-ids $instance_id > /dev/null
  wait_for_instance_status $instance_id 'stopped'
}

terminate_instance() {
  local instance_id=$1

  echo "Terminating the source AWS instance..."

  aws ec2 terminate-instances --instance-ids $instance_id > /dev/null
  wait_for_instance_status $instance_id 'terminated'
}

clean_up() {
  rm -f encrypted_image_id instance_id unencrypted_image_id
}

[ "$1" == "-h" ] && usage

source_image_id=$1
image_name=$2
kms_key_id=$3
os_type=$4
subnet_id=$5
iam_instance_profile=$6
tags=$7

if [ "$(this_account)" == "$(account_of $source_image_id)" ] ; then
  copy_image $source_image_id $image_name $kms_key_id
else
  run_instance $source_image_id $iam_instance_profile $subnet_id $os_type
  instance_id=$(<instance_id)
  stop_instance $instance_id
  create_image $instance_id "${image_name}-unencrypted"
  unencrypted_image_id=$(<unencrypted_image_id)
  terminate_instance $instance_id
  copy_image $unencrypted_image_id $image_name $kms_key_id
  deregister_image $unencrypted_image_id
fi

echo "Encrypted AMI ID: $(<encrypted_image_id)"
clean_up
