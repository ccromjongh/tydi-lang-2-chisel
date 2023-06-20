{% import 'elements.scala' as els -%}
import tydi_lib._
import chisel3._

{% for type in logic_types.values() -%}
{% if type.type.name == 'bit' %}
{{ els.bit(type) }}
{% elif type.type.name == 'group' %}
{{ els.group(type, logic_types) }}
{% elif type.type.name == 'ref' and logic_types[type.value].type.name == 'stream' %}
{{ els.stream_ref(type, logic_types) }}
{% endif -%}
{% endfor %}

// Usage example
class MyModule extends TydiModule {
{%- for stream_name in streams %}
  val {{ stream_name }}: {{ stream_name | capitalize }} = {{ stream_name | capitalize }}()
  val {{ stream_name }}IO: PhysicalStream = {{ stream_name }}.toPhysical
{%- endfor %}
}
