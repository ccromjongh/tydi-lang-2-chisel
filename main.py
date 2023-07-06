from enum import Enum
from json import loads, dumps
from collections import OrderedDict

from jinja2 import Environment, PackageLoader, select_autoescape, FileSystemLoader
env = Environment(
    loader=FileSystemLoader('templates'),
    autoescape=select_autoescape()
)


def get_json() -> dict:
    with open("json_output.json", 'r') as f:
        return loads(f.read())


class LogicType(Enum):
    stream = 'Stream'
    bit = 'Bit'
    group = 'Group'
    union = 'Union'
    null = 'Null'
    ref = 'Ref'


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
    logic_types = data.get('logic_types', {})
    for (key, item) in logic_types.items():
        item['type'] = LogicType(item['type'])
        name_parts = key.split('__')
        package = name_parts[0]
        if package.startswith('package_'):
            package = package[8:]
            item['defined'] = True
        else:
            item['defined'] = False
        item['package'] = package
        item['name'] = name_parts[1].lstrip('_') if len(name_parts) > 1 else name_parts[0]

        if item['type'] in [LogicType.group, LogicType.union]:
            # Replace (double) reference for group and union elements by element, so we can work with the name and type.
            item['value']['elements'] = {name: logic_types[logic_types[el['value']]['value']]
                                         for name, el in item['value']['elements'].items()}

    for (key, item) in data.get('stream_size', {}).items():
        name_parts = key.split('__')
        package = name_parts[0]
        if package.startswith('package_'):
            package = package[8:]
            item['defined'] = True
        else:
            item['defined'] = False
        item['package'] = package
        item['name'] = name_parts[1].lstrip('_')

    for (key, item) in data.get('implementations', {}).items():
        name_parts = key.split('__')
        package = name_parts[0]
        if package.startswith('package_'):
            package = package[8:]
            item['defined'] = True
        else:
            item['defined'] = False
        item['package'] = package
        item['name'] = name_parts[1].lstrip('_')
    return data


if __name__ == '__main__':
    tydi_data = get_json()
    # logic_types = tydi_data['logic_types']
    # to_solve = list(logic_types.keys())[-1]
    # processed_data = pre_process(logic_types, to_solve, [])
    template = env.get_template('output.scala')
    # to_template = {'logic_types': OrderedDict((item['name'], item)for item in processed_data), 'streams': [processed_data[-1]['name']]}
    env.globals['LogicType'] = LogicType
    to_template = new_process(dict(tydi_data))
    output = template.render(to_template)
    print(output)
    with open('output.scala', 'w') as f:
        f.write(output)
    pass
