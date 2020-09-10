from metaflow import FlowSpec, step, S3
from metaflow import Parameter
import json
import nuts_finder  # <--- just to show that the env is working


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
