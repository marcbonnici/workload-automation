#  Copyright 2018 ARM Limited
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

import re

from wa import OutputProcessor, Parameter
from wa.framework.exception import ConfigError
from wa.utils.types import list_or_string, numeric


class LogcatRegex(OutputProcessor):

    name = 'logcat-regex'

    description = '''
    Parse logcat for an aribitary set of regexes

    Provide either a single or list of regexes to be matched against the logcat
    output and add metric(s) with the specified "key" and "value" pair.

    '''
    parameters = [
        Parameter('regexes', kind=list_or_string,
                  description="""
                  A regex or list of regexes to match against
                  logcat output of the device. The regexes should contain 2 named
                  groups "key" and "value" where the "key" is an artibary string
                  and the "value" is a numeric value".
                  """),
    ]

    def __init__(self, *args, **kwargs):
        super(LogcatRegex, self).__init__(*args, **kwargs)
        self.compiled_regexes = []

    def validate(self):
        super(LogcatRegex, self).validate()
        for r in self.regexes:
            if '(?P<key>' not in r:
                raise ConfigError('Please ensure you have specified "key" as a named regex group')
            if '(?P<value>' not in r:
                raise ConfigError('Please ensure you have specified "value" as a named regex group')
            try:
                compiled = re.compile(r)
            except re.error as e:
                raise ConfigError('Regex error in "{}": {}'.format(r, e))
            self.compiled_regexes.append(compiled)

    # pylint: disable=unused-argument
    def process_job_output(self, output, target_info, job_output):
        logcat = output.get_artifact('logcat')
        if not logcat:
            return
        filepath = output.get_path(logcat.path)
        with open(filepath) as file:
            for line in file:
                for reg in self.compiled_regexes:
                    match = reg.match(line)
                    if not match or len(match.groups()) != 2:
                        continue
                    value = match.group('value')
                    try:
                        value = numeric(value)
                        output.add_metric(match.group('key'), value)
                    except ValueError:
                        msg = 'Value extracted for "{}": "{}" is not numeric'
                        self.logger.warning(msg.format(match.group('key'), value))
