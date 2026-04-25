#!/usr/bin/env python
import os.path
import sys

import agate
import agatesql  # noqa: F401
from sqlalchemy import create_engine, dialects

from csvkit.cli import CSVKitUtility, isatty, parse_list

try:
    import importlib_metadata
except ImportError:
    import importlib.metadata as importlib_metadata

DIALECTS = dialects.__all__ + tuple(e.name for e in importlib_metadata.entry_points(group='sqlalchemy.dialects'))


class CSVSQL(CSVKitUtility):
    description = 'Generate SQL statements for one or more CSV files, or execute those statements directly on a ' \
                  'database, and execute one or more SQL queries.'
    # Override 'f' because the utility accepts multiple files.
    override_flags = ['f']

    def add_arguments(self):
        pass

    def main(self):
        if isatty(sys.stdin) and self.args.input_paths == ['-']:
            self.argparser.error('You must provide an input file or piped data.')

        self.input_files = []
        self.connection = None
        self.table_names = []
        self.unique_constraint = []

        if self.args.table_names:
            self.table_names = self.args.table_names.split(',')
        if self.args.unique_constraint:
            self.unique_constraint = self.args.unique_constraint.split(',')

        # Create a SQLite database in memory if no connection string is specified
        if self.args.queries and not self.args.connection_string:
            self.args.connection_string = "sqlite:///:memory:"
            self.args.insert = True

        if self.args.dialect and self.args.connection_string:
            self.argparser.error('The --dialect option is only valid when neither --db nor --query are specified.')
        if self.args.insert and not self.args.connection_string:
            self.argparser.error('The --insert option is only valid when either --db or --query is specified.')

        if self.args.no_create and not self.args.insert:
            self.argparser.error('The --no-create option is only valid if --insert is also specified.')
        if self.args.create_if_not_exists and not self.args.insert:
            self.argparser.error('The --create-if-not-exists option is only valid if --insert is also specified.')
        if self.args.overwrite and not self.args.insert:
            self.argparser.error('The --overwrite option is only valid if --insert is also specified.')
        if self.args.overwrite and self.args.no_create:
            self.argparser.error('The --overwrite option is only valid if --no-create is not specified.')
        if self.args.before_insert and not self.args.insert:
            self.argparser.error('The --before-insert option is only valid if --insert is also specified.')
        if self.args.after_insert and not self.args.insert:
            self.argparser.error('The --after-insert option is only valid if --insert is also specified.')
        if self.args.chunk_size and not self.args.insert:
            self.argparser.error('The --chunk-size option is only valid if --insert is also specified.')

        if self.args.no_create and self.args.create_if_not_exists:
            self.argparser.error('The --no-create and --create-if-not-exists options are mutually exclusive.')

        # Lazy open files
        for path in self.args.input_paths:
            self.input_files.append(self._open_input_file(path))

        # Establish database validity before reading CSV files
        if self.args.connection_string:
            try:
                engine = create_engine(self.args.connection_string, **parse_list(self.args.engine_option))
            except ImportError as e:
                raise ImportError(
                    "You don't appear to have the necessary database backend installed for connection string you're "
                    "trying to use. Available backends include:\n\nPostgreSQL:\tpip install psycopg2\nMySQL:\t\tpip "
                    "install mysql-connector-python OR pip install mysqlclient\n\nFor details on connection strings "
                    "and other backends, please see the SQLAlchemy documentation on dialects at:\n\n"
                    "https://www.sqlalchemy.org/docs/dialects/"
                ) from e

            self.connection = engine.connect()

        try:
            self._failsafe_main()
        finally:
            for f in self.input_files:
                f.close()

            if self.connection:
                self.connection.close()
                engine.dispose()

    def _failsafe_main(self):
        """
        Inner main function. If anything fails in here, file handles and
        database connections will be safely closed.
        """
        if self.connection:
            transaction = self.connection.begin()

        for f in self.input_files:
            try:
                # Try to use name specified via --tables
                table_name = self.table_names.pop(0)
            except IndexError:
                if f == sys.stdin:
                    table_name = "stdin"
                else:
                    # Use filename as table name
                    table_name = os.path.splitext(os.path.basename(f.name))[0]

            table = None
            sniff_limit = self.args.sniff_limit if self.args.sniff_limit != -1 else None

            try:
                table = agate.Table.from_csv(
                    f,
                    skip_lines=self.args.skip_lines,
                    sniff_limit=sniff_limit,
                    column_types=self.get_column_types(),
                    **self.reader_kwargs,
                )
            except StopIteration:
                # Catch cases where no table data was provided and fall through
                # to query logic
                continue

            if table:
                if self.connection:
                    if self.args.before_insert:
                        for query in self.args.before_insert.split(self.args.sql_delimiter):
                            self.connection.exec_driver_sql(query)

                    table.to_sql(
                        self.connection,
                        table_name,
                        overwrite=self.args.overwrite,
                        create=not self.args.no_create,
                        create_if_not_exists=self.args.create_if_not_exists,
                        insert=self.args.insert and len(table.rows) > 0,
                        prefixes=self.args.prefix,
                        db_schema=self.args.db_schema,
                        constraints=not self.args.no_constraints,
                        unique_constraint=self.unique_constraint,
                        chunk_size=self.args.chunk_size,
                        min_col_len=self.args.min_col_len,
                        col_len_multiplier=self.args.col_len_multiplier,
                    )

                    if self.args.after_insert:
                        for query in self.args.after_insert.split(self.args.sql_delimiter):
                            self.connection.exec_driver_sql(query)

                # Output SQL statements
                else:
                    statement = table.to_sql_create_statement(
                        table_name,
                        dialect=self.args.dialect,
                        db_schema=self.args.db_schema,
                        constraints=not self.args.no_constraints,
                        unique_constraint=self.unique_constraint,
                    )

                    self.output_file.write(f'{statement}\n')

        if self.connection:
            if self.args.queries:
                queries = []
                for query in self.args.queries:
                    if os.path.exists(query):
                        with open(query) as f:
                            query = f.read()
                    queries += query.split(self.args.sql_delimiter)

                # Execute the specified SQL queries.
                rows = None

                for query in queries:
                    if query.strip():
                        rows = self.connection.exec_driver_sql(query)

                # Output the result of the last query as CSV
                if rows.returns_rows:
                    output = agate.csv.writer(self.output_file, **self.writer_kwargs)
                    output.writerow(rows._metadata.keys)
                    for row in rows:
                        output.writerow(row)

            transaction.commit()


def launch_new_instance():
    utility = CSVSQL()
    utility.run()


if __name__ == '__main__':
    launch_new_instance()
