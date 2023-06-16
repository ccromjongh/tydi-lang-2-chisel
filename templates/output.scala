import tydi_lib._
import chisel3._
import chisel3.internal.firrtl.Width

{% for name, type in logic_types.items() %}
{{ type.type }}: {{ type.get('value', '') }}
{% endfor %}
