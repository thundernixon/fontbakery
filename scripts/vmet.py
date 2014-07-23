#!/usr/bin/python
# coding: utf-8
# Copyright 2013 The Font Bakery Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# See AUTHORS.txt for the list of Authors and LICENSE.txt for the License.
#
# Based on http://typophile.com/node/13081
# Also see http://typophile.com/node/13081
from __future__ import print_function
import argparse
import collections
import os
import StringIO
from fontTools.ttLib import TTLibError


def metricview(fonts):
    from cli.ttfont import Font
    view = TextMetricsView()
    for f in fonts:
        try:
            metrics = Font(f)
        except TTLibError, ex:
            print("ERROR: %s" % ex)
            continue
        view.add_metric(os.path.basename(f), metrics)
    view.print_metrics()
    return view.get_contents()


def metricfix(fonts):
    from cli.ttfont import Font
    ymin = 0
    ymax = 0

    for f in fonts:
        metrics = Font(f)
        font_ymin, font_ymax = metrics.get_bounding()
        ymin = min(font_ymin, ymin)
        ymax = max(font_ymax, ymax)

    for f in fonts:
        metrics = Font(f)
        metrics.ascents.set(ymax)
        metrics.descents.set(ymin)
        metrics.linegaps.set(0)
        metrics.save(f + '.fix')


class TextMetricsView(object):

    def __init__(self):
        self.outstream = StringIO.StringIO()

        self._its_metrics_header = ['Parameter          ']
        # first column has a length of largest parameter
        # named OS/2.sTypoDescender
        self._its_metrics = collections.OrderedDict([
            ('ymax', []),
            ('hhea.ascent', []),
            ('OS/2.sTypoAscender', []),
            ('OS/2.usWinAscent', []),
            ('ymin', []),
            ('hhea.descent', []),
            ('OS/2.sTypoDescender', []),
            ('OS/2.usWinDescent', []),
            ('hhea.lineGap', []),
            ('OS/2.sTypoLineGap', []),
            ('hhea total', []),
            ('typo total', []),
            ('win total', []),
            ('UPM:Heights', []),
            ('UPM:Heights %', [])
        ])
        self._inconsistent = set()
        self._inconsistent_table = {}
        self._warnings = []

        self.glyphs = collections.OrderedDict()

    def add_to_table(self, fontname, key, value):
        if self._its_metrics[key] and value not in self._its_metrics[key]:
                self._inconsistent.add(key)

        if key not in self._inconsistent_table:
            self._inconsistent_table[key] = []

        # lookup row with value and append fontname to `fonts` key, eg.:
        # {'hhea.ascent': [{'value': 390,
        #                   'fonts': ['fontname.ttf', 'fontname2.ttf']}]}
        #
        # It looks like json groupped by metrics key
        row = {}
        for r in self._inconsistent_table[key]:
            if r['value'] == value:
                row = r

        if not row:
            row = {'value': value, 'fonts': []}
            self._inconsistent_table[key].append(row)

        row['fonts'].append(fontname)

        self._its_metrics[key].append(value)

    def add_metric(self, font_name, vmet):
        ymin, ymax = vmet.get_bounding()
        self._its_metrics_header.append(font_name)
        self.add_to_table(font_name, 'hhea.ascent', vmet.ascents.hhea)
        self.add_to_table(font_name, 'OS/2.sTypoAscender', vmet.ascents.os2typo)
        self.add_to_table(font_name, 'OS/2.usWinAscent', vmet.ascents.os2win)
        self.add_to_table(font_name, 'hhea.descent', vmet.descents.hhea)
        self.add_to_table(font_name, 'OS/2.sTypoDescender', vmet.descents.os2typo)
        self.add_to_table(font_name, 'OS/2.usWinDescent', vmet.descents.os2win)
        self.add_to_table(font_name, 'hhea.lineGap', vmet.linegaps.hhea)
        self.add_to_table(font_name, 'OS/2.sTypoLineGap', vmet.linegaps.os2typo)
        self._its_metrics['ymax'].append(ymax)
        self._its_metrics['ymin'].append(ymin)

        value = vmet.ascents.get_max() + abs(vmet.descents.get_min())
        upm = '%s:%s' % (vmet.get_upm_heights(), value)
        self._its_metrics['UPM:Heights'].append(upm)

        value = (value / float(vmet.get_upm_heights())) * 100
        self._its_metrics['UPM:Heights %'].append('%d %%' % value)

        hhea_total = vmet.ascents.hhea + abs(vmet.descents.hhea) + vmet.linegaps.hhea
        self._its_metrics['hhea total'].append(hhea_total)

        typo_total = vmet.ascents.os2typo + abs(vmet.descents.os2typo) + vmet.linegaps.os2typo
        self._its_metrics['typo total'].append(typo_total)

        win_total = vmet.ascents.os2win + abs(vmet.descents.os2win)
        self._its_metrics['win total'].append(win_total)

        if len(set([typo_total, hhea_total, win_total])) > 1:
            self._warnings.append('%s has NOT even heights' % font_name)

        self.glyphs[font_name] = vmet.get_highest_and_lowest()

    def print_metrics(self):
        self.print_warnings()
        self.print_metrics_table()
        self.print_high_glyphs()
        self.print_low_glyphs()
        self.print_inconsistent_table()

    def print_warnings(self):
        if self._inconsistent:
            _ = 'WARNING: Inconsistent {}'
            print(_.format(' '.join([str(x) for x in self._inconsistent])),
                  end='\n\n', file=self.outstream)

        if self._warnings:
            for warn in self._warnings:
                print('WARNING: %s' % warn, file=self.outstream)

    def print_metrics_table(self):
        formatstring = ''
        for k in self._its_metrics_header:
            print(('{:<%s}' % (len(k) + 4)).format(k), end='', file=self.outstream)
            formatstring += '{:<%s}' % (len(k) + 4)

        print(file=self.outstream)
        for k, values in self._its_metrics.items():
            print(formatstring.format(*([k] + values)), file=self.outstream)

    def print_high_glyphs(self):
        header_printed = False
        for font, glyphs in self.glyphs.items():
            if glyphs[0]:
                if not header_printed:
                    print(file=self.outstream)
                    print('High Glyphs', file=self.outstream)
                    header_printed = True
                print(font + ':', ' '.join(glyphs[0]), file=self.outstream)

    def print_low_glyphs(self):
        header_printed = False
        for font, glyphs in self.glyphs.items():
            if glyphs[1]:
                if not header_printed:
                    print(file=self.outstream)
                    print('Low Glyphs', file=self.outstream)
                    header_printed = True
                print(font + ':', ' '.join(glyphs[1]), file=self.outstream)

    def print_inconsistent_table(self):
        print(file=self.outstream)
        for metrickey, row in self._inconsistent_table.items():
            value = self.find_max_occurs_from_metrics_key(row)

            tbl = {}
            for r in row:
                if r['value'] == value:
                    continue
                if metrickey not in tbl:
                    tbl[metrickey] = []
                tbl[metrickey] += r['fonts']

            for k, r in tbl.items():
                print('Inconsistent %s:' % k, ', '.join(r), file=self.outstream)

    def find_max_occurs_from_metrics_key(self, metricvalues):
        result = 0
        occurs = 0
        for v in metricvalues:
            if len(v['fonts']) > occurs:
                occurs = len(v['fonts'])
                result = v['value']
        return result

    def get_contents(self):
        self.outstream.seek(0)
        return self.outstream.read()


