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


def pre_process(data: dict, solve: str, l: list[dict]) -> list[dict]:
    item = data.get(solve)
    item_type = LogicType(item['type'])
    if item_type == LogicType.ref:
        refers_to = item['value']
        l = pre_process(data, refers_to, l)
    elif item_type == LogicType.group or item_type == LogicType.union:
        for el in item['value']['elements'].values():
            l = pre_process(data, el['value'], l)
    elif item_type == LogicType.stream:
        l = pre_process(data, item['value']['stream_type'], l)
        l = pre_process(data, item['value']['user_type'], l)
    if not item.get('included', False):
        name_parts = solve.split('__')
        package = name_parts[0]
        if package.startswith('package_'):
            package = package[8:]
            item['defined'] = True
        else:
            item['defined'] = False
        item['package'] = package
        item['name'] = name_parts[1].lstrip('_')
        item['type'] = item_type
        if item_type == LogicType.ref:
            item['value'] = data[item['value']]['name']
        if item_type == LogicType.stream:
            item['value']['stream_type'] = data[item['value']['stream_type']]['name']
            item['value']['user_type'] = data[item['value']['user_type']]['name']
        l.append(item)
        item['included'] = True
    return l


def new_process(data: dict) -> dict:
    doubles_check = {}
    logic_types = data.get('logic_types', {})
    streamlets = data.get('streamlets', {})
    implementations = data.get('implementations', {})

    def set_name(item):
        name_parts = key.split('__')
        package = name_parts[0]
        if package.startswith('package_'):
            package = package[8:]
            item['defined'] = True
        else:
            item['defined'] = False
        item['package'] = package
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
                        'path': new_path
                    }
                    l.append(connection)
                l = l + find_child_streams(el, new_path)
        return l

    def solve_ref(data: dict, name: str) -> dict:
        solve = data[name]
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
            item['value']['elements'] = {name: solve_ref(logic_types, el['value'])
                                         for name, el in item['value']['elements'].items()}

        if item['type'] == LogicType.stream:
            # Replace reference for stream elements, so we can work with the name and type.
            item['value']['stream_type'] = logic_types[item['value']['stream_type']['value']]
            item['value']['user_type'] = logic_types[item['value']['user_type']['value']]

        if type(item.get('value')) is dict:
            item['document'] = item['value'].get('document')

    for (key, item) in streamlets.items():
        set_name(item)

        # Name ports and substitute references
        for name, port in item['ports'].items():
            logic_type = port['logic_type']
            # Follow all references
            while logic_type['type'] != LogicType.stream:
                logic_type = logic_types[logic_type['value']]
            port['logic_type'] = logic_type
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

    return data


def new_capitalize(value: str):
    return value[:1].upper() + value[1:]


def snake2camel(value: str):
    temp = value.split('_')
    return ''.join(el.title() for el in temp)


def sentence_filter(value: str):
    return new_capitalize(value.strip().rstrip('.') + ".")


def main():
    parser = argparse.ArgumentParser(description="Tydi-Lang-2-Chisel")
    parser.add_argument("output_dir", type=str, help="Output directory")
    parser.add_argument("input", type=str, nargs="*", help="Input file(s) or directory")
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
    env.globals['Direction'] = Direction
    env.filters['sentence'] = sentence_filter
    env.filters['capitalize'] = new_capitalize
    env.filters['snake2camel'] = snake2camel
    template = env.get_template('output.scala')

    for input_file, tydi_data in data.items():
        to_template = new_process(dict(tydi_data))
        output = template.render(to_template)
        # print(output)
        output_file = output_dir.joinpath(f"{input_file.stem}.scala")
        print(f"Saving output based on {input_file} to {output_file}")
        with open(output_file, 'w') as f:
            f.write(output)


if __name__ == '__main__':
    main()
    pass
