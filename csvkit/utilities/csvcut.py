#!/usr/bin/env python

"""
csvcut is originally the work of eminent hackers Joe Germuska and Aaron Bycoffe.

This code is forked from:
https://gist.github.com/561347/9846ebf8d0a69b06681da9255ffe3d3f59ec2c97

Used and modified with permission.
"""

import sys

import agate

from csvkit.cli import CSVKitUtility


class CSVCut(CSVKitUtility):
    description = 'Filter and truncate CSV files. Like the Unix "cut" command, but for tabular data.'
    override_flags = ['L', 'I']

    def add_arguments(self):
        pass

    def main(self):
        if self.args.names_only:
            self.print_column_names()
            return

        if self.additional_input_expected():
            sys.stderr.write('No input file or piped data provided. Waiting for standard input:\n')

        rows, column_names, column_ids = self.get_rows_and_column_names_and_column_ids(**self.reader_kwargs)

        output = agate.csv.writer(self.output_file, **self.writer_kwargs)
        output.writerow([column_names[column_id] for column_id in column_ids])

        for row in rows:
            out_row = [row[column_id] if column_id < len(row) else None for column_id in column_ids]

            if not self.args.delete_empty or any(out_row):
                output.writerow(out_row)


def launch_new_instance():
    utility = CSVCut()
    utility.run()


if __name__ == '__main__':
    launch_new_instance()
