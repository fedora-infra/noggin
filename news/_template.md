{% macro reference(value) -%}
   {%- if value.startswith("PR") -%}
     PR #{{ value[2:] }}
   {%- elif value.startswith("C") -%}
     [{{ value[1:] }}](https://github.com/fedora-infra/noggin/commit/{{ value[1:] }})
   {%- else -%}
     #{{ value }}
   {%- endif -%}
{%- endmacro -%}

{{- top_line -}}

Released on {{ versiondata.date }}.

{% for section, _ in sections.items() -%}
{%- if section -%}
## {{section}}
{%- endif -%}

{%- if sections[section] -%}
{%- for category, val in definitions.items() if category in sections[section] and category != "author" -%}
### {{ definitions[category]['name'] }}

{% if definitions[category]['showcontent'] -%}
{%- for text, values in sections[section][category].items() %}
- {{ text }}
{%- if values %}
{% if "\n  - " in text or '\n  * ' in text %}


  (
{%- else %}
 (
{%- endif -%}
{%- for issue in values %}
{{ reference(issue) }}{% if not loop.last %}, {% endif %}
{%- endfor %}
)
{% else %}

{% endif %}
{% endfor -%}
{%- else -%}
- {{ sections[section][category]['']|sort|join(', ') }}

{% endif -%}
{%- if sections[section][category]|length == 0 %}
No significant changes.

{% else -%}
{%- endif %}

{% endfor -%}
{% if sections[section]["author"] -%}
### {{definitions['author']["name"]}}

Many thanks to the contributors of bug reports, pull requests, and pull request reviews for this release:

{% for text, values in sections[section]["author"].items() -%}
- {{ text }}
{% endfor -%}
{%- endif %}

{% else -%}
No significant changes.

{% endif %}
{%- endfor +%}