if __name__ == '__main__':
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from cli.ttfont import Font

    parser = argparse.ArgumentParser()
    # ascent parameters
    parser.add_argument('-a', '--ascents', type=int,
                        help=("Set new ascents value in 'Horizontal Header'"
                              " table"))

    parser.add_argument('-ah', '--ascents-hhea', type=int,
                        help=("Set new ascents value in 'Horizontal Header'"
                              " table ('hhea'). This argument"
                              " cancels --ascents."))
    parser.add_argument('-at', '--ascents-typo', type=int,
                        help=("Set new ascents value in 'Horizontal Header'"
                              " table ('OS/2'). This argument"
                              " cancels --ascents."))
    parser.add_argument('-aw', '--ascents-win', type=int,
                        help=("Set new ascents value in 'Horizontal Header'"
                              " table ('OS/2.Win'). This argument"
                              " cancels --ascents."))

    # descent parameters
    parser.add_argument('-d', '--descents', type=int,
                        help=("Set new descents value in 'Horizontal Header'"
                              " table"))
    parser.add_argument('-dh', '--descents-hhea', type=int,
                        help=("Set new descents value in 'Horizontal Header'"
                              " table ('hhea'). This argument"
                              " cancels --descents."))
    parser.add_argument('-dt', '--descents-typo', type=int,
                        help=("Set new descents value in 'Horizontal Header'"
                              " table ('OS/2'). This argument"
                              " cancels --descents."))
    parser.add_argument('-dw', '--descents-win', type=int,
                        help=("Set new descents value in 'Horizontal Header'"
                              " table ('OS/2.Win'). This argument"
                              " cancels --descents."))

    # linegaps parameters
    parser.add_argument('-l', '--linegaps', type=int,
                        help=("Set new linegaps value in 'Horizontal Header'"
                              " table"))
    parser.add_argument('-lh', '--linegaps-hhea', type=int,
                        help=("Set new linegaps value in 'Horizontal Header'"
                              " table ('hhea')"))
    parser.add_argument('-lt', '--linegaps-typo', type=int,
                        help=("Set new linegaps value in 'Horizontal Header'"
                              " table ('OS/2')"))

    parser.add_argument('--autofix', action="store_true",
                        help="Autofix font metrics")
    parser.add_argument('fonts', nargs='+', metavar='font',
                        help="Font file in OpenType (TTF/OTF) format")

    options = parser.parse_args()

    fonts = options.fonts

    if (options.ascents or options.descents or options.linegaps
            or options.ascents_hhea or options.ascents_typo
            or options.ascents_win or options.descents_hhea
            or options.descents_typo or options.descents_win
            or options.linegaps_hhea or options.linegaps_typo):
        for f in fonts:
            try:
                metrics = Font(f)
            except TTLibError, ex:
                print('Error: %s' % ex)
                continue

            # set ascents, descents and linegaps. FontVerticalMetrics will
            # not set those values if None, and overwrite them if concrete
            # argument has been passed
            metrics.ascents.set(options.ascents)
            metrics.descents.set(options.descents)
            metrics.linegaps.set(options.linegaps)

            metrics.ascents.hhea = options.ascents_hhea
            metrics.ascents.os2typo = options.ascents_typo
            metrics.ascents.os2win = options.ascents_win

            metrics.descents.hhea = options.descents_hhea
            metrics.descents.os2typo = options.descents_typo
            metrics.descents.os2win = options.descents_win

            metrics.linegaps.hhea = options.linegaps_hhea
            metrics.linegaps.os2typo = options.linegaps_typo
            metrics.save(f + '.fix')

    elif options.autofix:
        metricfix(fonts)
    else:
        print(metricview(fonts))