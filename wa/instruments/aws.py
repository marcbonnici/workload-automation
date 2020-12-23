#    Copyright 2013-2018 ARM Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


# pylint: disable=W0613,no-member,attribute-defined-outside-init
"""

Some "standard" instruments to collect additional info about workload execution.

.. note:: The run() method of a Workload may perform some "boilerplate" as well as
          the actual execution of the workload (e.g. it may contain UI automation
          needed to start the workload). This "boilerplate" execution will also
          be measured by these instruments. As such, they are not suitable for collected
          precise data about specific operations.
"""
import logging
import json
from json.decoder import JSONDecodeError
from re import template

try:
    import boto3
except ImportError:
    boto3 = None

from wa import Instrument, Parameter, very_fast


logger = logging.getLogger(__name__)

AWS_META_DATA_URL = 'http://169.254.169.254/latest/meta-data'
AWS_METE_DATA_URL_TEMPLATE = 'curl -s -H "X-aws-ec2-metadata-token: {0}" -v {1} 2>/dev/null'
AWS_TOKEN_URL = 'curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" 2>/dev/null'
#wget -qO- http://example.com





class AWSMeta(Instrument):

    name = 'aws_meta'
    description = """
    Extracts AWS instance metadata

    """

    def initialize(self, context):
        self.get_metadata(context)

    def get_metadata(self, context):
        if boto3 and self.target.platform == 'AWSPLATFORM':
            meta_data = self._describe_instance_boto()
        else:
            self.logger.info('Fetching AWS Metadata')
            token = self.target.execute(AWS_TOKEN_URL)
            meta_data_list = self.target.execute(AWS_METE_DATA_URL_TEMPLATE.format(token, AWS_META_DATA_URL))
            meta_data = self._describe_instance_API(meta_data_list, AWS_META_DATA_URL, token)
        context.add_metadata('AWS_Instance', meta_data)

    def _describe_instance_boto(self):
        self.ec2 = boto3.client('ec2')
        self.ec2.describe_instances(InstanceIds=[self.target.platform.instance_id])

    def _describe_instance_API(self, entries, url, token):
        out = {}
        for entry in entries.split('\n'):
            path = str('{}/{}'.format(url, entry.rstrip('/')))
            entry = entry.strip()
            data = self.target.execute(AWS_METE_DATA_URL_TEMPLATE.format(token, path)).strip()

            # Assume 'entry' was actually the end of the tree
            if '404' in data:
                return entry
            # This usually indicates there are more entries to retrieve
            if entry.endswith('/'):
                out[entry[:-1]] = self.get_metadata(data, path, token)
            else:
                try:
                    data = json.loads(data)
                except JSONDecodeError:
                    # The data wasn't a JSON String
                    pass
                out[entry] = data
        return out


