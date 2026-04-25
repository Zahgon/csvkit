#!/usr/bin/env python

import agate

from csvkit.cli import CSVKitUtility, parse_column_identifiers


def ignore_case_sort(key):

    def inner(row):
        pass

    return inner


class CSVSort(CSVKitUtility):
    description = 'Sort CSV files. Like the Unix "sort" command, but for tabular data.'

    def add_arguments(self):
        pass

    def main(self):
        if self.args.names_only:
            self.print_column_names()
            return

        if self.additional_input_expected():
            self.argparser.error('You must provide an input file or piped data.')

        sniff_limit = self.args.sniff_limit if self.args.sniff_limit != -1 else None
        table = agate.Table.from_csv(
            self.input_file,
            skip_lines=self.args.skip_lines,
            sniff_limit=sniff_limit,
            column_types=self.get_column_types(),
            **self.reader_kwargs,
        )

        key = parse_column_identifiers(
            self.args.columns,
            table.column_names,
            self.get_column_offset(),
        )

        if self.args.ignore_case:
            key = ignore_case_sort(key)

        table = table.order_by(key, reverse=self.args.reverse)
        table.to_csv(self.output_file, **self.writer_kwargs)


def launch_new_instance():
    utility = CSVSort()
    utility.run()


if __name__ == '__main__':
    launch_new_instance()
