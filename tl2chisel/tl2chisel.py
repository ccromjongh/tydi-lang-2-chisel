#!/usr/bin/env python
import argparse
import sys
import os
from enum import Enum
from json import loads
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape, FileSystemLoader
env = Environment(
    loader=FileSystemLoader(Path(os.path.realpath(__file__)).parent.joinpath('templates')),
    autoescape=select_autoescape()
)

scope_types = ["package", "streamlet", "impl", "group", "union"]


def get_json(file: str | bytes | os.PathLike[str] | os.PathLike[bytes]) -> dict:
    with open(file, 'r') as f:
        return loads(f.read())


class LogicType(Enum):
    stream = 'Stream'
    bit = 'Bit'
    group = 'Group'
    union = 'Union'
    null = 'Null'
    ref = 'Ref'


class Direction(Enum):
    input = 'In'
    output = 'Out'


class ImplType(Enum):
    normal = 'normal'
    template_instance = 'TemplateInstance'
    duplicator = 'duplicator'
    voider = 'voider'


def new_process(data: dict) -> dict:
    doubles_check = {}
    logic_types = data.get('logic_types', {})
    streamlets = data.get('streamlets', {})
    implementations = data.get('implementations', {})

    def set_name(item):
        name_parts = key.split('__')
        scope = name_parts[0]
        item['scope_type'], item['scope_name'] = scope.split("_", 1)
        if item['scope_type'] in scope_types:
            item['defined'] = True
        else:
            item['defined'] = False
        if len(name_parts) == 1:
            item['unique'] = False
            return
        item['name'] = name_parts[1].lstrip('_')

    def filter_port_name(name: str) -> str:
        """
        Tydi-lang cannot handle "in" or "out" as signal name, therefore these are prefixed with "std_".
        This function removes that prefix.

        :param name: Unprocessed name
        :return: Name with "std_" removed
        """
        return name.removeprefix("std_")

    def find_child_streams(stream: dict, path: list[str] = []) -> list:
        l = []
        if stream['type'] != LogicType.stream:
            return l

        data_type = stream['value']['stream_type']
        if data_type['type'] in [LogicType.group, LogicType.union]:
            for name, el in data_type['value']['elements'].items():
                new_path = list(path) + ['el', name]
                if el['type'] == LogicType.stream:
                    connection = {
                        'name': name,
                        'logic_type': stream,
                        'path': new_path
                    }
                    l.append(connection)
                l = l + find_child_streams(el, new_path)
        return l

    def solve_ref(data: dict, ref: dict) -> dict:
        if ref['type'] != LogicType.ref and ref['type'] != 'Ref':
            raise TypeError("Argument given is not a reference")

        aliases = ref.get('alias', [])
        solve = data[ref['value']]
        # Get the possible aliases in a reference and save them in the list
        local_aliases = solve.get('alias', [])
        for alias in local_aliases:
            if alias not in aliases:
                aliases.append(alias)
        # Save aliases to the source logic type
        solve['alias'] = aliases
        if solve['type'] == LogicType.ref:
            return solve_ref(data, solve['value'])
        return solve

    for (key, item) in logic_types.items():
        item['type'] = LogicType(item['type'])
        set_name(item)
        if not item.get('unique', True):
            continue

        check_name = f"{item['name']}.{item['type']}"
        if not doubles_check.get(check_name, False):
            doubles_check[check_name] = True
            item['unique'] = True
        else:
            item['unique'] = False

        if item['type'] in [LogicType.group, LogicType.union]:
            # Replace (double) reference for group and union elements by element, so we can work with the name and type.
            item['value']['elements'] = {name: solve_ref(logic_types, el)
                                         for name, el in item['value']['elements'].items()}

        if item['type'] == LogicType.stream:
            item['value']['stream_type']['type'] = LogicType.ref
            item['value']['user_type']['type'] = LogicType.ref
            # Replace reference for stream elements, so we can work with the name and type.
            item['value']['stream_type'] = solve_ref(logic_types, item['value']['stream_type'])
            item['value']['user_type'] = solve_ref(logic_types, item['value']['user_type'])

        if type(item.get('value')) is dict:
            item['document'] = item['value'].get('document')

    for (key, item) in streamlets.items():
        set_name(item)

        # Name ports and substitute references
        for name, port in item['ports'].items():
            logic_type = port['logic_type']
            # Follow all references
            logic_type['type'] = LogicType.ref
            port['logic_type'] = solve_ref(logic_types, logic_type)
            port['name'] = filter_port_name(name.split('__')[1])
            port['direction'] = Direction(port['direction'])
            port['sub_streams'] = find_child_streams(logic_type)

    # First, name implementations and substitute references
    for (key, item) in implementations.items():
        set_name(item)
        item['derived_streamlet'] = streamlets[item['derived_streamlet']]
        # Name implementations and substitute references
        for name, instance in item['implementation_instances'].items():
            instance['name'] = name.split("__")[1]
            instance["impl"] = implementations[instance['derived_implementation']]

        item['type'] = ImplType.normal if item['impl_type'] == "Normal" else ImplType.template_instance
        if (item['type'] == ImplType.template_instance):
            if item['impl_type']['TemplateInstance']['template_name'] == "duplicator_i":
                item['type'] = ImplType.duplicator
            elif item['impl_type']['TemplateInstance']['template_name'] == "voider_i":
                item['type'] = ImplType.voider

    # Second, process the port connections. All references must be replaced by the above first or the process may fail.
    for (key, item) in implementations.items():
        # Name ports and substitute references
        for name, connection in item['nets'].items():
            connection['src_owner'] = item if connection['src_port_owner_name'] == "self" else item['implementation_instances'][connection['src_port_owner_name']]
            connection['sink_owner'] = item if connection['sink_port_owner_name'] == "self" else item['implementation_instances'][connection['sink_port_owner_name']]
            connection['src_port_name'] = filter_port_name(connection['src_port_name'].split("__")[1])
            connection['sink_port_name'] = filter_port_name(connection['sink_port_name'].split("__")[1])

            src_impl = item if connection['src_port_owner_name'] == "self" else connection['src_owner']['impl']
            src_streamlet = src_impl['derived_streamlet']
            port = next((port for port in src_streamlet['ports'].values() if port['name'] == connection['src_port_name']), None)
            port_type = port['logic_type']
            connection['type'] = port_type
            sub_streams = port['sub_streams']
            data_type = port_type['value']['stream_type']
            connection['data_type'] = data_type
            connection['sub_streams'] = sub_streams
            pass

    # Set the name of logic items to the first alias that is encountered
    for (key, item) in logic_types.items():
        aliases = item.get("alias", [])
        if len(aliases) > 0:
            item['name'] = aliases[-1]

    return data


