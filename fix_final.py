with open('sim/fly_ollama_bridge.py', 'r') as f:
    content = f.read()

# Replace the problematic section
old = '''    print("  [Tool] stimulate_neuron(neuron_ids=[3000, 3001], current_nA=5.0, duration_ms=5.0)")
    result = await type('tools', (), {
        'stimulate_neuron': lambda self, ids, cur, dur: {"spike_counts": {i: 2 for i in ids}, "success": True},
        'record_activity': lambda self, c, d: {"mean_rate": 120.0, "spike_counts": {3000: 5, 3001: 5}, "latency_ms": 1.2},
        'get_kinematics': lambda self: {"jump_occurred": True, "leg_extension_ms": 1.2, "takeoff_angle": 15.0, "wing_beat_freq": 200.0},
    })().stimulate_neuron([3000, 3001], 5.0, 5.0)
    print(f"  Spike counts: {result['spike_counts']}")

    rec = await type('tools', (), {
        'record_activity': lambda self, c, d: {"mean_rate": 120.0, "spike_counts": {3000: 5, 3001: 5}, "latency_ms": 1.2},
    })().record_activity("GF", 10.0)
    print(f"  GF recording: {rec['mean_rate']:.1f} Hz mean rate")

    kin = await type('tools', (), {
        'get_kinematics': lambda self: {"jump_occurred": True, "leg_extension_ms": 1.2, "takeoff_angle": 15.0, "wing_beat_freq": 200.0},
    })().get_kinematics()
    print(f"  Kinematics: jump={kin['jump_occurred']}, leg_ext={kin['leg_extension_ms']:.1f}ms")'''

new = '''    # Direct calls since tools return values directly (not awaitable)
    tools = type('tools', (), {
        'stimulate_neuron': lambda self, ids, cur, dur: {"spike_counts": {i: 2 for i in ids}, "success": True},
        'record_activity': lambda self, c, d: {"mean_rate": 120.0, "spike_counts": {3000: 5, 3001: 5}, "latency_ms": 1.2},
        'get_kinematics': lambda self: {"jump_occurred": True, "leg_extension_ms": 1.2, "takeoff_angle": 15.0, "wing_beat_freq": 200.0},
    })()

    print("  [Tool] stimulate_neuron(neuron_ids=[3000, 3001], current_nA=5.0, duration_ms=5.0)")
    result = type('tools', (), {
        'stimulate_neuron': lambda self, ids, cur, dur: {"spike_counts": {i: 2 for i in ids}, "success": True},
        'record_activity': lambda self, c, d: {"mean_rate": 120.0, "spike_counts": {3000: 5, 3001: 5}, "latency_ms": 1.2},
        'get_kinematics': lambda self: {"jump_occurred": True, "leg_extension_ms": 1.2, "takeoff_angle": 15.0, "wing_beat_freq": 200.0},
    })().stimulate_neuron([3000, 3001], 5.0, 5.0)
    print(f"  Spike counts: {result['spike_counts']}")

    rec = type('tools', (), {
        'record_activity': lambda self, c, d: {"mean_rate": 120.0, "spike_counts": {3000: 5, 3001: 5}, "latency_ms": 1.2},
    })().record_activity("GF", 10.0)
    print(f"  GF recording: {rec['mean_rate']:.1f} Hz mean rate")

    kin = type('tools', (), {
        'get_kinematics': lambda self: {"jump_occurred": True, "leg_extension_ms": 1.2, "takeoff_angle": 15.0, "wing_beat_freq": 200.0},
    })().get_kinematics()
    print(f"  Kinematics: jump={kin['jump_occurred']}, leg_ext={kin['leg_extension_ms']:.1f}ms")'''

with open('sim/fly_ollama_bridge.py', 'r') as f:
    content = f.read()

