#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewStroke/Hershey to FontoBene conversion script.
"""
import os
import numpy as np
from scipy import optimize
from ctypes import *

HEADER = """\
# This font was automatically converted from StrokeFont to FontoBene.
# - StrokeFont project:        http://vovanium.ru/sledy/newstroke/en
# - FontoBene specifications:  https://github.com/fontobene/fontobene
# - Converter script:          https://github.com/fontobene/fontobene-converters
#
# As the StrokeFont is released under the CC0-1.0 license, the converted
# FontoBene font is released under the same license. CC0 licence text:
# http://creativecommons.org/publicdomain/zero/1.0/

[format]
format = FontoBene
format_version = 1.0

[font]
name = FontoStroke
id = fontostroke
version = 1.0
author = StrokeFont Developers
author = FontoBene Developers
license = CC0-1.0
letter_spacing = 1.8
line_spacing = 16

---
"""

REPLACEMENT_GLYPH = 'F^K[KFYFY[K['


def format_number(num):
    """
    Properly format a floating point number according the fontobene specifications.
    """
    rounded = round(float(num), 2)
    rounded_str = "{:g}".format(rounded)
    if rounded_str.startswith('-0.'):
        rounded_str = '-' + rounded_str[2:]
    elif rounded_str.startswith('0.'):
        rounded_str = rounded_str[1:]
    return rounded_str


def format_vertex(vertex):
    res = '{},{}'.format(format_number(vertex[0]), format_number(vertex[1]))
    if vertex[2]:
        res += ',{}'.format(format_number(vertex[2]))
    return res


def format_polylines(polylines):
    return '\n'.join([';'.join([format_vertex(v) for v in p]) for p in polylines])


def convert_x(hershey):
    value = ord(hershey) - ord('R')
    value *= 9.0 / 21.0  # hershey to fontobene scaling
    return value


def convert_y(hershey):
    value = ord(hershey) - ord('R')
    value -= 9      # y offset
    value = -value  # y invert
    value *= 9.0 / 21.0  # hershey to fontobene scaling
    return value


def calc_R(x,y, xc, yc):
    """ calculate the distance of each 2D points from the center (xc, yc) """
    return np.sqrt((x-xc)**2 + (y-yc)**2)


def f(c, x, y):
    """ calculate the algebraic distance between the data points and the mean circle centered at c=(xc, yc) """
    Ri = calc_R(x, y, *c)
    return Ri - Ri.mean()


def leastsq_circle(x,y):
    x_m = np.mean(x)
    y_m = np.mean(y)
    center_estimate = x_m, y_m
    center, ier = optimize.leastsq(f, center_estimate, args=(x, y))
    xc, yc = center
    Ri = calc_R(x, y, *center)
    R = Ri.mean()
    residu = np.sum((Ri - R)**2)
    return xc, yc, R, residu


def calc_segment_length(start, end):
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    return np.sqrt(dx*dx + dy*dy)


def try_convert_polyline_to_arc(polyline):
    lengths = [calc_segment_length(polyline[i], polyline[i+1]) for i in range(0, len(polyline)-1)]
    #if np.mean(lengths) > 2:
    #    return None
    #if np.std(lengths) > 0.3:
    #    return None
    xc, yc, r, residu = leastsq_circle([v[0] for v in polyline], [v[1] for v in polyline])
    if residu / len(polyline) > 0.01:
        return None
    #if r > 2:
    #    return None
    x1 = polyline[0][0]
    y1 = polyline[0][1]
    a1 = np.arctan2(y1 - yc, x1 - xc)
    x2 = polyline[-1][0]
    y2 = polyline[-1][1]
    a2 = np.arctan2(y2 - yc, x2 - xc)
    angle = (a2 - a1) * 9 / np.pi
    return [(x1, y1, angle), (x2, y2, polyline[-1][2])]


def convert_polyline_arcs(polyline):
    vertices = list()
    i = 0
    while i < len(polyline):
        arc = None
        for k in range(len(polyline) - i, 2, -1):
            arc = try_convert_polyline_to_arc(polyline[i:i+k])
            if arc:
                vertices += arc
                i += k - 1
                break
        if not arc:
            vertices.append(polyline[i])
            i += 1
    return vertices


def convert_polyline(hershey):
    x_min = None
    x_max = None
    vertices = list()
    for i in range(0, len(hershey) // 2):
        x = convert_x(hershey[i * 2])
        y = convert_y(hershey[i * 2 + 1])
        vertices.append((x, y, 0))
        x_min = min(x, x_min) if x_min else x
        x_max = max(x, x_max) if x_max else x
    return vertices, x_min, x_max


def convert_polylines(hershey):
    x_min_total = None
    x_max_total = None
    polylines = list()
    for p in hershey.split(' R'):
        if len(p):
            polyline, x_min, x_max = convert_polyline(p)
            polylines.append(polyline)
            polylines.append(convert_polyline_arcs(polyline))
            x_min_total = min(x_min, x_min_total) if x_min_total else x_min
            x_max_total = max(x_max, x_max_total) if x_max_total else x_max
    return polylines, x_min_total, x_max_total


def offset_polylines(polylines, x_offset, y_offset):
    return [[(v[0] + x_offset, v[1] + y_offset, v[2]) for v in p] for p in polylines]


def convert_glyph(codepoint, hershey):
    header = '[{:04X}] {}\n'.format(codepoint, chr(codepoint))
    polylines, glyph_left, glyph_right = convert_polylines(hershey[2:])
    if len(polylines) > 0:
        # Actually in hershey fonts every glyph has defined its own spacing
        # before and after the glyph. That spacing is then used by the font
        # layout engine (no additional spacing is required). But in FontoBene
        # we have a global letter spacing which is applied to every glyph.
        # So we ignore the spacing of the hershey font and left-align every
        # glyph to X=0 to not mess up spacing of FontoBene layout engines.
        body = format_polylines(offset_polylines(polylines, -glyph_left, 0))  # left-align glyph
    else:
        # It seems to be a whitespace-only glyph. The whitespace width is
        # defined by the first two letters in the hershey glyph. Because
        # of the different concept of letter spacing, we have to subtract
        # around 3.26 from the total width to get a suitable FontoBene
        # spacing value. Negative spacing values are replaced by zero.
        left = convert_x(hershey[0])
        right = convert_x(hershey[1])
        body = '~{}'.format(format_number(max(right - left - 3.26, 0)))
    return header + body


if __name__ == '__main__':

    # generate C file with hershey font
    os.system('awk -f fontconv.awk symbol.lib font.lib charlist.txt > newstroke_font.c')

    # generate and load shared library
    os.system('gcc -shared -o newstroke_font.so newstroke_font.c')
    lib = cdll.LoadLibrary(os.path.dirname(os.path.abspath(__file__)) + '/newstroke_font.so')

    # load all glyphs into a list
    glyph_count = c_int.in_dll(lib, 'newstroke_font_bufsize').value
    glyph_array_type = c_char_p * glyph_count
    glyphs = [s.decode("utf-8") for s in glyph_array_type.in_dll(lib, 'newstroke_font')]

    # print fontobene file
    print(HEADER)
    for i, glyph in enumerate(glyphs):
        codepoint = i + 0x20
        if glyph == REPLACEMENT_GLYPH:
            continue
        print(convert_glyph(codepoint, glyph))
        print('')
    print(convert_glyph(0xFFFD, REPLACEMENT_GLYPH))  # because U+FFFD is missing in NewStroke
    print('')
