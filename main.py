from json import loads, dumps
from jinja2 import Environment, PackageLoader, select_autoescape, FileSystemLoader
env = Environment(
    loader=FileSystemLoader('templates'),
    autoescape=select_autoescape()
)


def get_json() -> dict:
    with open("json_output.json", 'r') as f:
        return loads(f.read())


if __name__ == '__main__':
    tydi_data = get_json()
    template = env.get_template('output.scala')
    output = template.render(tydi_data)
    pass
