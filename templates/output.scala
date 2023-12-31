{% import 'elements.scala' as els -%}
import tydi_lib._
import chisel3._

object MyTypes {
{%- for type in logic_types.values() %}
{%- if type.type == LogicType.bit %}
    {%- if type.defined %}
    /** Bit({{type.value}}) type, defined in {{ type.package }} */
    {%- endif %}
    def {{ type.name }} = UInt({{type.value}}.W)
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
{% endif -%}
{% endfor %}

{%- for streamlet in streamlets.values() %}
{{ els.documentation(streamlet, "Streamlet") }}
class {{ streamlet.name | capitalize }} extends TydiModule {
{%- for port in streamlet.ports.values() %}
    /** Stream of [[{{ port.name }}]] with {{ port.direction.name }} direction.{% if port.document %} {{ port.document | sentence }}{% endif %} */
    val {{ port.name }}Stream = {{ port.logic_type.name | capitalize }}(){% if port.direction == Direction.input %}.flip{% endif %}
    /** IO of [[{{ port.name }}Stream]] with {{ port.direction.name }} direction. */
    val {{ port.name }} = {{ port.name }}Stream.toPhysical

    {%- for sub_port in port.sub_streams %}
        /** IO of "{{sub_port.name}}" sub-stream of [[{{ port.name }}Stream]] with {{ port.direction.name }} direction. */
        val {{ port.name }}_{{ sub_port.name }} = {{ port.name }}Stream.{{ '.'.join(sub_port.path) }}.toPhysical
    {%- endfor %}
{% endfor -%}
}
{% endfor %}

{%- for impl in implementations.values() %}
{{ els.documentation(impl, "Implementation") }}
class {{ impl.name | capitalize }} extends {{ impl.derived_streamlet.name | capitalize }} {
{%- for port in impl.derived_streamlet.ports.values() %}
    // Fixme: Remove the following line if this impl. contains logic. If it just interconnects, remove this comment.
    {{ port.name }}Stream := DontCare
{%- endfor %}
{% if impl.implementation_instances %}
    // Modules
  {%- for inst in impl.implementation_instances.values() %}
    {% if inst.document %}/** {{ inst.document | sentence }} */
    {% endif -%}
    val {{ inst.name }} = Module(new {{ inst.impl.name | capitalize }})
  {%- endfor %}
{% endif %}
{%- if impl.nets %}
    // Connections
  {%- for con in impl.nets.values() %}
    {% if con.document %}// {{ con.document | sentence }}
    {% endif -%}
    {% if con.sink_port_owner_name != "self" %}{{ con.sink_owner.name }}.{% endif %}{{ con.sink_port_name }} := {% if con.src_port_owner_name != "self" %}{{ con.src_owner.name }}.{% endif %}{{ con.src_port_name }}
    {%- for sub_con in con.sub_streams %}
        {% if con.sink_port_owner_name != "self" %}{{ con.sink_owner.name }}.{% endif %}{{ con.sink_port_name }}_{{ sub_con.name }} := {% if con.src_port_owner_name != "self" %}{{ con.src_owner.name }}.{% endif %}{{ con.src_port_name }}_{{ sub_con.name }}
    {%- endfor %}
  {%- endfor %}
{% endif -%}
}
{% endfor %}
