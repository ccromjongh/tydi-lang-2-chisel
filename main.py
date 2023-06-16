from enum import Enum
from json import loads, dumps
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
    null = 'Null'
    ref = 'Ref'


def pre_process(data: dict, solve: str, l: list[dict]) -> list[dict]:
    item = data.get(solve)
    item_type = LogicType(item['type'])
    if item_type == LogicType.ref:
        refers_to = item['value']
        l = pre_process(data, refers_to, l)
    elif item_type == LogicType.group:
        for el in item['value']['elements'].values():
            l = pre_process(data, el['value'], l)
    elif item_type == LogicType.stream:
        l = pre_process(data, item['value']['stream_type'], l)
        l = pre_process(data, item['value']['user_type'], l)
    if not item.get('included', False):
        name_parts = solve.split('__')
        item['package'] = name_parts[0]
        item['name'] = name_parts[1]
        item['type'] = item_type
        l.append(item)
        item['included'] = True
    return l


if __name__ == '__main__':
    tydi_data = get_json()
    logic_types = tydi_data['logic_types']
    to_solve = list(logic_types.keys())[-1]
    processed_data = pre_process(logic_types, to_solve, [])
    template = env.get_template('output.scala')
    to_template = {'logic_types': processed_data}
    output = template.render(to_template)
    print(output)
    pass
