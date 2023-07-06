{% import 'elements.scala' as els -%}
import tydi_lib._
import chisel3._

object MyTypes {
{%- for type in logic_types.values() %}
{%- if type.type == LogicType.bit %}
    {%- if type.defined %}
    /** Bit({{type.value}}) type, defined in {{ type.package }} */
    {%- endif %}
    val {{ type.name }} = UInt({{type.value}}.W)
    assert(this.{{ type.name }}.getWidth == {{type.value}})
{% endif -%}
{% endfor -%}
}

{% for type in logic_types.values() if type.unique -%}
{% if type.type == LogicType.bit %}
{{ els.bit(type) }}
{% elif type.type == LogicType.group %}
{{ els.group(type, logic_types) }}
{% elif type.type == LogicType.union %}
{{ els.union(type, logic_types) }}
{% elif type.type == LogicType.stream %}
{{ els.stream(type.name, type, logic_types) }}
{% elif type.type == LogicType.ref and logic_types[type.value].type == LogicType.stream %}
{{ els.stream_ref(type, logic_types) }}
{% endif -%}
{% endfor %}

{% for streamlet in streamlets.values() -%}
class {{ streamlet.name | capitalize }} extends TydiModule {
  {%- for port in streamlet.ports.values() %}
    /** Stream of [[{{ port.name }}]] with {{ port.direction.name }} direction. */
    val {{ port.name }}_stream = new {{ port.logic_type.name | capitalize }}{% if port.direction == Direction.input %}.flip{% endif %}
    /** IO of [[{{ port.name }}_stream]] with {{ port.direction.name }} direction. */
    val {{ port.name }} = {{ port.name }}_stream.toPhysical
  {%- endfor %}
}
{% endfor %}

// Usage example
class MyModule extends TydiModule {
{%- for stream_name in streams %}
  val {{ stream_name }}: {{ stream_name | capitalize }} = {{ stream_name | capitalize }}()
  val {{ stream_name }}IO: PhysicalStream = {{ stream_name }}.toPhysical
{%- endfor %}
}
