"""
LFF to FontoBene conversion script.
"""
import math
import re
import sys
import os


FORMAT_VERSION = '0.0.0'


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


def convert_vertex(match):
    """
    Convert LFF vertex to FontoBene vertex.
    """
    x = format_number(match.groups()[0])
    y = format_number(match.groups()[1])
    bulge_str = match.groups()[3]
    if bulge_str:
        bulge_deg = math.atan(float(bulge_str)) * 4 / math.pi
        bulge = format_number(bulge_deg * 9)
        return '{},{},{}'.format(x, y, bulge)
    else:
        return '{},{}'.format(x, y)


def convert_ref(match):
    """
    Convert LFF references to FontoBene references.
    """
    return '@{}'.format(match.groups()[0].upper())


def convert_codepoint(match):
    """
    Convert LFF codepoints to FontoBene codepoints.
    """
    groups = match.groups()
    return '{}{}'.format(groups[0].upper(), groups[1])

def split_oneliner(match):
    """
    Split LFF one-liner (codepoint and reference on same line) into two lines
    """
    groups = match.groups()
    return '{}{}\n{}'.format(groups[0], groups[1].rstrip(), groups[2])


def move_bulge_parameter(match):
    """
    Move bulge parameter to start coordinate of arc segments (instead of end coordinate)
    """
    vertices = [v.split(',') for v in match.groups()[0].split(';')]
    for i, vertex in enumerate(vertices):
        if len(vertices[i]) > 2:
            del vertices[i][2]
        if len(vertices) > i + 1 and len(vertices[i + 1]) > 2:
            vertices[i].append(vertices[i + 1][2])
    return ';'.join([','.join(v) for v in vertices])


if __name__ == '__main__':

    # Validate args
    if len(sys.argv) != 2:
        print('Usage: %s <fontfile.lff>' % sys.argv[0])
        sys.exit(1)

    # Read file
    with open(sys.argv[1], 'r') as f:
        lines = f.readlines()

    # Match regexes
    # Note: Some regexes are very tolerant in parsing LFF files because many LFF
    # files contain small format errors, which we still want to parse properly...
    vertex_re = re.compile(r'(-?[0-9\.]+),(-?[0-9\.]+)(,?A?(-?[0-9\.]+))?')
    ref_re = re.compile(r'C([0-9a-fA-F]{4,6})')
    metadata_string_re = re.compile(r'#\s*([a-zA-Z0-9\s]*):\s+(.+)')
    codepoint_re = re.compile(r'^(\[[0-9a-zA-Z]{4,6}\])(.*)')
    oneliner_re = re.compile(r'^(\[[0-9a-zA-Z]{4,6}\])(.*)(C[0-9a-fA-F]{4,6})')
    polyline_re = re.compile(r'((-?[0-9\.]+,-?[0-9\.]+(,-?[0-9\.]+)?;?)+)')
    non_id_char_re = re.compile(r'[^a-zA-Z\-]')

    # Process all lines
    metadata = {}
    out = []
    for line in lines:
        matches = metadata_string_re.match(line)
        if matches:
            groups = matches.groups()
            metadata[groups[0].lower()] = groups[1]
        else:
            converted = line
            converted = vertex_re.sub(convert_vertex, converted)
            converted = oneliner_re.sub(split_oneliner, converted)
            converted = ref_re.sub(convert_ref, converted)
            converted = codepoint_re.sub(convert_codepoint, converted)
            converted = polyline_re.sub(move_bulge_parameter, converted)
            out.append(converted)

    header = True
    for outline in out:
        if header:
            # End of header
            header = False
            print('[format]')
            print('format = FontoBene')
            print('format_version = {}'.format(FORMAT_VERSION))
            print('')
            print('[font]')
            font_name = metadata.get('name', 'converted')
            print('name = {}'.format(font_name))
            font_id = non_id_char_re.sub('', font_name).lower().strip('-')
            print('id = {}'.format(font_id))
            print('version = {}'.format(metadata.get('version', '0.0.0')))
            font_author = metadata.get('author', metadata.get('creator', 'converted'))
            print('author = {}'.format(font_author))
            print('license = {}'.format(metadata.get('license', 'unknown')))
            print('letter_spacing = 1.8')
            print('line_spacing = 15')
            print('')
            print('[user]')
            print('lff_filename = {}'.format(os.path.basename(sys.argv[1])))
            print('lff_LetterSpacing = {:g}'.format(float(metadata.get('LetterSpacing', 3))))
            print('lff_WordSpacing = {:g}'.format(float(metadata.get('WordSpacing', 6.75))))
            print('lff_LineSpacingFactor = {:g}'.format(float(metadata.get('LineSpacingFactor', 1))))
            print('')
            print('---')
            print('')
            print('[0020] SPACE')
            print('~3.6')
            print('')
        else:
            # We're in the body
            print(outline, end='')
