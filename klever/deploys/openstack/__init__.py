#
# Copyright (c) 2018 ISP RAS (http://www.ispras.ru)
# Ivannikov Institute for System Programming of the Russian Academy of Sciences
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

import argparse
import errno
import getpass
import os
import sys

from klever.deploys.openstack.instances import OSKleverInstances
from klever.deploys.openstack.instance import OSKleverInstance
from klever.deploys.openstack.image import OSKleverBaseImage
from klever.deploys.utils import check_deployment_configuration_file, get_logger
from klever.deploys.openstack.constants import OS_USER


def load_default_base_image_name():
    with open(os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'conf', 'openstack-base-image.txt'))) \
            as fp:
        return fp.read().strip()


def parse_args(args, logger):
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['show', 'create', 'update', 'ssh', 'remove', 'share', 'hide'],
                        help='Action to be executed.')
    parser.add_argument('entity', choices=['image', 'instance'],
                        help='Entity for which action to be executed.')
    parser.add_argument('--os-auth-url', default='https://sky.ispras.ru:13000',
                        help='OpenStack identity service endpoint for authorization (default: "%(default)s").')
    parser.add_argument('--os-username', default=getpass.getuser(),
                        help='OpenStack username for authentication (default: "%(default)s").')
    parser.add_argument('--os-tenant-name', default='computations',
                        help='OpenStack tenant name (default: "%(default)s").')
    parser.add_argument('--os-domain-name', default='ispras',
                        help='OpenStack domain name (default: "%(default)s").')
    parser.add_argument('--os-network-type', default='internal',
                        help='OpenStack network type. Can be "internal" or "external" (default: "%(default)s").')
    parser.add_argument('--os-sec-group', default='ldv-sec',
                        help='OpenStack security group (default: "%(default)s").')
    parser.add_argument('--os-keypair-name', default='ldv',
                        help='OpenStack keypair name (default: "%(default)s").')
    parser.add_argument('--ssh-username', default=OS_USER,
                        help='SSH username for authentication (default: "%(default)s").')
    parser.add_argument('--ssh-rsa-private-key-file',
                        help='Path to SSH RSA private key file.'
                             'The appropriate SSH RSA key pair should be stored to OpenStack by name "ldv".')
    parser.add_argument('--name', help='Entity name.')
    parser.add_argument('--base-image', default='Debian-9-amd64',
                        help='Name of base image on which Klever base image will be based on (default: "%(default)s").')
    parser.add_argument('--klever-base-image', default=load_default_base_image_name(),
                        help='Name of Klever base image on which instances will be based on (default: "%(default)s").')
    parser.add_argument('--vcpus', default=2, type=int,
                        help='Number of VCPUs to be used in new instances (default: "%(default)s").')
    parser.add_argument('--ram', type=int,
                        help='Amount of RAM to be used in new instances (default: 4 x VCPUs x 1024).')
    parser.add_argument('--disk', default=200, type=int,
                        help='Amount of disk space to be used in new instances (default: "%(default)s").')
    parser.add_argument('--instances', type=int, default=1,
                        help='The number of new Klever instances (default: "%(default)s").')
    parser.add_argument('--mode', choices=['development', 'production'], default='production',
                        help='Mode for which action to be executed (default: "%(default)s").')
    parser.add_argument('--deployment-configuration-file',
                        default=os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'conf', 'klever.json')),
                        help='Path to Klever deployment configuration file (default: "%(default)s").')
    parser.add_argument('--source-directory', default=os.getcwd(),
                        help='Path to Klever source directory (default: "%(default)s").')
    parser.add_argument('--update-packages', default=False, action='store_true',
                        help='Update packages for actions "create" and "update" (default: "%(default)s"). '
                             'This option has no effect for other actions.')
    parser.add_argument('--update-python3-packages', default=False, action='store_true',
                        help='Update Python3 packages for action "create" and "update" (default: "%(default)s"). '
                             'This option has no effect for other actions.')
    parser.add_argument('--store-password', action='store_true',
                        help='Store OpenStack password on disk (default: False).')

    # TODO: Check the correctness of the provided arguments
    args = parser.parse_args(args)

    if args.instances <= 0:
        logger.error('The number of new Klever instances must be greater then 0')
        sys.exit(errno.EINVAL)

    if not args.ram:
        args.ram = args.vcpus * 4 * 1024

    return args


def main(sys_args=sys.argv[1:]):
    logger = get_logger(__name__)

    args = parse_args(sys_args, logger)

    check_deployment_configuration_file(logger, args.deployment_configuration_file)

    try:
        if args.entity == 'image':
            getattr(OSKleverBaseImage(args, logger), args.action)()
        elif args.entity == 'instance' and args.instances == 1:
            getattr(OSKleverInstance(args, logger), args.action)()
        elif args.entity == 'instance' and args.instances > 1:
            getattr(OSKleverInstances(args, logger), args.action)()
        else:
            logger.error(f'Entity "{args.entity}" is not supported')
            sys.exit(errno.ENOSYS)
    except SystemExit:
        logger.error(
            f'Could not execute action "{args.action}" for "{args.entity}" (analyze error messages above for details)'
        )
        raise

    logger.info('Finish execution of action "{0}" for "{1}"'.format(args.action, args.entity))
