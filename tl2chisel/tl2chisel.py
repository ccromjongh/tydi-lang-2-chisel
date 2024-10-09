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

scope_types = ["package", "streamlet", "impl", "group", "union", "instance"]


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


def stream_namer(stream: dict) -> str:
    """
    Generate a readable name for a stream based on its parameters that are non-default.\n
    The name has a template of "stream_{data_type_name}_{user_type_name}_t{t}_s{s}_c{c}_d{d}", where everything after
    `data_type_name` is optional and only used if not none or non-default.\n
    Example: `stream_myGroup_t4_0_c8`

    :param stream: Stream to generate name for
    :return: A readable name for a stream based on its parameters that are non-default.
    """
    if stream['type'] != LogicType.stream and stream['type'] != 'Stream':
        raise ValueError(f'Unexpected stream type: {stream["type"]}')

    properties = stream['value']
    defaults = {
        "throughput": 1.0,
        "synchronicity": "Sync",
        "complexity": 1,
        "dimension": 1,  # This should be called dimensionality for consistency but the TL output says dimension.
        "direction": "Forward",
    }
    short_names = {
        "throughput": "t",
        "synchronicity": "s",
        "complexity": "c",
        "dimension": "d",
        "direction": "r"
    }
    data_type_name = properties['stream_type']['name']
    user_type_name = properties['user_type']['name'] if properties['user_type']['type'] != LogicType.null else None
    name = f"stream_{data_type_name}"
    if user_type_name is not None:
        name = f"{name}_{user_type_name}"

    for prop, default in defaults.items():
        if properties[prop] != default:
            name = f"{name}_{short_names[prop]}{properties[prop]}"
    name = name.replace('.', '_')
    return name


def new_process(data: dict, auto_naming=True) -> dict:
    doubles_check = {}
    logic_types = data.get('logic_types', {})
    streamlets = data.get('streamlets', {})
    implementations = data.get('implementations', {})

    def set_name(tag: str, item: dict):
        item['name'] = tag
        name_parts = tag.split('__')
        scope = name_parts[0]
        item['scope_type'], item['scope_name'] = scope.split("_", 1)
        if item['scope_type'] in scope_types:
            item['defined'] = True
        else:
            item['defined'] = False
        if len(name_parts) == 1:
            item['unique'] = False
        elif item['defined']:
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
            return ref

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

    def deduplicate(name: str, item: dict):
        """
        Checks if a logic type is already known by this `name`.
        If this is the case, and it's a stream, substitute the stream and user types by the "unique" stream's values.
        This way, they al reference the same types while not keeping track of _all_ the references to a stream.

        :param name: String to check for duplicates
        :param item: Item this name applies for
        :return: If the item is unique or not
        """
        if item.get('unique', True) and not doubles_check.get(name, False):
            doubles_check[name] = item
            item['unique'] = True
        elif doubles_check.get(name, False) != item:
            item['unique'] = False
            if doubles_check.get(name, False) and item['type'] == LogicType.stream:
                item['value']['stream_type'] = doubles_check[name]['value']['stream_type']
                item['value']['user_type'] = doubles_check[name]['value']['user_type']
        return item['unique']

    for (key, item) in logic_types.items():
        item['type'] = LogicType(item['type'])
        set_name(key, item)

        # Remove all duplicate logic types from emission
        check_name = f"{item['name']}.{item['type']}"
        deduplicate(check_name, item)

        if item['type'] in [LogicType.group, LogicType.union]:
            # Replace (double) reference for group and union elements by element, so we can work with the name and type.
            item['value']['elements'] = {name: solve_ref(logic_types, el)
                                         for name, el in item['value']['elements'].items()}

        if item['type'] == LogicType.stream:
            # Replace reference for stream elements, so we can work with the name and type.
            item['value']['stream_type'] = solve_ref(logic_types, item['value']['stream_type'])
            item['value']['user_type'] = solve_ref(logic_types, item['value']['user_type'])

        if type(item.get('value')) is dict:
            item['document'] = item['value'].get('document')

    for (key, item) in streamlets.items():
        set_name(key, item)

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
        set_name(key, item)
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
            item['original_name'] = item['name']
            item['name'] = aliases[-1]
            if item['scope_type'] == "instance":
                item['name'] = f"{item['name']}_{item['scope_name']}"
                # This gives the problem that the original references are not updated, and so the type info
                # that is emitted for streams that represent the same but are duplicate is not correct.
                deduplicate(item['name'], item)

    if auto_naming:
        for (key, item) in logic_types.items():
            if item['type'] == LogicType.stream:
                auto_name = stream_namer(item)
                if item['name'].startswith("generated"):
                    item['original_name'] = item['name']
                    item['name'] = auto_name
                deduplicate(item['name'], item)

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
    parser.add_argument("--no-auto-naming", action='store_true', help="If enabled, prevent auto naming of anonymous streams")
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
    os.makedirs(output_dir, exist_ok=True)

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
        to_template = new_process(dict(tydi_data), not args.no_auto_naming)
        for name, template in output_files.items():
            output = template.render(to_template, output_dir=output_dir, external_only=args.external_only)
            output_file = output_dir.joinpath(f"{input_file.stem}_{name}.scala")
            print(f"Saving output based on {input_file} to {output_file}")
            with open(output_file, 'w') as f:
                f.write(output)


if __name__ == '__main__':
    main()
    pass
