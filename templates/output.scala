{% import 'elements.scala' as els -%}
import tydi_lib._
import chisel3._

{% for type in logic_types.values() -%}
{% if type.type.name == 'bit' %}
{{ els.bit(type) }}
{% elif type.type.name == 'group' %}
{{ els.group(type, logic_types) }}
{% elif type.type.name == 'stream' %}
{{ els.stream(type, logic_types) }}
{% elif type.type.name == 'ref' and logic_types[type.value].type.name == 'stream' %}
class {{type.name | capitalize}} extends {{type.value | capitalize}}
{% endif -%}
{% endfor -%}
