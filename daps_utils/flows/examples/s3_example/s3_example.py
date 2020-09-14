"""
example_flow
------------

An example Flow for writing to S3. This flow is also used
as a good example for it's interacting with MetaflowTask.
"""

from daps_utils import talk_to_luigi
from metaflow import FlowSpec, step, S3
from metaflow import Parameter
import json


@talk_to_luigi
class S3DemoFlow(FlowSpec):
    filename = Parameter('filename',
                         help='The filename',
                         default='test.json')

    @step
    def start(self):
        with S3(run=self) as s3:
            message = json.dumps({'message': 'hello world!'})
            url = s3.put(self.filename, message)
            print("Message saved at", url)
        self.next(self.end)

    @step
    def end(self):
        with S3(run=self) as s3:
            s3obj = s3.get(self.filename)
            print("Object found at", s3obj.url)
            print("Message:", json.loads(s3obj.text))


if __name__ == '__main__':
    S3DemoFlow()
