{% import 'elements.scala' as els -%}
/*
 * This file contains all modules of the "{{ compile_options.package_of_top_level_implementation }}" package which are not external.
 * The `streamlet` interface definitions can be found in the `..._main.scala` file. You can use the implementation
 * definitions in this file as a basis for your own Chisel components. If you want to develop them separately, mark them
 * as @External in your Tydi-lang code.
 */

import nl.tudelft.tydi_chisel._
import chisel3._
import {{ compile_options.package_of_top_level_implementation }}._

{% macro internal_impl(impl) -%}
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
{%- endmacro %}

{%- for impl in implementations.values() %}
{%- if not "External" in impl.attributes -%}
    {{ internal_impl(impl) }}
{%- endif %}
{%- endfor %}
