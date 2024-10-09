{% import 'elements.scala' as els -%}
package {{ compile_options.package_of_top_level_implementation }}

import nl.tudelft.tydi_chisel._
import chisel3._
import chisel3.experimental.ExtModule

object MyTypes {
{%- for type in logic_types.values() %}
{%- if type.type == LogicType.bit %}
    {%- if type.defined %}
    /** Bit({{type.value}}) type, defined in {{ type.scope_type }} [[{{ type.scope_name }}]] */
    {%- endif %}
    def {{ type.name }}: UInt = UInt({{type.value}}.W)
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
    protected val {{ port.name }}Stream: PhysicalStreamDetailed[{{ port.logic_type.value.stream_type.name | capitalize }}, {% if port.logic_type.value.user_type.type == LogicType.null %}Null{% else %}{{port.logic_type.value.user_type.name | capitalize}}{% endif %}] = {{ port.logic_type.name | capitalize }}(){% if port.direction == Direction.input %}.flip{% endif %}
    /** IO of [[{{ port.name }}Stream]] with {{ port.direction.name }} direction. */
    val {{ port.name }}: PhysicalStream = {{ port.name }}Stream.toPhysical

    {%- for sub_port in port.sub_streams %}
        /** IO of "{{sub_port.name}}" sub-stream of [[{{ port.name }}Stream]] with {{ port.direction.name }} direction. */
        val {{ port.name }}_{{ sub_port.name }}: PhysicalStream = {{ port.name }}Stream.{{ '.'.join(sub_port.path) }}.toPhysical
    {%- endfor %}
{% endfor -%}
}
{% endfor %}

{%- macro internal_impl(impl) -%}
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
    private val {{ inst.name }} = Module(new {{ inst.impl.name | capitalize }})
  {%- endfor %}
{% endif %}
{%- if impl.nets %}
    // Connections
  {%- for con in impl.nets.values() %}
    {% if con.document %}/* {{ con.document | sentence }} */
    {% endif -%}
    {% if con.sink_port_owner_name != "self" %}{{ con.sink_owner.name }}.{% endif %}{{ con.sink_port_name }} := {% if con.src_port_owner_name != "self" %}{{ con.src_owner.name }}.{% endif %}{{ con.src_port_name }}
    {%- for sub_con in con.sub_streams %}
        {% if con.sink_port_owner_name != "self" %}{{ con.sink_owner.name }}.{% endif %}{{ con.sink_port_name }}_{{ sub_con.name }} := {% if con.src_port_owner_name != "self" %}{{ con.src_owner.name }}.{% endif %}{{ con.src_port_name }}_{{ sub_con.name }}
    {%- endfor %}
  {%- endfor %}
{% endif -%}
}
{%- endmacro %}

{%- macro external_impl(impl) -%}
{{ els.documentation(impl, "External implementation") }}
class {{ impl.name | capitalize }} extends TydiExtModule {
{%- for port in impl.derived_streamlet.ports.values() %}
    /** IO of [[{{ port.logic_type.name | capitalize }}]] with {{ port.direction.name }} direction.{% if port.document %} {{ port.document | sentence }}{% endif %} */
    val {{ port.name }}: PhysicalStream = IO({% if port.direction == Direction.input %}Flipped({% endif %}new {{ els.io_stream(port.logic_type.name, port.logic_type, logic_types) }}{% if port.direction == Direction.input %}){% endif %})

    {%- for sub_port in port.sub_streams %}
        /** IO of "{{sub_port.name}}" sub-stream of [[{{ port.name }}Stream]] with {{ port.direction.name }} direction. */
        val {{ port.name }}_{{ sub_port.name }} = IO({% if port.direction == Direction.input %}Flipped({% endif %}new {{ els.io_stream(sub_port.name, sub_port.logic_type, logic_types) }}{% if port.direction == Direction.input %}){% endif %})
    {%- endfor %}
{% endfor -%}
}
{%- endmacro %}

{%- macro duplicator(impl) -%}
{{ els.documentation(impl, "Duplicator implementation") }}
class {{ impl.name | capitalize }} extends {{ impl.derived_streamlet.name | capitalize }} {
  {%- for port in impl.derived_streamlet.ports.values() %}
    {{ port.name }}Stream := DontCare
  {%- endfor %}
    private val duplicator: StreamDuplicator = Module(new StreamDuplicator({{ impl.impl_type.TemplateInstance.instance_args["1"].Int }}, {{ (impl.derived_streamlet.ports.values()|first).name }}))
{% for port in impl.derived_streamlet.ports.values() %}
  {%- if port.direction == Direction.input %}
    duplicator.in := {{ port.name }}
  {%- else %}
    {{ port.name }} := duplicator.out({{ loop.index0 }})
  {%- endif %}
{%- endfor %}
}
{%- endmacro %}

{%- for impl in implementations.values() %}
{% if impl.type == ImplType.duplicator -%}
    {{ duplicator(impl) }}
{% elif "External" in impl.attributes or (external_only and (impl.implementation_instances|length == 0 and impl.nets|length == 0)) -%}
    {{ external_impl(impl) }}
{%- elif impl.implementation_instances|length > 0 or impl.nets|length > 0 -%}
    {#- This means an internal implementation that is not empty! -#}
    {{ internal_impl(impl) }}
{%- endif %}
{% endfor %}
