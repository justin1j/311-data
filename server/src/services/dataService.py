import datetime
import pandas as pd
import sqlalchemy as db
from sqlalchemy.orm import sessionmaker
from .databaseOrm import Ingest as Request


class DataService(object):
    def includeMeta(func):
        def innerFunc(*args, **kwargs):
            dataResponse = func(*args, **kwargs)
            if 'Error' in dataResponse:
                return dataResponse
            # Will represent last time the ingest pipeline ran
            lastPulledTimestamp = datetime.datetime.utcnow()
            withMeta = {'lastPulled': lastPulledTimestamp,
                        'data': dataResponse}
            return withMeta

        return innerFunc

    def __init__(self, config=None, tableName="ingest_staging_table"):
        self.config = config
        self.dbString = None if not self.config  \
            else self.config['Database']['DB_CONNECTION_STRING']

        self.table = tableName
        self.data = None
        self.engine = db.create_engine(self.dbString)
        self.session = sessionmaker(bind=self.engine)()

    def standardFilters(self,
                        startDate=None,
                        endDate=None,
                        ncList=[],
                        requestTypes=[]):
        '''
        Generates filters for dates, ncs, and request types.
        '''

        return [
            Request.createddate > startDate if startDate else True,
            Request.createddate < endDate if endDate else True,
            Request.ncname.in_(ncList) if ncList else True,
            Request.requesttype.in_(requestTypes) if requestTypes else True
        ]

    @includeMeta
    def itemQuery(self, requestNumber):
        '''
        Returns a single request by its requestNumber.
        '''

        if not requestNumber or not isinstance(requestNumber, str):
            return {'Error': 'Missing request number'}

        return self.session \
            .query(Request) \
            .get(requestNumber) \
            ._asdict()

    @includeMeta
    def query(self, queryItems=[], queryFilters=[], limit=None):
        '''
        Returns the specified properties of each request,
        after filtering by queryFilters and applying the limit.
        '''

        if not queryItems or not isinstance(queryItems, list):
            return {'Error': 'Missing query items'}

        selectFields = [getattr(Request, item) for item in queryItems]
        records = self.session \
            .query(*selectFields) \
            .filter(*queryFilters) \
            .limit(limit) \
            .all()

        return [rec._asdict() for rec in records]

    @includeMeta
    def aggregateQuery(self, countFields=[], queryFilters=[]):
        '''
        Returns the counts of distinct values in the specified fields,
        after filtering by queryFilters.
        '''

        if not countFields or not isinstance(countFields, list):
            return {'Error': 'Missing count fields'}

        filteredData = self.query(countFields, queryFilters)
        df = pd.DataFrame(data=filteredData['data'])

        return [{
            'field': field,
            'counts': df.groupby(by=field).size().to_dict()
        } for field in countFields]

    def storedProc(self):
        pass