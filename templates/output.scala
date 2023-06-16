import tydi_lib._
import chisel3._
import chisel3.internal.firrtl.Width

{% for type in logic_types -%}
{{ type.name }}: {{ type.type }} - {{ type.get('value', '') }}
{% endfor -%}
