{% macro documentation_short(item, name) -%}
/**{% if item.defined %} {{ name }}, defined in {{ item.package }}.{% if item.document %}
 * {% endif %}{% endif %}{% if item.document %}{{ item.document | sentence }}{% endif %} */
{%- endmacro %}

{% macro documentation(item, name) -%}
/**{% if item.defined %}
 * {{ name }}, defined in {{ item.package }}.{% endif %}{% if item.document %}
 * {{ item.document | sentence }}{% endif %}
 */
{%- endmacro %}

{% macro bit(type) -%}
{{ documentation_short(type, "Bit(" + type.value  + ")") }}
class {{type.name | capitalize}} extends BitsEl({{type.value}}.W)
{%- endmacro %}

{% macro group(type, types) -%}
{{ documentation_short(type, "Group element") }}
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
{{ documentation_short(type, "Union element") }}
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
{{ documentation_short(type, "Stream") }}
class {{ name | capitalize }} extends PhysicalStreamDetailed(e=new {{type.value.stream_type.name | capitalize}}, n={{type.value.throughput | int}}, d={{type.value.dimension}}, c={{type.value.complexity}}, r={{'true' if type.value.direction=='Reverse' else 'false'}}, u={% if type.value.user_type.type == LogicType.null %}Null(){% else %}new {{type.value.user_type.name | capitalize}}{% endif %})
{%- endmacro %}

{% macro stream_ref(type, types) -%}
{{ stream(type.name, types[type.value], types) }}

object {{ type.name | capitalize }} {
    def apply(): {{ type.name | capitalize }} = new {{ type.name | capitalize }}()
}
{%- endmacro %}
