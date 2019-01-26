#!/usr/bin/env python

import unittest
import placebo

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

    os.environ['AWS_DEFAULT_REGION'] = 'ap-southeast-2'

  def tearDown(self):
    pass

  def testEncryptAMIDifferentAccount(self):
    ami_encrypter = AMIEncrypter()
    encrypted_ami = ami_encrypter.encrypt('ami-52293031', 'jenkins', 'alias/mykey', 'MyInstanceProfile', 'subnet-43920e34', 'linux')
    self.assertEquals(encrypted_ami, 'ami-2939214a')

def main():
  unittest.main()

if __name__ == "__main__":
  main()
