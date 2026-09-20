import ast

code = """
        return {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": "stimulate_neuron",
                        "arguments": {"neuron_ids": [3000, 3001], "current_nA": 5.0, "duration_ms": 5.0}
                    }
                ]
            }
        }
    }

ast.parse(code)
print('OK')
