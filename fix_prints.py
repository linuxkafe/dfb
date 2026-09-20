with open('sim/fly_ollama_bridge.py', 'r') as f:
    content = f.read()

replacements = {
    'print("\\n[Scenario 2] Neural Telemetry -> Behavioral Narration")': 'print("\\n[Scenario 2] Neural Telemetry -> Behavioral Narration")',
    'print("-" * 40)': 'print("-" * 40)',
    'print("\\n[Scenario 3] Neurobiologist (Tool Calling)")': 'print("\\n[Scenario 3] Neurobiologist (Tool Calling)")',
    'print("-" * 40)': 'print("-" * 40)',
}

with open('sim/fly_ollama_bridge.py', 'r') as f:
    content = f.read()

for old, new in [
    ('print("\\n[Scenario 2] Neural Telemetry -> Behavioral Narration")', 'print("\\n[Scenario 2] Neural Telemetry -> Behavioral Narration")'),
    ('print("-" * 40)', 'print("-" * 40)'),
    ('print("\\n[Scenario 3] Neurobiologist (Tool Calling)")', 'print("\\n[Scenario 3] Neurobiologist (Tool Calling)")'),
    ('print("-" * 40)', 'print("-" * 40)'),
]:
    content = content.replace(old, new)

with open('sim/fly_ollama_bridge.py', 'w') as f:
    f.write(content)

print('Fixed')
