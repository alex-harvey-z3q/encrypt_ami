#!/usr/bin/env python

import unittest
import placebo
import mock
from mock import Mock

import sys
sys.path.insert(0, './scripts')
from aws_ec2_copy_image import *

import boto3
import os

# Attach the Placebo library. Calls to Boto3 are intercepted and replaced
# with the canned responses found in data_path.

boto3.setup_default_session()
session = boto3.DEFAULT_SESSION
pill = placebo.attach(session, data_path='pyunit/fixtures/aws_ec2_copy_image')
pill.playback()

class TestAwsEc2CopyImage(unittest.TestCase):

  def setUp(self):

    # Silence STDOUT everywhere.
    sys.stdout = open(os.devnull, 'w')

    # Stub out time.sleep everywhere.
    def newsleep(seconds):
      pass
    time.sleep = newsleep

    # Set the environment variables and command line args that the script
    # is expected to be called with.

    os.environ['AWS_DEFAULT_REGION'] = 'ap-southeast-2'
    os.environ['AWS_BACKEND_SUBNET_IDS'] = 'subnet-43920e34,subnet-3c82f559'
    os.environ['DATE_TIME'] = '201701011111'
    os.environ['JOB_NAME'] = 'Encrypt_AMI'
    self.args = {
      'description':   '',
      'source_ami_id': 'ami-52293031',
      'encrypted':     True,
      'kms_key_id':    '',
      'source_region': 'ap-southeast-2',
      'name':          'jenkins',
    }

  def tearDown(self):
    pass

  def test_get_account_id(self):
    self.assertFalse(get_account_id())

  def test_get_ec2_image_account_id(self):
    acc = get_ec2_image_account_id('ami-52293031')
    self.assertEquals('625972064986', acc)

  def test_launch_ec2_instance(self):
    instance_id = launch_ec2_instance(**self.args)
    self.assertEquals('i-0481ed4a67454b5e7', instance_id)

  @mock.patch('aws_ec2_copy_image.get_ec2_instance_status')
  def test_stop_ec2_instance(self, patched_get_ec2_instance_status):
    stop_ec2_instance('i-0481ed4a67454b5e7')
    patched_get_ec2_instance_status.assert_called_once_with('i-0481ed4a67454b5e7', 'stopped')

  def test_create_ec2_image(self):
    unencrypted_ami_id, kwargs = create_ec2_image('i-0481ed4a67454b5e7', **self.args)
    self.assertEquals('ami-23061e40', unencrypted_ami_id)
    self.assertEquals(
      {
        'description':   '',
        'source_ami_id': 'ami-52293031',
        'encrypted':     True,
        'kms_key_id':    '',
        'source_region': 'ap-southeast-2',
        'name':          'unencrypted-jenkins-201701011111'
      },
      kwargs,
    )

  def test_get_ec2_image_status(self):
    kwargs = {
      'description':   '',
      'source_ami_id': 'ami-52293031',
      'encrypted':     True,
      'kms_key_id':    '',
      'source_region': 'ap-southeast-2',
      'name':          'unencrypted-jenkins-201701011111'
    }
    get_ec2_image_status('ami-23061e40', **kwargs)
    self.assertTrue(os.path.exists('Encrypt_AMI_ID.txt'))
    content = open('Encrypt_AMI_ID.txt', 'r').read().rstrip()
    self.assertEquals(content, 'ami-23061e40')
    os.remove('Encrypt_AMI_ID.txt')

  @mock.patch('aws_ec2_copy_image.get_ec2_instance_status')
  def test_terminate_ec2_instance(self, patched_get_ec2_instance_status):
    terminate_ec2_instance('i-0481ed4a67454b5e7')
    patched_get_ec2_instance_status.assert_called_once_with('i-0481ed4a67454b5e7', 'terminated')

  def test_copy_ec2_image(self):
    self.args['source_ami_id'] = 'ami-23061e40'
    encrypted_ami_id, kwargs = copy_ec2_image(**self.args)
    self.assertEquals('ami-2939214a', encrypted_ami_id)
    self.assertEquals(
      {
        'description':   '',
        'source_ami_id': 'ami-23061e40',
        'encrypted':     True,
        'kms_key_id':    '',
        'source_region': 'ap-southeast-2',
        'name':          'encrypted-jenkins-201701011111',
      },
      kwargs,
    )

  def test_deregister_ec2_image(self):
    response = deregister_ec2_image('ami-23061e40')
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
