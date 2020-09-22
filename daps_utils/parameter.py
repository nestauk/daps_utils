import luigi

class SqlAlchemyParameter(luigi.Parameter):
    """
    Parameter whose value is a ``sqlalchemy`` column.
    """
    def serialize(self, x):
        return str(x)
