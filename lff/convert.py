"""
LFF to FontoBene conversion script.
"""
import math
import re
import sys


FORMAT_VERSION = '0.0.0'


def convert_arc(match):
    """
    Convert LFF angles to FontoBene angles.
    """
    val = float(match.group()[1:])
    converted_deg = math.atan(val) * 4 / math.pi
    return str(converted_deg * 9)


if __name__ == '__main__':

    # Validate args
    if len(sys.argv) != 2:
        print('Usage: %s <fontfile.lff>' % sys.argv[0])
        sys.exit(1)

    # Read file
    with open(sys.argv[1], 'r') as f:
        lines = f.readlines()

    # Match regexes
    arc_re = re.compile(r'A-?[0-9\.]+')
    metadata_string_re = re.compile(r'#\s*([a-zA-Z0-9]*):\s+(.+)')
    non_id_char_re = re.compile(r'[^a-zA-Z\-]')

    # Process all lines
    metadata = {}
    out = []
    for line in lines:
        converted = arc_re.sub(convert_arc, line)

        matches = metadata_string_re.match(line)
        if matches:
            groups = matches.groups()
            metadata[groups[0].lower()] = groups[1]

        out.append(converted)

    header = True
    for outline in out:
        if header and not outline.startswith('#'):
            # End of header
            header = False
            print('')
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
            print('')
        else:
            # We're in the body
            print(outline, end='')
