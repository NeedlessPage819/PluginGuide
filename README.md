# Sparkline Plugin Development Guide

A comprehensive guide for creating plugins for the Sparkline application using the enhanced PluginLoader system.

## Table of Contents

- [Overview](#overview)
- [Plugin Structure](#plugin-structure)
- [Core Methods](#core-methods)
- [Optional Methods](#optional-methods)
- [Conditional Methods](#conditional-methods)
- [Plugin State Management](#plugin-state-management)
- [Installation and Reloading](#installation-and-reloading)
- [Logging](#logging)
- [Dependencies](#dependencies)
- [GUI Interaction](#gui-interaction)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [API Reference Quick Links](#api-reference-quick-links)

## Overview

The PluginLoader system allows you to extend the Sparkline application with custom functionality through dynamically loaded Python plugins. Plugins can:

-   Observe and react to game state via `GameTickPacket` and `FieldInfoPacket`.
-   Inject `SimpleControllerState` objects to control the player's car. Multiple plugins can contribute controller states.
-   Filter `SimpleControllerState` objects from other sources (including other plugins or the main bot) before they are sent to the game.
-   Execute conditional logic based on specific game events or states using the `@condition` decorator.
-   Run background tasks in separate threads.
-   Be enabled/disabled via the Sparkline GUI.

## Plugin Structure

### Basic Plugin Template

```python
# plugins/my_example_plugin.py

# If you have RLBot installed, you can import SimpleControllerState:
# from rlbot.agents.base_agent import SimpleControllerState
# Otherwise, ensure your controller state object is compatible.
# For this example, we'll assume a compatible SimpleControllerState is available.
# A basic compatible class could be:
class SimpleControllerState:
    def __init__(self, steer=0.0, throttle=0.0, pitch=0.0, yaw=0.0, roll=0.0, jump=False, boost=False, handbrake=False, use_item=False):
        self.steer = steer
        self.throttle = throttle
        self.pitch = pitch
        self.yaw = yaw
        self.roll = roll
        self.jump = jump
        self.boost = boost
        self.handbrake = handbrake
        self.use_item = use_item

class MyExamplePlugin:
    def __init__(self, ConsoleLogger=None):
        """
        Initialize your plugin.
        ConsoleLogger: A function to log messages to the main application's console.
        """
        self.logger = ConsoleLogger or print  # Use provided logger or fallback to print
        self.Name = "My Example Plugin"      # Static name
        # Or, for a dynamic name:
        # self.Name = lambda: f"My Dynamic Plugin v1.{self.some_version}"
        self.enabled = True                  # Controls if the plugin is active

        self.logger(f"[{self.Name}] __init__ called.")

    def initialize(self):
        """
        Called once when the plugin system initializes all loaded plugins,
        or when plugins are reloaded.
        """
        self.logger(f"[{self.Name}] initialize called.")
        # Perform one-time setup tasks here

    def game_tick_packet_set(self, packet, local_player_index, playername, field_info):
        """
        Called every game tick with the current game state.
        - packet: The GameTickPacket (CTypes struct).
        - local_player_index: Index of the bot-controlled player in packet.game_cars.
        - playername: Name of the bot-controlled player.
        - field_info: The FieldInfoPacket (CTypes struct), usually static for the map.

        Return a SimpleControllerState to inject controls, or None to not inject.
        Multiple plugins can return controller states; they will all be processed.
        """
        if not self.enabled:
            return None

        # Example: Log ball position
        # self.logger(f"[{self.Name}] Ball at: ({packet.game_ball.physics.location.x:.0f}, {packet.game_ball.physics.location.y:.0f})")

        # Example: Simple jump on kickoff
        if packet.game_info.is_kickoff_pause and packet.game_cars[local_player_index].physics.location.z < 100:
            controller = SimpleControllerState()
            controller.jump = True
            # self.logger(f"[{self.Name}] Sending jump for kickoff.")
            return controller # This controller state will be added to the list of inputs to write

        return None # No controller state to inject this tick

    def controller_filter(self, controller: SimpleControllerState) -> SimpleControllerState:
        """
        Called for *each* SimpleControllerState that is about to be written to memory.
        This includes states from the main bot and other plugins.
        Modify the 'controller' object in-place or return a new one.
        If you return None, the original controller (possibly modified in-place) is used.
        """
        if not self.enabled:
            return controller

        # Example: Prevent boosting if throttle is negative
        if controller.throttle < 0 and controller.boost:
            self.logger(f"[{self.Name}] Filter: Disabling boost while reversing.")
            controller.boost = False
        return controller # Return the (potentially modified) controller

    @condition("packet.game_ball.physics.location.z > 1500 and packet.game_cars[local_player_index].physics.location.z < 100")
    def on_high_ball_and_grounded(self, packet, local_player_index, playername):
        """
        This method is called only when the ball is very high AND the player is on the ground.
        The @condition decorator is provided by the PluginLoader.
        Parameters are automatically injected based on the method signature.
        """
        if not self.enabled:
            return

        self.logger(f"[{self.Name}] Conditional: High ball detected while {playername} is grounded!")
        # Potential logic: print a message, trigger a quick chat, etc.

    def on_game_event_started(self, event):
        """Called when a new game event (match) starts."""
        self.logger(f"[{self.Name}] Game event started.")

    def on_game_event_destroyed(self, event):
        """Called when a game event (match) ends."""
        self.logger(f"[{self.Name}] Game event destroyed.")

    def main(self):
        """
        If this method exists, it will be run in a separate daemon thread.
        Useful for long-running background tasks.
        """
        import time
        self.logger(f"[{self.Name}] Main thread started.")
        counter = 0
        while self.enabled: # Check self.enabled to allow thread to exit gracefully
            # self.logger(f"[{self.Name}] Background task running... ({counter})")
            counter += 1
            time.sleep(10) # Example: Perform a task every 10 seconds
        self.logger(f"[{self.Name}] Main thread finishing.")


    def shutdown(self):
        """
        Called when plugins are being shut down (e.g., on reload or bot exit).
        Perform cleanup tasks here.
        """
        self.enabled = False # Important for background threads to terminate
        self.logger(f"[{self.Name}] shutdown called.")
```

### File Structure

Place your plugin files (e.g., `my_plugin.py`) in the `plugins/` directory relative to the Sparkline executable.

```
(Sparkline executable directory)/
├── plugins/
│   ├── my_example_plugin.py
│   └── another_plugin.py
└── Sparkline.exe
```

## Core Methods

### `__init__(self, ConsoleLogger=None)`

-   **Purpose**: Constructor for your plugin. Called when the plugin module is loaded.
-   **Parameters**:
    -   `ConsoleLogger`: A function provided by the PluginLoader for logging messages to the main application's console. It's recommended to store and use this (e.g., `self.logger = ConsoleLogger or print`).
-   **Initialization**:
    -   Set `self.Name`: This attribute is used by the PluginLoader and GUI to display your plugin's name. It can be a static string (e.g., `self.Name = "My Plugin"`) or a lambda/callable (e.g., `self.Name = lambda: "My Dynamic Plugin"`).
    -   Set `self.enabled = True` (or `False`): Determines if your plugin's main logic should run. This can be toggled by the GUI.
    -   Initialize any other internal state your plugin requires.

### `game_tick_packet_set(self, packet, local_player_index, playername, field_info)`

-   **Purpose**: This is the primary method called by the PluginLoader every game tick, providing current game state.
-   **Parameters**:
    -   `packet`: An instance of `GameTickPacket` (a CTypes structure) containing dynamic data about cars, ball, game info, etc.
    -   `local_player_index`: The index of the player car controlled by Sparkline within `packet.game_cars`.
    -   `playername`: The name of the Sparkline-controlled player.
    -   `field_info`: An instance of `FieldInfoPacket` (a CTypes structure) containing static data about the map, like boost pad locations and goal dimensions.
-   **Return Value**:
    -   `SimpleControllerState` object: If you want to inject controls for the car, return a populated `SimpleControllerState` object. This state will be added to a list of controller inputs to be processed.
    -   `None`: If your plugin does not want to inject controls for this tick.
-   **Behavior**: The PluginLoader collects `SimpleControllerState` objects returned by *all* active plugins (and the main bot, if applicable). Each of these controller states will then be passed through the `controller_filter` method of all active plugins before being written to game memory.

## Optional Methods

### `initialize(self)`

-   **Purpose**: Called once after all plugins have been loaded and their `__init__` methods have run. Also called after a plugin reload.
-   **Use Cases**: Perform one-time setup tasks that might depend on the initial environment or other plugins (though direct inter-plugin dependency is not formally managed by the loader).

### `shutdown(self)`

-   **Purpose**: Called when the plugin system is shutting down, either due to a plugin reload or the application closing.
-   **Use Cases**: Perform cleanup tasks, save state, release resources. If you have a `main` background thread, ensure it can terminate gracefully (e.g., by checking `self.enabled`).

### `main(self)`

-   **Purpose**: If this method is defined, the PluginLoader will execute it in a new daemon thread.
-   **Use Cases**: For long-running background tasks, periodic checks, or operations that should not block the main game tick processing (e.g., communicating with an external API, complex calculations).
-   **Note**: Ensure your `main` method respects the `self.enabled` flag to allow for graceful termination when the plugin is disabled or shut down.

### `controller_filter(self, controller: SimpleControllerState) -> SimpleControllerState`

-   **Purpose**: Allows your plugin to inspect and potentially modify any `SimpleControllerState` object that is about to be written to the game's memory. This includes controller states originating from the main Sparkline bot, other plugins, or even a previous `game_tick_packet_set` call from your own plugin.
-   **Parameters**:
    -   `controller`: The `SimpleControllerState` object to be filtered.
-   **Return Value**:
    -   The (potentially modified) `SimpleControllerState` object. You can modify the passed `controller` in-place and return it, or create and return a new `SimpleControllerState` instance.
    -   If you return `None`, the original controller object (possibly modified in-place) will be used.
-   **Behavior**: This method is called sequentially for each `SimpleControllerState` in the list gathered from all sources before it's written.

### `on_game_event_started(self, event)`

-   **Purpose**: Called when the Sparkline SDK fires an `EventTypes.ON_GAME_EVENT_STARTED` event, typically signaling the beginning of a match or game session.
-   **Parameters**:
    -   `event`: The event data object associated with the game event start (currently `EventGameEventStarted`, which is a simple marker).
-   **Use Cases**: Resetting match-specific state, logging match start.

### `on_game_event_destroyed(self, event)`

-   **Purpose**: Called when the Sparkline SDK fires an `EventTypes.ON_GAME_EVENT_DESTROYED` event, typically signaling the end of a match or game session.
-   **Parameters**:
    -   `event`: The event data object associated with the game event destruction (currently `EventGameEventDestroyed`).
-   **Use Cases**: Finalizing match statistics, logging match end.

## Conditional Methods

You can define methods that are only called when a specific Python expression (evaluated against the game state) is true. This is achieved using the `@condition` decorator, which is automatically made available in your plugin's module scope by the PluginLoader.

```python
@condition("packet.game_info.is_kickoff_pause")
def handle_kickoff_logic(self, packet, local_player_index, playername):
    # This code only runs if packet.game_info.is_kickoff_pause is True
    self.logger(f"[{self.Name}] Kickoff logic for {playername}!")

@condition("packet.game_ball.physics.location.z > 300 and packet.game_cars[local_player_index].boost < 20")
def low_boost_high_ball_alert(self, packet, local_player_index):
    # Runs when ball is high and player has low boost
    self.logger(f"[{self.Name}] Alert: Ball is high, and player {local_player_index} has low boost!")
```

-   **Decorator**: `@condition("your_python_expression_as_string")`
-   **Evaluation Context**: The expression string is evaluated with access to:
    -   `packet`: The current `GameTickPacket`.
    -   `local_player_index`: Index of the Sparkline-controlled player.
    -   `playername`: Name of the Sparkline-controlled player.
    -   `field_info`: The `FieldInfoPacket`.
    -   `process_id`: The game process ID (may be `None`).
    -   Standard Python built-ins like `True`, `False`, `None`, `abs()`, `min()`, `max()`, `round()`, `len()`.
-   **Method Parameters**: The PluginLoader inspects the signature of your decorated method. You can define parameters for any of the context variables listed above (e.g., `def my_method(self, packet, field_info):`). Only the requested parameters will be passed.
-   **Execution**: If the condition evaluates to `True`, your method will be called during the plugin ticking phase.

## Plugin State Management

### `self.enabled`

-   Each plugin instance typically has an `self.enabled` boolean attribute.
-   It's good practice to check `if not self.enabled: return` at the beginning of your tick-based methods (`game_tick_packet_set`, `controller_filter`, conditional methods) and in loops within your `main` thread to allow the plugin to be gracefully paused or stopped.
-   The Sparkline GUI provides checkboxes to toggle this `enabled` state for each loaded plugin.

## Installation and Reloading

1.  **Create Plugin File**: Write your plugin code in a Python file (e.g., `my_plugin.py`).
2.  **Place in `plugins/` Directory**: Put this file into the `plugins` folder located in the same directory as the Sparkline executable.
3.  **Start Sparkline**: Launch Sparkline. The PluginLoader will automatically attempt to load all valid `.py` files from the `plugins/` directory.
4.  **Reloading**: The Sparkline GUI has a "RELOAD" button in the "PLUGINS" section. Clicking this will:
    1.  Call the `shutdown()` method of all currently loaded plugins.
    2.  Unload the plugin modules.
    3.  Re-scan the `plugins/` directory and load all valid plugin files.
    4.  Call `__init__()` and then `initialize()` for all newly loaded plugins.

## Logging

-   The `ConsoleLogger` function passed to your plugin's `__init__` method should be used for logging.
-   Example: `self.logger(f"[{self.Name}] An important event occurred.")`
-   This ensures your plugin's messages are displayed in the main Sparkline console output.

## Dependencies

-   If your plugin requires external Python packages (e.g., `numpy`, `requests`), these packages must be installed in the Python environment that Sparkline is using.
-   The PluginLoader includes an advanced mechanism for Windows to attempt to find common Python `site-packages` directories (especially for Python 3.11, but also others) and add them to `sys.path`. This improves the chances of your plugin finding its dependencies if they are installed in a standard Python installation, even if Sparkline is run from a bundled executable.
-   However, for maximum reliability, especially if distributing your plugin or Sparkline, consider bundling dependencies or instructing users on how to install them into the correct environment.

## GUI Interaction

-   **Plugin List**: Loaded plugins are listed in the "PLUGINS" section of the Sparkline GUI. The name displayed is taken from your plugin's `self.Name` attribute.
-   **Enable/Disable**: Each plugin in the list has a checkbox. Toggling this checkbox directly sets the `self.enabled` attribute of your plugin instance. Your plugin code should respect this flag.

## Best Practices

1.  **Error Handling**: Wrap potentially problematic code in `try...except` blocks, especially in methods called frequently like `game_tick_packet_set` and `controller_filter`. Log errors using `self.logger`.
    ```python
    try:
        # Risky operation
        value = packet.game_cars[some_index].boost
    except IndexError:
        self.logger(f"[{self.Name}] Error: Car index out of bounds.")
        return None # Or handle appropriately
    except Exception as e:
        self.logger(f"[{self.Name}] Unexpected error: {e}")
        return None
    ```
2.  **Performance**:
    -   `game_tick_packet_set` and `controller_filter` are called very frequently (up to 120 times per second). Keep them efficient.
    -   Offload heavy computations or I/O operations to conditional methods (if they don't need to run every tick) or to the `main()` background thread.
3.  **Statefulness**: Be mindful of state. If your plugin needs to remember information between ticks, store it in `self` attributes. Initialize these in `__init__` or `initialize`. Reset match-specific state in `on_game_event_started`.
4.  **Resource Management**: If your plugin opens files, network connections, or other resources, ensure they are properly closed in the `shutdown()` method.
5.  **Idempotency**: Where applicable, design operations to be safe if called multiple times with the same state.
6.  **Clear Logging**: Use `self.logger` with informative messages, including your plugin's name, to aid in debugging.
7.  **Respect `self.enabled`**: Always check `self.enabled` in recurring methods and loops to allow your plugin to be cleanly disabled or shut down.

## Troubleshooting

-   **Plugin Not Loading**:
    -   Verify the file is a `.py` file directly in the `plugins/` folder.
    -   Ensure the filename doesn't start with `__`.
    -   Check the console for Python syntax errors or import errors from your plugin file.
    -   Make sure your plugin class has an `__init__` method and a `game_tick_packet_set` method.
-   **`ModuleNotFoundError`**:
    -   The required package is not installed in the Python environment Sparkline uses.
    -   If on Windows, the PluginLoader's path detection might not have found the correct `site-packages`. Try installing the dependency into the Python version Sparkline is most likely using (e.g., system Python 3.11).
-   **Plugin Logic Not Working**:
    -   Add extensive logging with `self.logger` at various points in your code to trace execution and variable values.
    -   Simplify your logic: test small pieces individually.
    -   Double-check the CTypes structure definitions if you are manually interpreting byte offsets (though direct access to `packet.field.subfield` is preferred).
-   **Conditional Methods Not Firing**:
    -   Verify the Python expression in the `@condition("...")` string is correct.
    -   Test the expression manually with sample `packet` data if possible.
    -   Ensure variable names in the expression match those available in the context (`packet`, `local_player_index`, etc.).
-   **GUI Issues**:
    -   If your plugin's `self.Name` is not a string or a callable returning a string, it might not display correctly.
    -   If the enable/disable checkbox doesn't work, ensure your plugin code checks `self.enabled`.

## API Reference Quick Links

(Refer to the CTypes structure definitions in `Sparkline.py` for full details on structures like `Vector3`, `Rotator`, `Physics`, etc.)

### `GameTickPacket` (`packet`)

-   `packet.game_cars`: Array of `PlayerInfo` structs (up to `MAX_PLAYERS`).
    -   `packet.game_cars[i].physics`: `Physics` struct (location, rotation, velocity, angular_velocity). All fields populated.
    -   `packet.game_cars[i].score_info`: `ScoreInfo` struct.
        -   `.score`: Populated.
        -   Other fields like `.goals`, `.assists`, etc., will be default (0) unless `generate_game_tick_packet` is updated to populate them.
    -   `packet.game_cars[i].is_demolished`: Boolean (Note: Not populated by the provided `generate_game_tick_packet` function; will be default `False`).
    -   `packet.game_cars[i].has_wheel_contact`: Boolean. Populated (derived from `car.is_on_ground()`).
    -   `packet.game_cars[i].is_super_sonic`: Boolean. Populated.
    -   `packet.game_cars[i].is_bot`: Boolean (Note: Not populated by `generate_game_tick_packet`; will be default `False`).
    -   `packet.game_cars[i].jumped`: Boolean. Populated.
    -   `packet.game_cars[i].double_jumped`: Boolean. Populated.
    -   `packet.game_cars[i].name`: Player name (wchar array). Populated.
    -   `packet.game_cars[i].team`: Team index (ubyte). Populated.
    -   `packet.game_cars[i].boost`: Boost amount (int, 0-100). Populated.
    -   `packet.game_cars[i].hitbox`: `BoxShape` struct (Note: Not populated by `generate_game_tick_packet`; will contain default/zero values).
    -   `packet.game_cars[i].hitbox_offset`: `Vector3` struct (Note: Not populated by `generate_game_tick_packet`; will contain default/zero values).
    -   `packet.game_cars[i].spawn_id`: Integer (Note: Not populated by `generate_game_tick_packet`; will be default `0`).
-   `packet.num_cars`: Number of active cars. Populated.
-   `packet.game_boosts`: Array of `BoostPadState` structs (up to `MAX_BOOSTS`).
    -   `packet.game_boosts[i].is_active`: Boolean. Populated.
    -   `packet.game_boosts[i].timer`: Float, time until respawn if inactive. Populated.
-   `packet.num_boost`: Number of boost pads in `game_boosts`. Populated.
-   `packet.game_ball`: `BallInfo` struct.
    -   `packet.game_ball.physics`: `Physics` struct. All fields populated.
    -   `packet.game_ball.latest_touch`: `Touch` struct (Note: Not populated by `generate_game_tick_packet`; will contain default values).
    -   `packet.game_ball.drop_shot_info`: `DropShotInfo` struct (Note: Not populated by `generate_game_tick_packet`; will contain default values).
    -   `packet.game_ball.collision_shape`: `CollisionShape` struct (Note: Not populated by `generate_game_tick_packet`; will contain default values).
-   `packet.game_info`: `GameInfo` struct.
    -   `.seconds_elapsed`, `.game_time_remaining`, `.is_overtime`, `.is_unlimited_time`, `.is_round_active`, `.is_kickoff_pause`, `.is_match_ended`, `.frame_num`, `.game_speed`, `.world_gravity_z`. All fields populated.
-   `packet.teams`: Array of `TeamInfo` structs (up to `MAX_TEAMS`).
    -   `packet.teams[i].team_index`, `.score`. Populated.
-   `packet.num_teams`: Number of active teams. Populated.
-   `packet.dropshot_tiles`: Array of `TileInfo` structs (Note: Not populated by `generate_game_tick_packet`; will contain default values).
-   `packet.num_tiles`: Integer (Note: Not populated by `generate_game_tick_packet`; will be default `0`).


### `FieldInfoPacket` (`field_info`)

(Populated by `set_field_info` method)
-   `field_info.boost_pads`: Array of `BoostPad` structs (up to `MAX_BOOSTS`).
    -   `field_info.boost_pads[i].location`: `Vector3`. Populated.
    -   `field_info.boost_pads[i].is_full_boost`: Boolean. Populated.
-   `field_info.num_boosts`: Number of boost pads. Populated.
-   `field_info.goals`: Array of `GoalInfo` structs (up to `MAX_GOALS`).
    -   `field_info.goals[i].team_num`, `.location` (Vector3), `.direction` (Vector3), `.width`, `.height`. Populated.
-   `field_info.num_goals`: Number of goals. Populated.

### `SimpleControllerState` (`controller`)

(Assuming compatibility with `rlbot.agents.base_agent.SimpleControllerState`)
-   `controller.throttle`: Float (-1.0 to 1.0)
-   `controller.steer`: Float (-1.0 to 1.0)
-   `controller.pitch`: Float (-1.0 to 1.0)
-   `controller.yaw`: Float (-1.0 to 1.0)
-   `controller.roll`: Float (-1.0 to 1.0)
-   `controller.jump`: Boolean
-   `controller.boost`: Boolean
-   `controller.handbrake`: Boolean
-   `controller.use_item`: Boolean (for rumble items, typically unused in standard modes)

Happy plugin development! 🚀

---
