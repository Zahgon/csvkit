#!/usr/bin/env python
import itertools
import sys

import agate

from csvkit.cli import QUOTING_CHOICES, CSVKitUtility, make_default_headers


class CSVFormat(CSVKitUtility):
    description = 'Convert a CSV file to a custom output format.'
    override_flags = ['I']

    def add_arguments(self):
        pass

    def _extract_csv_writer_kwargs(self):
        pass

    def main(self):
        if self.additional_input_expected():
            sys.stderr.write('No input file or piped data provided. Waiting for standard input:\n')

        writer = agate.csv.writer(self.output_file, **self.writer_kwargs)

        if self.args.out_quoting == 2:
            table = agate.Table.from_csv(
                self.input_file,
                skip_lines=self.args.skip_lines,
                column_types=self.get_column_types(),
                **self.reader_kwargs,
            )

            # table.to_csv() has no option to omit the column names.
            if not self.args.skip_header:
                writer.writerow(table.column_names)

            writer.writerows(table.rows)
        else:
            reader = agate.csv.reader(self.skip_lines(), **self.reader_kwargs)
            if self.args.no_header_row:
                # Peek at a row to get the number of columns.
                _row = next(reader)
                headers = make_default_headers(len(_row))
                reader = itertools.chain([headers, _row], reader)

            if self.args.skip_header:
                next(reader)

            writer.writerows(reader)


def launch_new_instance():
    utility = CSVFormat()
    utility.run()


if __name__ == '__main__':
    launch_new_instance()
