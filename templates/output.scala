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
{% if type.type == LogicType.group %}
{{ els.group(type, logic_types) }}
{% elif type.type == LogicType.union %}
{{ els.union(type, logic_types) }}
{% elif type.type == LogicType.stream %}
{{ els.stream(type.name, type, logic_types) }}
{% elif type.type == LogicType.ref and logic_types[type.value].type == LogicType.stream %}
{{ els.stream_ref(type, logic_types) }}
{% endif -%}
{% endfor %}

{%- for streamlet in streamlets.values() %}
class {{ streamlet.name | capitalize }} extends TydiModule {
  {%- for port in streamlet.ports.values() %}
    /** Stream of [[{{ port.name }}]] with {{ port.direction.name }} direction. */
    val {{ port.name }}_stream = new {{ port.logic_type.name | capitalize }}{% if port.direction == Direction.input %}.flip{% endif %}
    /** IO of [[{{ port.name }}_stream]] with {{ port.direction.name }} direction. */
    val {{ port.name }} = {{ port.name }}_stream.toPhysical
  {%- endfor %}
}
{% endfor %}

{%- for impl in implementations.values() %}
{% if impl.defined -%}
/** Implementation, defined in {{ impl.package }} */
{%- endif %}
class {{ impl.name | capitalize }} extends {{ impl.derived_streamlet.name | capitalize }} {
    // Modules
  {%- for inst in impl.implementation_instances.values() %}
    val {{ inst.name }} = Module(new {{ inst.impl.name | capitalize }})
  {%- endfor %}
    // Connections
  {%- for con in impl.nets.values() %}
    {% if con.sink_port_owner_name != "self" %}{{ con.sink_owner.name }}.{% endif %}{{ con.sink_port_name }} := {% if con.src_port_owner_name != "self" %}{{ con.src_owner.name }}.{% endif %}{{ con.src_port_name }}
  {%- endfor %}
}
{% endfor %}
