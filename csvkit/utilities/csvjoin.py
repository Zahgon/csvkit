#!/usr/bin/env python

import sys

import agate

from csvkit.cli import CSVKitUtility, isatty, match_column_identifier


class CSVJoin(CSVKitUtility):
    description = 'Execute a SQL-like join to merge CSV files on a specified column or columns.'
    epilog = "Note that the join operation requires reading all files into memory. Don't try this on very large files."
    # Override 'f' because the utility accepts multiple files.
    override_flags = ['f']

    def add_arguments(self):
        pass

    def main(self):
        if isatty(sys.stdin) and self.args.input_paths == ['-']:
            self.argparser.error('You must provide an input file or piped data.')

        self.input_files = []

        for path in self.args.input_paths:
            self.input_files.append(self._open_input_file(path))

        if self.args.columns:
            join_column_names = self._parse_join_column_names(self.args.columns)

            if len(join_column_names) == 1:
                join_column_names = join_column_names * len(self.input_files)

            if len(join_column_names) != len(self.input_files):
                self.argparser.error('The number of join column names must match the number of files, or be a single '
                                     'column name that exists in all files.')

        if (self.args.left_join or self.args.right_join or self.args.outer_join) and not self.args.columns:
            self.argparser.error('You must provide join column names when performing an outer join.')

        if self.args.left_join and self.args.right_join:
            self.argparser.error('It is not valid to specify both a left and a right join.')

        tables = []
        sniff_limit = self.args.sniff_limit if self.args.sniff_limit != -1 else None
        column_types = self.get_column_types()

        for f in self.input_files:
            tables.append(agate.Table.from_csv(
                f,
                skip_lines=self.args.skip_lines,
                sniff_limit=sniff_limit,
                column_types=column_types,
                **self.reader_kwargs,
            ))
            f.close()

        join_column_ids = []

        if self.args.columns:
            for i, table in enumerate(tables):
                join_column_ids.append(match_column_identifier(table.column_names, join_column_names[i]))

        jointab = tables[0]

        if self.args.left_join:
            # Left outer join
            for i, table in enumerate(tables[1:]):
                jointab = agate.Table.join(jointab, table, join_column_ids[0], join_column_ids[i + 1])
        elif self.args.right_join:
            # Right outer join
            jointab = tables[-1]

            remaining_tables = tables[:-1]
            remaining_tables.reverse()

            for i, table in enumerate(remaining_tables):
                jointab = agate.Table.join(jointab, table, join_column_ids[-1], join_column_ids[-(i + 2)])
        elif self.args.outer_join:
            # Full outer join
            for i, table in enumerate(tables[1:]):
                jointab = agate.Table.join(jointab, table, join_column_ids[0], join_column_ids[i + 1], full_outer=True)
        elif self.args.columns:
            # Inner join
            for i, table in enumerate(tables[1:]):
                jointab = agate.Table.join(jointab, table, join_column_ids[0], join_column_ids[i + 1], inner=True)
        else:
            # Sequential join
            for table in tables[1:]:
                jointab = agate.Table.join(jointab, table, full_outer=True)

        jointab.to_csv(self.output_file, **self.writer_kwargs)

    def _parse_join_column_names(self, join_string):
        """
        Parse a list of join columns.
        """
        return list(map(str.strip, join_string.split(',')))


def launch_new_instance():
    utility = CSVJoin()
    utility.run()


if __name__ == '__main__':
    launch_new_instance()
