#!/usr/bin/env python

import unittest
import placebo
import mock
from mock import Mock

import sys
sys.path.insert(0, '.')
from encrypt_ami import *

import boto3
import os

# Attach the Placebo library. Calls to Boto3 are intercepted and replaced
# with the canned responses found in data_path.

boto3.setup_default_session()
session = boto3.DEFAULT_SESSION
pill = placebo.attach(session, data_path='pyunit/fixtures/encrypt_ami')
pill.playback()

class TestAwsEc2CopyImage(unittest.TestCase):

  def setUp(self):

    # Silence STDOUT everywhere.
    sys.stdout = open(os.devnull, 'w')

    # Stub out time.sleep everywhere.
    def dummy_sleep(seconds):
      pass
    time.sleep = dummy_sleep

    # Set the environment variables and command line args that the script
    # is expected to be called with.

    os.environ['AWS_DEFAULT_REGION'] = 'ap-southeast-2'
    os.environ['AWS_BACKEND_SUBNET_IDS'] = 'subnet-43920e34,subnet-3c82f559'
    os.environ['DATE_TIME'] = '201701011111'
    os.environ['JOB_NAME'] = 'Encrypt_AMI'
    self.args = {
      'description':   '',
      'source_image_id': 'ami-52293031',
      'encrypted':     True,
      'kms_key_id':    '',
      'source_region': 'ap-southeast-2',
      'name':          'jenkins',
      'os':            'linux',
    }

  def tearDown(self):
    pass

  def test_this_account(self):
    self.assertEquals('123456781234', this_account())

  def test_account_of(self):
    acc = account_of('ami-52293031')
    self.assertEquals('625972064986', acc)

  def test_run_instance(self):
    instance_id = run_instance('ami-52293031', 'CIMSAppServerInstanceProfile', 'subnet-43920e34', 'windows')
    self.assertEquals('i-0481ed4a67454b5e7', instance_id)

  @mock.patch('encrypt_ami.wait_for_instance_status')
  def test_stop_instance(self, patched_wait_for_instance_status):
    stop_instance('i-0481ed4a67454b5e7')
    patched_wait_for_instance_status.assert_called_once_with('i-0481ed4a67454b5e7', 'stopped')

  def test_create_image(self):
    unencrypted_ami_id = create_image('i-0481ed4a67454b5e7', 'unencrypted-jenkins-201701011111')
    self.assertEquals('ami-23061e40', unencrypted_ami_id)

  def test_wait_for_image_state(self):
    kwargs = {
      'description':   '',
      'source_image_id': 'ami-52293031',
      'encrypted':     True,
      'source_region': 'ap-southeast-2',
      'name':          'unencrypted-jenkins-201701011111',
      'os':            'linux',
    }
    wait_for_image_state('ami-23061e40', 'available', **kwargs)

  @mock.patch('encrypt_ami.wait_for_instance_status')
  def test_terminate_instance(self, patched_wait_for_instance_status):
    terminate_instance('i-0481ed4a67454b5e7')
    patched_wait_for_instance_status.assert_called_once_with('i-0481ed4a67454b5e7', 'terminated')

  def test_copy_image(self):
    encrypted_ami_id = copy_image('ami-23061e40', 'encrypted-jenkins-201701011111', 'alias/mykey')
    self.assertEquals('ami-2939214a', encrypted_ami_id)

  def test_deregister_image(self):
    response = deregister_image('ami-23061e40')
    self.assertEquals(
      {
        u'ResponseMetadata': {
          u'RetryAttempts': 0,
          u'HTTPStatusCode': 200,
          u'RequestId': u'4a760895-5dd7-4800-87c7-6f2ec3e6641b',
          u'HTTPHeaders': {
            u'transfer-encoding': u'chunked',
            u'content-type': u'text/xml;charset=UTF-8',
            u'vary': u'Accept-Encoding',
            u'date': u'Sun, 13 Aug 2017 06:22:56 GMT',
            u'server': u'AmazonEC2',
          },
        },
      },
      response
    )

def main():
  unittest.main()

if __name__ == "__main__":
  main()
