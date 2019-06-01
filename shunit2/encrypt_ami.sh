#!/usr/bin/env bash

script_under_test=$(basename "$0")

aws() {
  case "${FUNCNAME[0]} $1 $2" in
    'aws ec2 run-instances')
    echo "${FUNCNAME[0]} $1 $2" | cut -c-187 >> commands_log
    echo i-060e9491b4a288669
    return
  esac

  echo "${FUNCNAME[0]} $*" >> commands_log
  case "${FUNCNAME[0]} $*" in
  'aws sts get-caller-identity --query Account --output text')
    count=$(<count1)
    case $count in
      1) echo 111111111111 ;;
      2) echo 222222222222 ;;
    esac
    (( count++ ))
    echo $count > count1
    ;;
  'aws ec2 describe-images --image-id ami-0114e9d25da9ed405 --query Images[].OwnerId --output text') echo 111111111111 ;;
  'aws ec2 copy-image --name encrypted-alex --source-image-id ami-0114e9d25da9ed405 --source-region ap-southeast-2 --encrypted --kms-key-id alias/mykey --query ImageId --output text')
    echo ami-023d5e57238507bdf
    ;;
  'aws ec2 describe-images --image-id ami-023d5e57238507bdf --query Images[].State --output text')
    count=$(<count2)
    case $count in
      [123]) echo pending ;;
      4) echo available ;;
    esac
    (( count++ ))
    echo $count > count2
    ;;
  'aws ec2 describe-instances --instance-ids i-060e9491b4a288669 --query Reservations[].Instances[].State.Name --output text')
    count=$(<count3)
    case $count in
      [12]) echo pending ;;
      3) echo running ;;
      [45]) echo stopping ;;
      6) echo stopped ;; 
      [78]) echo shutting-down ;;
      9) echo terminated ;;
    esac
    (( count++ ))
    echo $count > count3
    ;;
  'aws ec2 describe-instance-status --instance-ids i-060e9491b4a288669 --query InstanceStatuses[].InstanceStatus.Status --output text')
    count=$(<count4)
    case $count in
      [123]) echo initializing ;;
      4) echo ok ;;
    esac
    (( count++ ))
    echo $count > count4
    ;;
  'aws ec2 stop-instances --instance-ids i-060e9491b4a288669')
    cat <<'EOF'
{
    "StoppingInstances": [
        {
            "InstanceId": "i-060e9491b4a288669", 
            "CurrentState": {
                "Code": 64, 
                "Name": "stopping"
            }, 
            "PreviousState": {
                "Code": 16, 
                "Name": "running"
            }
        }
    ]
}
EOF
    ;;
  'aws ec2 create-image --instance-id i-060e9491b4a288669 --name encrypted-alex-unencrypted --query ImageId --output text')
    echo ami-02d59780171ffe88a ;;
  'aws ec2 describe-images --image-id ami-02d59780171ffe88a --query Images[].State --output text')
    count=$(<count5)
    case $count in
      [123]) echo pending ;;
      4) echo available ;;
    esac
    (( count++ ))
    echo $count > count5
    ;;
  'aws ec2 describe-images --image-id ami-02c1d3e42b630babc --query Images[].State --output text')
    count=$(<count6)
    case $count in
      [123]) echo pending ;;
      4) echo available ;;
    esac
    (( count++ ))
    echo $count > count6
    ;;
  'aws ec2 terminate-instances --instance-ids i-060e9491b4a288669')
    cat <<'EOF'
{
    "TerminatingInstances": [
        {
            "InstanceId": "i-060e9491b4a288669", 
            "CurrentState": {
                "Code": 48, 
                "Name": "terminated"
            }, 
            "PreviousState": {
                "Code": 80, 
                "Name": "stopped"
            }
        }
    ]
}
EOF
    ;;
  'aws ec2 copy-image --name encrypted-alex --source-image-id ami-02d59780171ffe88a --source-region ap-southeast-2 --encrypted --kms-key-id alias/mykey --query ImageId --output text')
    echo ami-02c1d3e42b630babc
    ;;
  'aws ec2 deregister-image --image-id ami-02d59780171ffe88a') true ;;
  *)
    echo "No responses for: aws $*"
    exit 1
    ;;
  esac
}

sleep() {
  echo "${FUNCNAME[0]} $*" >> commands_log
}

tearDown() {
  rm -f count* commands_log expected_log
}

testUsage() {
  assertTrue "unexpected output when testing script usage function" ". $script_under_test -h | grep -qi usage"
}

