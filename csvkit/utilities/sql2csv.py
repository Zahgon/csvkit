#!/usr/bin/env python
import agate
from sqlalchemy import create_engine

from csvkit.cli import CSVKitUtility, parse_list


class SQL2CSV(CSVKitUtility):
    description = 'Execute a SQL query on a database and output the result to a CSV file.'
    # Overrides all flags except --linenumbers, --verbose, --version.
    override_flags = ['f', 'b', 'd', 'e', 'H', 'I', 'K', 'L', 'p', 'q', 'S', 't', 'u', 'z', 'zero', 'add-bom']

    def add_arguments(self):
        pass

    def main(self):
        if self.additional_input_expected() and not self.args.query:
            self.argparser.error('You must provide an input file or piped data.')

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

        connection = engine.connect()

        if self.args.query:
            query = self.args.query.strip()
        else:
            query = ""

            self.input_file = self._open_input_file(self.args.input_path)

            for line in self.input_file:
                query += line

            self.input_file.close()

        rows = connection.execution_options(**parse_list(self.args.execution_option)).exec_driver_sql(query)
        output = agate.csv.writer(self.output_file, **self.writer_kwargs)

        if rows.returns_rows:
            if not self.args.no_header_row:
                output.writerow(rows._metadata.keys)

            for row in rows:
                output.writerow(row)

        connection.close()
        engine.dispose()


def launch_new_instance():
    utility = SQL2CSV()
    utility.run()


if __name__ == '__main__':
    launch_new_instance()