content = content.replace(
    '''    print("  [Tool] stimulate_neuron(neuron_ids=[3000, 3001], current_nA=5.0, duration_ms=5.0)")
    result = await type('tools', (), {
        'stimulate_neuron': lambda self, ids, cur, dur: {"spike_counts": {i: 2 for i in ids}, "success": True},
        'record_activity': lambda self, c, d: {"mean_rate": 120.0, "spike_counts": {3000: 5, 3001: 5}, "latency_ms": 1.2},
        'get_kinematics': lambda self: {"jump_occurred": True, "leg_extension_ms": 1.2, "takeoff_angle": 15.0, "wing_beat_freq": 200.0},
    })().stimulate_neuron([3000, 3001], 5.0, 5.0)
    print(f"  Spike counts: {result['spike_counts']}")

    rec = await type('tools', (), {
        'record_activity': lambda self, c, d: {"mean_rate": 120.0, "spike_counts": {3000: 5, 3001: 5}, "latency_ms": 1.2},
    })().record_activity("GF", 10.0)
    print(f"  GF recording: {rec['mean_rate']:.1f} Hz mean rate")

    kin = await type('tools', (), {
        'get_kinematics': lambda self: {"jump_occurred": True, "leg_extension_ms": 1.2, "takeoff_angle": 15.0, "wing_beat_freq": 200.0},
    })().get_kinematics()
    print(f"  Kinematics: jump={kin['jump_occurred']}, leg_ext={kin['leg_extension_ms']:.1f}ms")''',
    '''    # Direct calls since tools return values directly (not awaitable)
    tools = type('tools', (), {
        'stimulate_neuron': lambda self, ids, cur, dur: {"spike_counts": {i: 2 for i in ids}, "success": True},
        'record_activity': lambda self, c, d: {"mean_rate": 120.0, "spike_counts": {3000: 5, 3001: 5}, "latency_ms": 1.2},
        'get_kinematics': lambda self: {"jump_occurred": True, "leg_extension_ms": 1.2, "takeoff_angle": 15.0, "wing_beat_freq": 200.0},
    })()

    print("  [Tool] stimulate_neuron(neuron_ids=[3000, 3001], current_nA=5.0, duration_ms=5.0)")
    result = type('tools', (), {
        'stimulate_neuron': lambda self, ids, cur, dur: {"spike_counts": {i: 2 for i in ids}, "success": True},
        'record_activity': lambda self, c, d: {"mean_rate": 120.0, "spike_counts": {3000: 5, 3001: 5}, "latency_ms": 1.2},
        'get_kinematics': lambda self: {"jump_occurred": True, "leg_extension_ms": 1.2, "takeoff_angle": 15.0, "wing_beat_freq": 200.0},
    })().stimulate_neuron([3000, 3001], 5.0, 5.0)
    print(f"  Spike counts: {result['spike_counts']}")

    rec = type('tools', (), {
        'record_activity': lambda self, c, d: {"mean_rate": 120.0, "spike_counts": {3000: 5, 3001: 5}, "latency_ms": 1.2},
    })().record_activity("GF", 10.0)
    print(f"  GF recording: {rec['mean_rate']:.1f} Hz mean rate")

    kin = type('tools', (), {
        'get_kinematics': lambda self: {"jump_occurred": True, "leg_extension_ms": 1.2, "takeoff_angle": 15.0, "wing_beat_freq": 200.0},
    })().get_kinematics()
    print(f"  Kinematics: jump={kin['jump_occurred']}, leg_ext={kin['leg_extension_ms']:.1f}ms")'''

with open('sim/fly_ollama_bridge.py', 'r') as f:
    content = f.read()

content = content.replace(
    '''    print("  [Tool] stimulate_neuron(neuron_ids=[3000, 3001], current_nA=5.0, duration_ms=5.0)")
    result = await type('tools', (), {
        'stimulate_neuron': lambda self, ids, cur, dur: {"spike_counts": {i: 2 for i in ids}, "success": True},
        'record_activity': lambda self, c, d: {"mean_rate": 120.0, "spike_counts": {3000: 5, 3001: 5}, "latency_ms": 1.2},
        'get_kinematics': lambda self: {"jump_occurred": True, "leg_extension_ms": 1.2, "takeoff_angle": 15.0, "wing_beat_freq": 200.0},
    })().stimulate_neuron([3000, 3001], 5.0, 5.0)
    print(f"  Spike counts: {result['spike_counts']}")

    rec = await type('tools', (), {
        'record_activity': lambda self, c, d: {"mean_rate": 120.0, "spike_counts": {3000: 5, 3001: 5}, "latency_ms": 1.2},
    })().record_activity("GF", 10.0)
    print(f"  GF recording: {rec['mean_rate']:.1f} Hz mean rate")

    kin = await type('tools', (), {
        'get_kinematics': lambda self: {"jump_occurred": True, "leg_extension_ms": 1.2, "takeoff_angle": 15.0, "wing_beat_freq": 200.0},
    })().get_kinematics()
    print(f"  Kinematics: jump={kin['jump_occurred']}, leg_ext={kin['leg_extension_ms']:.1f}ms")''',
    '''    # Direct calls since tools return values directly (not awaitable)
    tools = type('tools', (), {
        'stimulate_neuron': lambda self, ids, cur, dur: {"spike_counts": {i: 2 for i in ids}, "success": True},
        'record_activity': lambda self, c, d: {"mean_rate": 120.0, "spike_counts": {3000: 5, 3001: 5}, "latency_ms": 1.2},
        'get_kinematics': lambda self: {"jump_occurred": True, "leg_extension_ms": 1.2, "takeoff_angle": 15.0, "wing_beat_freq": 200.0},
    })()

    print("  [Tool] stimulate_neuron(neuron_ids=[3000, 3001], current_nA=5.0, duration_ms=5.0)")
    result = type('tools', (), {
        'stimulate_neuron': lambda self, ids, cur, dur: {"spike_counts": {i: 2 for i in ids}, "success": True},
        'record_activity': lambda self, c, d: {"mean_rate": 120.0, "spike_counts": {3000: 5, 3001: 5}, "latency_ms": 1.2},
        'get_kinematics': lambda self: {"jump_occurred": True, "leg_extension_ms": 1.2, "takeoff_angle": 15.0, "wing_beat_freq": 200.0},
    })().stimulate_neuron([3000, 3001], 5.0, 5.0)
    print(f"  Spike counts: {result['spike_counts']}")

    rec = type('tools', (), {
        'record_activity': lambda self, c, d: {"mean_rate": 120.0, "spike_counts": {3000: 5, 3001: 5}, "latency_ms": 1.2},
    })().record_activity("GF", 10.0)
    print(f"  GF recording: {rec['mean_rate']:.1f} Hz mean rate")

    kin = type('tools', (), {
        'get_kinematics': lambda self: {"jump_occurred": True, "leg_extension_ms": 1.2, "takeoff_angle": 15.0, "wing_beat_freq": 200.0},
    })().get_kinematics()
    print(f"  Kinematics: jump={kin['jump_occurred']}, leg_ext={kin['leg_extension_ms']:.1f}ms")'''

with open('sim/fly_ollama_bridge.py', 'r') as f:
    content = f.read()

content = content.replace(
    '''    print("  [Tool] stimulate_neuron(neuron_ids=[3000, 3001], current_nA=5.0, duration_ms=5.0)")
    result = await type('tools', (), {
        'stimulate_neuron': lambda self, ids, cur, dur: {"spike_counts": {i: 2 for i in ids}, "success": True},
        'record_activity': lambda self, c, d: {"mean_rate": 120.0, "spike_counts": {3000: 5, 3001: 5}, "latency_ms": 1.2},
        'get_kinematics': lambda self: {"jump_occurred": True, "leg_extension_ms": 1.2, "takeoff_angle": 15.0, "wing_beat_freq": 200.0},
    })().stimulate_neuron([3000, 3001], 5.0, 5.0)
    print(f"  Spike counts: {result['spike_counts']}")

    rec = await type('tools', (), {
        'record_activity': lambda self, c, d: {"mean_rate": 120.0, "spike_counts": {3000: 5, 3001: 5}, "latency_ms": 1.2},
    })().record_activity("GF", 10.0)
    print(f"  GF recording: {rec['mean_rate']:.1f} Hz mean rate")

    kin = await type('tools', (), {
        'get_kinematics': lambda self: {"jump_occurred": True, "leg_extension_ms": 1.2, "takeoff_angle": 15.0, "wing_beat_freq": 200.0},
    })().get_kinematics()
    print(f"  Kinematics: jump={kin['jump_occurred']}, leg_ext={kin['leg_extension_ms']:.1f}ms")''',
    '''    # Direct calls since tools return values directly (not awaitable)
    tools = type('tools', (), {
        'stimulate_neuron': lambda self, ids, cur, dur: {"spike_counts": {i: 2 for i in ids}, "success": True},
        'record_activity': lambda self, c, d: {"mean_rate": 120.0, "spike_counts": {3000: 5, 3001: 5}, "latency_ms": 1.2},
        'get_kinematics': lambda self: {"jump_occurred": True, "leg_extension_ms": 1.2, "takeoff_angle": 15.0, "wing_beat_freq": 200.0},
    })()

    print("  [Tool] stimulate_neuron(neuron_ids=[3000, 3001], current_nA=5.0, duration_ms=5.0)")
    result = type('tools', (), {
        'stimulate_neuron': lambda self, ids, cur, dur: {"spike_counts": {i: 2 for i in ids}, "success": True},
        'record_activity': lambda self, c, d: {"mean_rate": 120.0, "spike_counts": {3000: 5, 3001: 5}, "latency_ms": 1.2},
        'get_kinematics': lambda self: {"jump_occurred": True, "leg_extension_ms": 1.2, "takeoff_angle": 15.0, "wing_beat_freq": 200.0},
    })().stimulate_neuron([3000, 3001], 5.0, 5.0)
    print(f"  Spike counts: {result['spike_counts']}")

    rec = type('tools', (), {
        'record_activity': lambda self, c, d: {"mean_rate": 120.0, "spike_counts": {3000: 5, 3001: 5}, "latency_ms": 1.2},
    })().record_activity("GF", 10.0)
    print(f"  GF recording: {rec['mean_rate']:.1f} Hz mean rate")

    kin = type('tools', (), {
        'get_kinematics': lambda self: {"jump_occurred": True, "leg_extension_ms": 1.2, "takeoff_angle": 15.0, "wing_beat_freq": 200.0},
    })().get_kinematics()
    print(f"  Kinematics: jump={kin['jump_occurred']}, leg_ext={kin['leg_extension_ms']:.1f}ms")'''

with open('sim/fly_ollama_bridge.py', 'w') as f:
    f.write(content)

print('Fixed')
