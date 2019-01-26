#!/usr/bin/env bash
  
usage() {
  echo "Usage: $0 [-h] SOURCE_IMAGE_ID \
TARGET_ACCOUNT[,TARGET_ACCOUNT2...]"
  exit 1
}

[ "$1" == "-h" ] && usage

source_image_id=$1
target_account_list=$2

IFS=',' read -r -a target_accounts <<< "$target_account_list"

snapshot_ids=$(aws ec2 describe-images \
  --image-ids $source_image_id \
  --query \
    'Images[].BlockDeviceMappings[].Ebs[].SnapshotId' \
  --output text)

for account in "${target_accounts[@]}" ; do

  echo "Adding launch permission for \
    $account to image $source_image_id..."

  aws ec2 modify-image-attribute \
    --image-id $source_image_id \
    --launch-permission \
      "Add=[{UserId=$account}]"

  for snapshot_id in $snapshot_ids ; do

    echo "Adding create volume permission \
      for $account to snapshot $snapshot_id..."

    aws ec2 modify-snapshot-attribute \
      --snapshot-id $snapshot_id \
      --attribute createVolumePermission \
      --operation-type add \
      --user-ids $account
  done
done
