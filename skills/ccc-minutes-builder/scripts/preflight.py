#!/usr/bin/env python3
"""Runtime preflight: return non-zero if a release-critical dependency is missing."""
import argparse
import importlib.metadata
import shutil
import sys


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--render', action='store_true',
                        help='also require LibreOffice for DOCX visual QA')
    args = parser.parse_args(argv)
    errors = []
    if sys.version_info < (3, 10):
        errors.append('Python 3.10+ required')
    for distribution in ('lxml', 'Pillow'):
        try:
            version = importlib.metadata.version(distribution)
            print('OK      %s %s' % (distribution, version))
        except importlib.metadata.PackageNotFoundError:
            errors.append('missing Python package: %s' % distribution)
    for binary in ('pdfinfo', 'pdftotext', 'pdftoppm'):
        value = shutil.which(binary)
        if value:
            print('OK      %s: %s' % (binary, value))
        else:
            errors.append('missing Poppler command: %s' % binary)
    if args.render and not shutil.which('soffice'):
        errors.append('missing LibreOffice soffice for visual rendering')
    for problem in errors:
        print('BLOCKER %s' % problem)
    print('PREFLIGHT: %s' % ('FAIL' if errors else 'PASS'))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
