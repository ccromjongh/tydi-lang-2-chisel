{% macro bit(type) -%}
{% if type.defined -%}
/** Bit({{type.value}}), defined in {{ type.package }} */
{%- endif %}
class {{type.name | capitalize}} extends BitsEl({{type.value}}.W)
{%- endmacro %}
{% macro group(type, types) -%}
{% if type.defined -%}
/** Group element, defined in {{ type.package }} */
{%- endif %}
class {{type.name | capitalize}} extends Group {
{%- for name, el in type.value.elements.items() %}
  {%- if el.type == LogicType.bit %}
    val {{ name }} = MyTypes.{{ el.name }}
  {%- else %}
    val {{ name }} = new {{ el.name | capitalize }}
  {%- endif %}
{%- endfor %}
}
{%- endmacro %}
{% macro union(type, types) -%}
{% if type.defined -%}
/** Union element, defined in {{ type.package }} */
{%- endif %}
class {{type.name | capitalize}} extends Union({{ type.value.elements.keys() | length }}) {
{%- for name, el in type.value.elements.items() %}
  {%- if el.type == LogicType.bit %}
    val {{ name }} = MyTypes.{{ el.name }}
  {%- else %}
    val {{ name }} = new {{ el.name | capitalize }}
  {%- endif %}
{%- endfor %}
}
{%- endmacro %}
{% macro stream(name, type, types) -%}
{% if type.defined -%}
/** Stream, defined in {{ type.package }} */
{%- endif %}
class {{ name | capitalize }} extends PhysicalStreamDetailed(e=new {{type.value.stream_type | capitalize}}, n={{type.value.throughput | int}}, d={{type.value.dimension}}, c={{type.value.complexity}}, r={{'true' if type.value.direction=='Reverse' else 'false'}}, u=Null())
{%- endmacro %}
{% macro stream_ref(type, types) -%}
{{ stream(type.name, types[type.value], types) }}

object {{ type.name | capitalize }} {
    def apply(): {{ type.name | capitalize }} = new {{ type.name | capitalize }}()
}
{%- endmacro %}
