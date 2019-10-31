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

import os
import importlib
from core.utils import get_search_dirs
from core.vtg.emg.common import get_necessary_conf_property
from core.vtg.emg.common.specifications import get_specs
from core.vtg.emg.common.process import ProcessCollection


def generate_processes(emg, source):
    """
    This is the main function for generating processes of the environment model in the intermediate representation.
    From the configuration, the function reads the list of generators names and runs them one by one to obtain a final
    set of processes before translation them into C code.

    :param emg: EMG plugin object.
    :param source: Source collection object.
    :return: ProcessCollection object.
    """
    # In a specific order start proess generators
    generator_names = ('.vtg.emg.processGenerator.{}'.format(e) for e in
                       [list(e.keys())[0] for e in get_necessary_conf_property(emg.conf, "intermediate model options")])
    configurations = [list(e.values())[0] for e in get_necessary_conf_property(emg.conf, "intermediate model options")]
    generators = [importlib.import_module(name, 'core') for name in generator_names]

    # Get first kinds of specifications
    kinds = dict()
    for generator in generators:
        kinds[generator.__name__] = generator.specifications_endings

    # Get specifications for each kind of a agenerator
    possible_locations = [root for root, _, _ in os.walk(os.path.dirname(emg.conf['requirements DB']))] + \
                         list(get_search_dirs(emg.conf['main working directory']))
    specifications = get_specs(emg.logger, emg.conf, kinds, possible_locations)

    for index, generator in enumerate(generators):
        generator.generate_processes(emg, source, processes, configurations[index],
                                     {kind: specifications[kind] for kind in kinds[generator.__name__]})

    processes = ProcessCollection(emg.logger, emg.conf)
    return processes

