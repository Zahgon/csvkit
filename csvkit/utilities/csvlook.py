#!/usr/bin/env python

import agate
from agate import config

from csvkit.cli import CSVKitUtility


class CSVLook(CSVKitUtility):
    description = 'Render a CSV file in the console as a Markdown-compatible, fixed-width table.'

    def add_arguments(self):
        pass

    def main(self):
        if self.additional_input_expected():
            self.argparser.error('You must provide an input file or piped data.')

        kwargs = {}
        # In agate, max_precision defaults to 3. None means infinity.
        if self.args.max_precision is not None:
            kwargs['max_precision'] = self.args.max_precision

        if self.args.no_number_ellipsis:
            config.set_option('number_truncation_chars', '')

        sniff_limit = self.args.sniff_limit if self.args.sniff_limit != -1 else None
        table = agate.Table.from_csv(
            self.input_file,
            skip_lines=self.args.skip_lines,
            sniff_limit=sniff_limit,
            row_limit=self.args.max_rows,
            column_types=self.get_column_types(),
            line_numbers=self.args.line_numbers,
            **self.reader_kwargs,
        )

        table.print_table(
            output=self.output_file,
            max_rows=self.args.max_rows,
            max_columns=self.args.max_columns,
            max_column_width=self.args.max_column_width,
            **kwargs,
        )


def launch_new_instance():
    utility = CSVLook()
    utility.run()


if __name__ == '__main__':
    launch_new_instance()