def new_capitalize(value: str):
    return value[:1].upper() + value[1:]


def new_lower(value: str):
    return value[:1].lower() + value[1:]


def snake2pascal(value: str):
    temp = value.split('_')
    return ''.join(el.title() for el in temp)


def snake2camel(value: str):
    return new_lower(snake2pascal(value))


def sentence_filter(value: str):
    return new_capitalize(value.strip().rstrip('.') + ".")


def main():
    parser = argparse.ArgumentParser(prog="python -m tl2chisel", description="Tydi-lang-2-Chisel")
    parser.add_argument("output_dir", type=str, help="Output directory")
    parser.add_argument("input", type=str, nargs="*", help="Input file(s) or directory")
    parser.add_argument("-e", "--external-only", action='store_true', help="If enabled, emit all implementations as external")
    args = parser.parse_args()

    data = {}

    if args.input:
        first_path = Path(args.input[0])
        # If only one directory is specified, search for all tydi-lang files in the directory.
        if len(args.input) == 1 and first_path.is_dir():
            input_files = first_path.glob('*.json')
        # Get specified input files.
        else:
            input_files = [Path(file) for file in args.input]
        for input_file in input_files:
            # Put all input files in a dictionary with their name
            data[input_file] = get_json(input_file)
    elif not sys.stdin.isatty():
        # Read from stdin
        data["tydi-system"] = loads(sys.stdin.read())
    else:
        raise Exception("Please specify input files or pipe text to stdin")
    output_dir = Path(args.output_dir)

    env.globals['LogicType'] = LogicType
    env.globals['ImplType'] = ImplType
    env.globals['Direction'] = Direction
    env.filters['sentence'] = sentence_filter
    env.filters['capitalize'] = new_capitalize
    env.filters['snake2pascal'] = snake2pascal
    env.filters['snake2camel'] = snake2camel

    output_files = {
        "main": env.get_template('output.scala'),
        "chisel_components": env.get_template('chisel_components.scala'),
        "generation_stub": env.get_template('generation_stub.scala'),
    }

    for input_file, tydi_data in data.items():
        to_template = new_process(dict(tydi_data))
        for name, template in output_files.items():
            output = template.render(to_template, output_dir=output_dir, external_only=args.external_only)
            output_file = output_dir.joinpath(f"{input_file.stem}_{name}.scala")
            print(f"Saving output based on {input_file} to {output_file}")
            with open(output_file, 'w') as f:
                f.write(output)


if __name__ == '__main__':
    main()
    pass
