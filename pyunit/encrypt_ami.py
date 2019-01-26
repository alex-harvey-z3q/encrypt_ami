#!/usr/bin/env python

import unittest
import placebo
import mock
from mock import Mock

import sys
sys.path.insert(0, '.')
from encrypt_ami import AMIEncrypter

import boto3
import os

import time

# Attach the Placebo library. Calls to Boto3 are intercepted and replaced
# with the canned responses found in data_path.

boto3.setup_default_session()
session = boto3.DEFAULT_SESSION
pill = placebo.attach(session, data_path='pyunit/fixtures/encrypt_ami')
pill.playback()

class TestEncryptAMI(unittest.TestCase):

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
    self.args = {
      'source_image_id': 'ami-52293031',
      'kms_key_id': 'alias/mykey',
      'name': 'jenkins',
      'iam_instance_profile': 'MyInstanceProfile',
      'subnet_id': 'subnet-43920e34',
      'os_type': 'linux',
    }

  def tearDown(self):
    pass

  def testEncryptAMI(self):
    ami_encrypter = AMIEncrypter()
    encrypted_ami = ami_encrypter.encrypt('ami-52293031', 'jenkins', 'alias/mykey', 'MyInstanceProfile', 'subnet-43920e34', 'linux')
    self.assertEquals(encrypted_ami, 'ami-2939214a')

def main():
  unittest.main()

if __name__ == "__main__":
  main()
