import logging
import pathlib
import sys

import trustme


logging.basicConfig(level=logging.INFO)


def main():
    if len(sys.argv) != 2:
        logging.error('Usage: %s <hostname>', sys.argv[0])
        sys.exit(1)
    hostname = sys.argv[1]
    here = pathlib.Path(__file__).parent
    ca_path = here / 'ca.crt'
    server_path = here / 'server.crt'
    logging.info('Creating self-signed certificate for "%s"', hostname)
    ca_cert = trustme.CA()
    ca_cert.cert_pem.write_to_path(ca_path)
    logging.info(' * CA certificate: {}'.format(ca_path))
    server_cert = ca_cert.issue_server_cert(hostname)
    server_cert.private_key_and_cert_chain_pem.write_to_path(server_path)
    logging.info(' * Server certificate: {}'.format(server_path))
    logging.info('Done')


if __name__ == '__main__':
    main()
