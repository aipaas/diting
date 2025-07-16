import os
from jinja2 import Environment, meta, exceptions

dt_persistent_path = os.getenv("DT_INSPECT_DATA", "data")


def has_jinja2_syntax_parser(text: str):
    try:
        env = Environment()
        # Try to parse the template
        ast = env.parse(text)
        # If parsing succeeds and finds variables/blocks, it has Jinja2 syntax
        variables = meta.find_undeclared_variables(ast)
        return len(variables) > 0 or "{{" in text or "{%" in text
    except exceptions.TemplateSyntaxError:
        # If there's a syntax error, it might still contain Jinja2 syntax
        return "{{" in text or "{%" in text or "{#" in text
    except Exception:
        return False
