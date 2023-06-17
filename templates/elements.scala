{% macro bit(type) -%}
class {{type.name | capitalize}} extends BitsEl({{type.value}}.W)
{%- endmacro %}
{% macro group(type, types) -%}
class {{type.name | capitalize}} extends Group {
{%- for name, el in type.value.elements.items() %}
    val {{ name }} = new {{ types[el.value.split('__')[1]].value | capitalize }}
{%- endfor %}
}
{%- endmacro %}
{% macro stream(type, types) -%}
class {{type.name | capitalize}} extends PhysicalStreamDetailed(e=new {{type.value.stream_type | capitalize}}, n={{type.value.throughput | int}}, d={{type.value.dimension}}, c={{type.value.complexity}}, r={{'true' if type.value.direction=='Reverse' else 'false'}}, u=Null())
{%- endmacro %}