testEncryptSameAccount() {
  for i in {1..2} ; do
    echo 1 > count$i
  done

  . "$script_under_test" 'ami-0114e9d25da9ed405' 'encrypted-alex' 'alias/mykey' 'windows' > /dev/null 2>&1

  cat > expected_log <<EOF
aws sts get-caller-identity --query Account --output text
aws ec2 describe-images --image-id ami-0114e9d25da9ed405 --query Images[].OwnerId --output text
aws ec2 copy-image --name encrypted-alex --source-image-id ami-0114e9d25da9ed405 --source-region ap-southeast-2 --encrypted --kms-key-id alias/mykey --query ImageId --output text
aws ec2 describe-images --image-id ami-023d5e57238507bdf --query Images[].State --output text
sleep 10
aws ec2 describe-images --image-id ami-023d5e57238507bdf --query Images[].State --output text
sleep 10
aws ec2 describe-images --image-id ami-023d5e57238507bdf --query Images[].State --output text
sleep 10
aws ec2 describe-images --image-id ami-023d5e57238507bdf --query Images[].State --output text
EOF

  assertEquals "unexpected sequence of commands issued" \
    "" "$(diff -wu expected_log commands_log)"
}

testEncryptDifferentAccount() {
  for i in {2..6} ; do
    echo 1 > count$i
  done

  . "$script_under_test" 'ami-0114e9d25da9ed405' 'encrypted-alex' 'alias/mykey' 'windows' 'subnet-08fa0f2711688bd28' 'CIMSAppServerInstanceProfile' '[{Key=CostCentre,Value=V_CIMS}]' > /dev/null 2>&1

  run_instances_command_abbreviated='aws ec2 run-instances'
  cat > expected_log <<EOF
aws sts get-caller-identity --query Account --output text
aws ec2 describe-images --image-id ami-0114e9d25da9ed405 --query Images[].OwnerId --output text
$run_instances_command_abbreviated
aws ec2 describe-instances --instance-ids i-060e9491b4a288669 --query Reservations[].Instances[].State.Name --output text
sleep 5
aws ec2 describe-instances --instance-ids i-060e9491b4a288669 --query Reservations[].Instances[].State.Name --output text
sleep 5
aws ec2 describe-instances --instance-ids i-060e9491b4a288669 --query Reservations[].Instances[].State.Name --output text
aws ec2 describe-instance-status --instance-ids i-060e9491b4a288669 --query InstanceStatuses[].InstanceStatus.Status --output text
sleep 5
aws ec2 describe-instance-status --instance-ids i-060e9491b4a288669 --query InstanceStatuses[].InstanceStatus.Status --output text
sleep 5
aws ec2 describe-instance-status --instance-ids i-060e9491b4a288669 --query InstanceStatuses[].InstanceStatus.Status --output text
sleep 5
aws ec2 describe-instance-status --instance-ids i-060e9491b4a288669 --query InstanceStatuses[].InstanceStatus.Status --output text
aws ec2 stop-instances --instance-ids i-060e9491b4a288669
aws ec2 describe-instances --instance-ids i-060e9491b4a288669 --query Reservations[].Instances[].State.Name --output text
sleep 5
aws ec2 describe-instances --instance-ids i-060e9491b4a288669 --query Reservations[].Instances[].State.Name --output text
sleep 5
aws ec2 describe-instances --instance-ids i-060e9491b4a288669 --query Reservations[].Instances[].State.Name --output text
aws ec2 create-image --instance-id i-060e9491b4a288669 --name encrypted-alex-unencrypted --query ImageId --output text
aws ec2 describe-images --image-id ami-02d59780171ffe88a --query Images[].State --output text
sleep 10
aws ec2 describe-images --image-id ami-02d59780171ffe88a --query Images[].State --output text
sleep 10
aws ec2 describe-images --image-id ami-02d59780171ffe88a --query Images[].State --output text
sleep 10
aws ec2 describe-images --image-id ami-02d59780171ffe88a --query Images[].State --output text
aws ec2 terminate-instances --instance-ids i-060e9491b4a288669
aws ec2 describe-instances --instance-ids i-060e9491b4a288669 --query Reservations[].Instances[].State.Name --output text
sleep 5
aws ec2 describe-instances --instance-ids i-060e9491b4a288669 --query Reservations[].Instances[].State.Name --output text
sleep 5
aws ec2 describe-instances --instance-ids i-060e9491b4a288669 --query Reservations[].Instances[].State.Name --output text
aws ec2 copy-image --name encrypted-alex --source-image-id ami-02d59780171ffe88a --source-region ap-southeast-2 --encrypted --kms-key-id alias/mykey --query ImageId --output text
aws ec2 describe-images --image-id ami-02c1d3e42b630babc --query Images[].State --output text
sleep 10
aws ec2 describe-images --image-id ami-02c1d3e42b630babc --query Images[].State --output text
sleep 10
aws ec2 describe-images --image-id ami-02c1d3e42b630babc --query Images[].State --output text
sleep 10
aws ec2 describe-images --image-id ami-02c1d3e42b630babc --query Images[].State --output text
aws ec2 deregister-image --image-id ami-02d59780171ffe88a
EOF

  assertEquals "unexpected sequence of commands issued" \
    "" "$(diff -wu expected_log commands_log)"
}

. shunit2
