import ast
from pathlib import Path


def test_process_message_does_not_accept_temperature_parameter():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    source = app_path.read_text(encoding="utf-8")
    module = ast.parse(source)

    process_message = next(
        node for node in module.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "process_message"
    )

    parameter_names = [arg.arg for arg in process_message.args.args]
    assert "temperature" not in parameter_names
