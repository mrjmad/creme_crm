# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2016 Hybird
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
################################################################################

from __future__ import print_function

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, connections
from django.test.utils import CaptureQueriesContext as DjangoCaptureQueriesContext
from django.utils.decorators import ContextDecorator


class CaptureQueriesContext(DjangoCaptureQueriesContext):
    def __init__(self, connection=None):
        super(CaptureQueriesContext, self).__init__(connection if connection is not None else
                                                    connections[DEFAULT_DB_ALIAS]
                                                   )
        self._captured_sql = None

    @property
    def captured_sql(self):
        if self._captured_sql is None:
            db_engine = settings.DATABASES['default']['ENGINE']

            if db_engine == 'django.db.backends.sqlite3':
                prefix_len = len("QUERY = u'")
                query_improver = lambda q: q[prefix_len:]
            else:
                query_improver = lambda q: q

            self._captured_sql = [query_improver(query_info['sql'])
                                    for query_info in self.captured_queries
                                 ]

        return self._captured_sql


class QueriesPrinter(CaptureQueriesContext, ContextDecorator):
    """Print the SQL queries which are executed.
    Use as a context manager:
        with QueriesPrinter():
            [...]

    Use as a decorator:
        @QueriesPrinter()
        def [...]
    """
    def __exit__(self, *args, **kwargs):
        super(QueriesPrinter, self).__exit__(*args, **kwargs)

        queries = self.captured_queries
        if queries:
            print('%s QUERIES:\n' % len(queries) +
                  '\n'.join(' - %(time)s: %(sql)s' % query for query in queries)
                 )