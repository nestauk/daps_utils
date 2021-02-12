from metaflow import Parameter


class DapsFlowMixin:
    production = Parameter('production',
                           help='Run in production mode?',
                           default=False)

    @property
    def test(self):
        return not self.production
