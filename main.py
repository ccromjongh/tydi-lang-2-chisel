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
    bits = 'Bits'
    group = 'Group'
    null = 'Null'
    ref = 'Ref'


def pre_process(data: dict, solve: str, l: list[dict]) -> list[dict]:
    item = data.get(solve)
    item_type = LogicType(item['type'])
    if item_type == LogicType.ref:
        refers_to = item['value']
        l = pre_process(data, refers_to, l)
    if not item.get('included', False):
        l.append(item)
    return l


if __name__ == '__main__':
    tydi_data = get_json()
    logic_types = tydi_data['logic_types']
    to_solve = list(logic_types.keys())[-1]
    processed_data = pre_process(logic_types, to_solve, [])
    template = env.get_template('output.scala')
    output = template.render(tydi_data)
    print(output)
    pass
