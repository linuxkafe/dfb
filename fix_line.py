with open('sim/fly_ollama_bridge.py', 'r') as f:
    lines = f.readlines()

# Fix line 779 (index 778)
if 'print("' in lines[778] and '[Scenario 2]' in lines[778] and '\n' in lines[778] and '\\n' not in lines[778]:
    print(f'Found at line 779: {repr(lines[778])}')
    lines[778] = lines[778].replace('print("', 'print("\\n').replace('")', '")')
    print('Fixed')

with open('sim/fly_ollama_bridge.py', 'w') as f:
    f.writelines(lines)

print('Done')
