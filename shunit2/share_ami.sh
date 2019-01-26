#!/usr/bin/env bash

script_under_test=$(basename $0)

aws() {
  echo "${FUNCNAME[0]} $*" >> commands_log
  case "${FUNCNAME[0]} $*" in
  'aws ec2 describe-images --image-ids ami-0114e9d25da9ed405 --query Images[].BlockDeviceMappings[].Ebs[].SnapshotId --output text')
    echo snap-00cf8cb2074819f44	snap-0f353f0815e57bc30
    ;;
  'aws ec2 modify-image-attribute --image-id ami-0114e9d25da9ed405 --launch-permission Add=[{UserId=111111111111}]') true ;;
  'aws ec2 modify-snapshot-attribute --snapshot-id snap-00cf8cb2074819f44 --attribute createVolumePermission --operation-type add --user-ids 111111111111') true ;;
  'aws ec2 modify-snapshot-attribute --snapshot-id snap-0f353f0815e57bc30 --attribute createVolumePermission --operation-type add --user-ids 111111111111') true ;;
  'aws ec2 modify-image-attribute --image-id ami-0114e9d25da9ed405 --launch-permission Add=[{UserId=222222222222}]') true ;;
  'aws ec2 modify-snapshot-attribute --snapshot-id snap-00cf8cb2074819f44 --attribute createVolumePermission --operation-type add --user-ids 222222222222') true ;;
  'aws ec2 modify-snapshot-attribute --snapshot-id snap-0f353f0815e57bc30 --attribute createVolumePermission --operation-type add --user-ids 222222222222') true ;;
  *)
    echo "No responses for: aws $*"
    ;;
  esac
}

tearDown() {
  rm -f commands_log expected_log
}

testUsage() {
  assertTrue "unexpected output when testing script usage function" ". $script_under_test -h | grep -qi usage"
}

testShareAMI() {
  . $script_under_test 'ami-0114e9d25da9ed405' '111111111111,222222222222' > /dev/null

  cat > expected_log <<EOF
aws ec2 describe-images --image-ids ami-0114e9d25da9ed405 --query Images[].BlockDeviceMappings[].Ebs[].SnapshotId --output text
aws ec2 modify-image-attribute --image-id ami-0114e9d25da9ed405 --launch-permission Add=[{UserId=111111111111}]
aws ec2 modify-snapshot-attribute --snapshot-id snap-00cf8cb2074819f44 --attribute createVolumePermission --operation-type add --user-ids 111111111111
aws ec2 modify-snapshot-attribute --snapshot-id snap-0f353f0815e57bc30 --attribute createVolumePermission --operation-type add --user-ids 111111111111
aws ec2 modify-image-attribute --image-id ami-0114e9d25da9ed405 --launch-permission Add=[{UserId=222222222222}]
aws ec2 modify-snapshot-attribute --snapshot-id snap-00cf8cb2074819f44 --attribute createVolumePermission --operation-type add --user-ids 222222222222
aws ec2 modify-snapshot-attribute --snapshot-id snap-0f353f0815e57bc30 --attribute createVolumePermission --operation-type add --user-ids 222222222222
EOF

  assertEquals "unexpected sequence of commands issued" \
    "" "$(diff -wu expected_log commands_log)"
}

. shunit2
