from functools import wraps
import hashlib
try:
    import json
except ImportError:
    import simplejson as json

try:
    from flaskext.sqlalchemy import get_debug_queries
except ImportError:
    get_debug_queries = None


from flask import request, current_app, abort, render_template
from flask_debugtoolbar import module
from flask_debugtoolbar.panels import DebugPanel
from flask_debugtoolbar.utils import format_fname, format_sql
from flaskext.sqlalchemy import SQLAlchemy


_ = lambda x: x

class SQLAlchemyDebugPanel(DebugPanel):
    """
    Panel that displays the time a response took in milliseconds.
    """
    name = 'SQLAlchemy'

    @staticmethod
    def setup_url_rules():
        # Panel views
        def hash_check_view_decorator(f):
            @wraps(f)
            def wrapper(*args, **kwds):
                statement = request.args['sql']
                params = request.args['params']

                # Validate hash
                hash = hashlib.sha1(
                    current_app.config['SECRET_KEY'] + statement + params).hexdigest()
                if hash != request.args['hash']:
                    return abort(406)

                # Make sure it is a select statement
                if not statement.lower().strip().startswith('select'):
                    return abort(406)

                return f(*args, **kwds)
            return wrapper

        @hash_check_view_decorator
        def sql_select():
            statement = request.args['sql']
            params = request.args['params']
            params = json.loads(params)

            db = SQLAlchemy()
            result = db.engine.execute(statement, params)
            return render_template('panels/sqlalchemy_select.html', **{
                'result': result.fetchall(),
                'headers': result.keys(),
                'sql': format_sql(statement, params),
                'duration': float(request.args['duration']),
                })

        @hash_check_view_decorator
        def sql_explain():
            statement = request.args['sql']
            params = request.args['params']
            params = json.loads(params)

            db = SQLAlchemy()
            if db.engine.driver == 'pysqlite':
                query = 'EXPLAIN QUERY PLAN %s' % statement
            elif db.engine.driver == 'psycopg2':
                query = 'EXPLAIN VERBOSE %s' % statement
            else:
                query = 'EXPLAIN %s' % statement

            result = db.engine.execute(query, params)
            return render_template('panels/sqlalchemy_explain.html', **{
                'result': result.fetchall(),
                'headers': result.keys(),
                'sql': format_sql(statement, params),
                'duration': float(request.args['duration']),
                })

        module.add_url_rule('/sqlalchemy/sql_select',
            'sql_select',
            view_func=sql_select,
            methods=['GET', 'POST']
        )

        module.add_url_rule('/sqlalchemy/sql_explain',
            'sql_explain',
            view_func=sql_explain,
            methods=['GET', 'POST']
        )


    @property
    def has_content(self):
        return True if get_debug_queries and get_debug_queries() else False

    def process_request(self, request):
        pass

    def process_response(self, request, response):
        pass

    def nav_title(self):
        return _('SQLAlchemy')

    def nav_subtitle(self):
        if get_debug_queries:
            count = len(get_debug_queries())
            return "%d %s" % (count, "query" if count == 1 else "queries")

    def title(self):
        return _('SQLAlchemy queries')

    def url(self):
        return ''

    def content(self):
        queries = get_debug_queries()
        data = []
        for query in queries:
            is_select = query.statement.strip().lower().startswith('select')
            _params = ''
            try:
                _params = json.dumps(query.parameters)
            except TypeError:
                pass # object not JSON serializable


            hash = hashlib.sha1(
                current_app.config['SECRET_KEY'] +
                query.statement + _params).hexdigest()

            data.append({
                'duration': query.duration,
                'sql': format_sql(query.statement, query.parameters),
                'raw_sql': query.statement,
                'hash': hash,
                'params': _params,
                'is_select': is_select,
                'context_long': query.context,
                'context': format_fname(query.context)
            })
        return self.render('panels/sqlalchemy.html', { 'queries': data})
