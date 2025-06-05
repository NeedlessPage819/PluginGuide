# Plugin Development Guide

A comprehensive guide for creating plugins for the RLBot application using the PluginLoader system.

## Table of Contents

- [Overview](#overview)
- [Plugin Structure](#plugin-structure)
- [Required Methods](#required-methods)
- [Optional Methods](#optional-methods)
- [Conditional Methods](#conditional-methods)

- [Installation](#installation)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

The PluginLoader system allows you to extend the RLBot application with custom functionality through dynamically loaded Python plugins. Plugins can:

- Override bot controller states
- Filter controller inputs
- Execute conditional logic based on game state
- Run background threads for continuous operations
- Access game packet data and player information

## Plugin Structure

### Basic Plugin Template

```python
class MyPlugin:
    def __init__(self, ConsoleLogger=None):
        """
        Initialize your plugin
        ConsoleLogger: Function to log messages to the main application
        """
        self.logger = ConsoleLogger or print
        self.Name = lambda: "My Plugin Name"  # Plugin display name
    
    def initialize(self):
        """Called once when the plugin system initializes"""
        self.logger("MyPlugin initialized!")
    
    def game_tick_packet_set(self, packet, local_player_index, playername):
        """
        Called every game tick with game state data
        Return a SimpleControllerState to override bot controls, or None to pass through
        """
        # Your plugin logic here
        return None  # Don't override controller
    
    def shutdown(self):
        """Called when the plugin system shuts down"""
        self.logger("MyPlugin shutting down!")
```

### File Structure

```
plugins/
├── my_plugin.py          # Your plugin file
├── another_plugin.py     # Another plugin
└── __pycache__/          # Auto-generated, ignore
```

## Required Methods

### `__init__(self, ConsoleLogger=None)`

**Purpose**: Initialize your plugin instance

**Parameters**:
- `ConsoleLogger`: Function to log messages (defaults to `print` if not provided)

**Example**:
```python
def __init__(self, ConsoleLogger=None):
    self.logger = ConsoleLogger or print
    self.Name = lambda: "My Awesome Plugin"
    self.some_setting = True
```

### `game_tick_packet_set(self, packet, local_player_index, playername)`

**Purpose**: Main plugin entry point called every game tick

**Parameters**:
- `packet`: GameTickPacket containing all game state information
- `local_player_index`: Index of the local player (usually 0)
- `playername`: Name of the player

**Return Value**:
- `SimpleControllerState`: Override bot controls
- `None`: Pass through without modification

**Example**:
```python
def game_tick_packet_set(self, packet, local_player_index, playername):
    player = packet.game_cars[local_player_index]
    
    # Example: Stop the bot if it's going too fast
    if player.physics.velocity.length() > 2000:
        from rlbot.agents.base_agent import SimpleControllerState
        controller = SimpleControllerState()
        controller.throttle = 0
        controller.brake = 1
        return controller
    
    return None  # Don't override
```

## Optional Methods

### `initialize(self)`

Called once when the plugin system starts up. Use for one-time setup.

```python
def initialize(self):
    self.logger("Plugin starting up!")
    self.setup_data_structures()
```

### `shutdown(self)`

Called when the plugin system shuts down. Use for cleanup.

```python
def shutdown(self):
    self.logger("Plugin shutting down!")
    self.save_data_to_file()
```

### `main(self)`

If present, runs in a separate daemon thread. Use for background operations.

```python
def main(self):
    import time
    while True:
        self.logger("Background task running...")
        time.sleep(5)
```

### `controller_filter(self, controller)`

Filter/modify controller inputs from other sources.

**Parameters**:
- `controller`: SimpleControllerState to potentially modify

**Return Value**:
- `SimpleControllerState`: Modified controller
- `None`: Controller was modified in-place or no changes

```python
def controller_filter(self, controller):
    # Example: Limit maximum throttle
    if controller.throttle > 0.8:
        controller.throttle = 0.8
    return controller
```

## Conditional Methods

Use the `@condition` decorator to create methods that only execute when specific conditions are met:

```python
@condition("packet.game_info.is_kickoff_pause")
def on_kickoff(self, packet, local_player_index, playername):
    """This method only runs during kickoff"""
    self.logger("Kickoff detected!")

@condition("packet.game_cars[local_player_index].has_wheel_contact == False")
def on_aerial(self, packet, local_player_index):
    """This method runs when the bot is airborne"""
    self.logger("Bot is in the air!")

@condition("packet.game_ball.physics.location.z > 200")
def on_high_ball(self, packet):
    """This method runs when the ball is high"""
    self.logger("Ball is high up!")
```

### Available Variables in Conditions

- `packet`: The GameTickPacket
- `local_player_index`: Player index
- `playername`: Player name
- `process_id`: Process ID (if available)
- Standard Python builtins: `True`, `False`, `None`, `abs`, `min`, `max`, `round`, `len`

## Installation

1. **Create your plugin file**: Save your plugin as a `.py` file in the `plugins/` directory
2. **Name your plugin class**: Ensure your class has the required methods
3. **Test your plugin**: Run the application and check the logs for your plugin loading
4. **Debug if needed**: Check the console output for any error messages

### Plugin File Naming

- ✅ `my_plugin.py` - Good
- ✅ `speed_monitor.py` - Good  
- ❌ `__init__.py` - Ignored (starts with `__`)
- ❌ `plugin.txt` - Ignored (not `.py` file)

## Best Practices

### 1. Error Handling

Always wrap potentially failing code in try-catch blocks:

```python
def game_tick_packet_set(self, packet, local_player_index, playername):
    try:
        # Your plugin logic here
        player = packet.game_cars[local_player_index]
        # ... do something with player data
    except Exception as e:
        self.logger(f"Error in plugin: {e}")
    return None
```

### 2. Performance Considerations

- Keep `game_tick_packet_set` lightweight (it's called every tick)
- Use conditional methods for expensive operations
- Consider using background threads for heavy computations

```python
# Good: Lightweight check
def game_tick_packet_set(self, packet, local_player_index, playername):
    if packet.game_info.seconds_elapsed % 1.0 < 0.1:  # Once per second
        self.do_expensive_calculation()
    return None

# Better: Use conditional method
@condition("packet.game_info.seconds_elapsed % 1.0 < 0.1")
def periodic_check(self, packet):
    self.do_expensive_calculation()
```

### 3. Resource Management

Clean up resources in the `shutdown` method:

```python
def __init__(self, ConsoleLogger=None):
    self.logger = ConsoleLogger or print
    self.file_handle = open("plugin_data.txt", "w")

def shutdown(self):
    if self.file_handle:
        self.file_handle.close()
        self.logger("File closed successfully")
```

### 4. Logging Best Practices

Use descriptive log messages with your plugin name:

```python
def initialize(self):
    self.logger(f"[{self.Name()}] Plugin initialized successfully")

def game_tick_packet_set(self, packet, local_player_index, playername):
    if some_condition:
        self.logger(f"[{self.Name()}] Special condition detected at {packet.game_info.seconds_elapsed:.1f}s")
```

## Troubleshooting

### Common Issues

#### Plugin Not Loading

**Problem**: Plugin doesn't appear in logs
**Solutions**:
- Check file is in correct `plugins/` directory
- Ensure filename ends with `.py`
- Verify class has required `game_tick_packet_set` method
- Check console for import errors

#### Import Errors

**Problem**: `ModuleNotFoundError` in logs
**Solutions**:
- Install missing dependencies: `pip install package_name`
- Check if package is available in your Python environment
- For Windows: Plugin loader attempts to add common Python paths automatically

#### Plugin Crashes

**Problem**: Plugin causes application to crash
**Solutions**:
- Add try-catch blocks around your code
- Test with simple plugin first
- Check parameter types match expected values
- Verify return types are correct

#### Conditional Methods Not Running

**Problem**: `@condition` decorated methods never execute
**Solutions**:
- Verify condition string syntax is valid Python
- Test condition in Python console first
- Check available variables in condition context
- Add logging to verify plugin is loaded

### Debug Template

Use this template to debug issues:

```python
class DebugPlugin:
    def __init__(self, ConsoleLogger=None):
        self.logger = ConsoleLogger or print
        self.Name = lambda: "Debug Plugin"
        self.logger("DEBUG: Plugin __init__ called")
    
    def initialize(self):
        self.logger("DEBUG: Plugin initialize() called")
    
    def game_tick_packet_set(self, packet, local_player_index, playername):
        self.logger(f"DEBUG: Tick {packet.game_info.seconds_elapsed:.1f}s")
        return None
    
    @condition("True")  # Always true for testing
    def debug_condition(self, packet):
        self.logger("DEBUG: Conditional method working!")
    
    def shutdown(self):
        self.logger("DEBUG: Plugin shutdown() called")
```

### Getting Help

If you're still having issues:

1. Check the console logs for specific error messages
2. Test with a minimal plugin first
3. Verify your Python environment has required packages
4. Make sure you're using the correct parameter names and types

---

## API Reference Quick Links

### GameTickPacket Properties
- `packet.game_info` - Match information (time, score, etc.)
- `packet.game_cars[index]` - Player car data
- `packet.game_ball` - Ball physics and position
- `packet.game_boosts` - Boost pad states

### SimpleControllerState Properties
- `controller.throttle` - Forward/backward (-1 to 1)
- `controller.steer` - Left/right (-1 to 1)  
- `controller.pitch` - Nose up/down (-1 to 1)
- `controller.yaw` - Turn left/right (-1 to 1)
- `controller.roll` - Roll left/right (-1 to 1)
- `controller.jump` - Jump button (True/False)
- `controller.boost` - Boost button (True/False)
- `controller.handbrake` - Handbrake button (True/False)

Happy plugin development! 🚀
