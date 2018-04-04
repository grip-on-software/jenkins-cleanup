"""
Generate additional pip arguments based on a PyPI registry index URL.
"""

from __future__ import print_function
import urllib.parse
import sys
import tempfile
import pip._vendor.requests.certs as certs

def main(args):
    """
    Main entry point.
    """

    if not args:
        print('Must provide PyPI registry argument', file=sys.stderr)
        sys.exit(1)

    registry_url = args[0]
    certificate_path = args[1] if len(args) > 1 else None

    # Parse URL: does it have a protocol? Get domain name without port/proto.
    if registry_url.startswith('http://') or registry_url.startswith('https://'):
        host = urllib.parse.urlsplit(registry_url).hostname
    else:
        host = registry_url.split(':', 1)[0]
        registry_url = 'http://{}'.format(registry_url)

    arguments = {
        'extra-index-url': registry_url,
        'trusted-host': host
    }

    if certificate_path is not None:
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            bundle_path = certs.where()
            with open(bundle_path, 'r') as bundle_file:
                for line in bundle_file:
                    temp_file.write(line)

            # Append the certificate to the temporary file
            with open(certificate_path, 'r') as certificate_file:
                for line in certificate_file:
                    temp_file.write(line)

            arguments['cert'] = temp_file.name

    print(' '.join('--{} {}'.format(key, value) for key, value in arguments.items()))

if __name__ == '__main__':
    main(sys.argv[1:])
