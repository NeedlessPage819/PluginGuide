import time
import math

class BallTracker:
    def __init__(self, ConsoleLogger=None):
        """
        Initialize the Ball Tracker plugin
        This plugin tracks ball statistics and provides some basic game awareness
        """
        self.logger = ConsoleLogger or print
        self.Name = lambda: "Ball Tracker"
        
        # Plugin state variables
        self.ball_height_record = 0
        self.ball_speed_record = 0
        self.last_ball_touch_time = 0
        self.ball_possession_time = 0
        self.last_possession_player = None
        
        # Settings
        self.possession_distance = 150  # Distance to consider "possession"
        self.high_ball_threshold = 300  # Height threshold for "high ball"
        self.fast_ball_threshold = 1500  # Speed threshold for "fast ball"
        
        self.logger("Ball Tracker plugin initialized!")
    
    def initialize(self):
        """Called when the plugin system starts up"""
        self.logger("Ball Tracker: Starting ball analysis...")
        self.start_time = time.time()
    
    def game_tick_packet_set(self, packet, local_player_index, playername):
        """
        Main plugin method called every game tick
        Analyzes ball data and tracks statistics
        """
        try:
            ball = packet.game_ball
            
            # Update ball records
            self._update_ball_records(ball)
            
            # Track possession
            self._track_possession(packet, local_player_index)
            
            # Don't override controller - this is an analysis plugin
            return None
            
        except Exception as e:
            self.logger(f"Ball Tracker: Error in game_tick_packet_set: {e}")
            return None
    
    def _update_ball_records(self, ball):
        """Update ball height and speed records"""
        # Track highest ball
        ball_height = ball.physics.location.z
        if ball_height > self.ball_height_record:
            self.ball_height_record = ball_height
        
        # Track fastest ball
        velocity = ball.physics.velocity
        ball_speed = math.sqrt(velocity.x**2 + velocity.y**2 + velocity.z**2)
        if ball_speed > self.ball_speed_record:
            self.ball_speed_record = ball_speed
    
    def _track_possession(self, packet, local_player_index):
        """Track which player has possession of the ball"""
        ball = packet.game_ball
        closest_player = None
        closest_distance = float('inf')
        
        # Find closest player to ball
        for i, car in enumerate(packet.game_cars):
            if i >= packet.num_cars:
                break
                
            # Calculate distance to ball
            dx = car.physics.location.x - ball.physics.location.x
            dy = car.physics.location.y - ball.physics.location.y
            dz = car.physics.location.z - ball.physics.location.z
            distance = math.sqrt(dx**2 + dy**2 + dz**2)
            
            if distance < closest_distance:
                closest_distance = distance
                closest_player = i
        
        # Update possession if within threshold
        if closest_distance < self.possession_distance:
            if self.last_possession_player != closest_player:
                self.last_possession_player = closest_player
                self.ball_possession_time = time.time()
    
    @condition("packet.game_info.is_kickoff_pause")
    def on_kickoff_start(self, packet, local_player_index, playername):
        """Triggered when kickoff starts"""
        self.logger("Ball Tracker: Kickoff detected - resetting possession tracking")
        self.last_possession_player = None
        self.ball_possession_time = 0
    
    @condition("packet.game_ball.physics.location.z > self.high_ball_threshold")
    def on_high_ball(self, packet, local_player_index):
        """Triggered when ball is high in the air"""
        ball_height = packet.game_ball.physics.location.z
        if ball_height > self.ball_height_record * 0.9:  # Only log if near record
            self.logger(f"Ball Tracker: High ball detected! Height: {ball_height:.0f}")
    
    @condition("packet.game_ball.physics.velocity.length() > self.fast_ball_threshold")
    def on_fast_ball(self, packet):
        """Triggered when ball is moving very fast"""
        velocity = packet.game_ball.physics.velocity
        speed = math.sqrt(velocity.x**2 + velocity.y**2 + velocity.z**2)
        if speed > self.ball_speed_record * 0.9:  # Only log if near record
            self.logger(f"Ball Tracker: Fast ball detected! Speed: {speed:.0f}")
    
    @condition("packet.game_info.is_match_ended")
    def on_match_end(self, packet):
        """Triggered when match ends - report statistics"""
        self.logger("=== BALL TRACKER MATCH SUMMARY ===")
        self.logger(f"Highest ball height: {self.ball_height_record:.0f}")
        self.logger(f"Fastest ball speed: {self.ball_speed_record:.0f}")
        self.logger("=================================")
    
    def controller_filter(self, controller):
        """
        This plugin doesn't modify controls, but demonstrates the method
        You could add logic here to modify controller inputs
        """
        # Example: Could add slight input smoothing or limits here
        return controller  # Return unmodified
    
    def main(self):
        """
        Background thread for periodic reporting
        Runs every 30 seconds to report current statistics
        """
        try:
            while True:
                time.sleep(30)  # Report every 30 seconds
                
                if hasattr(self, 'start_time'):
                    runtime = time.time() - self.start_time
                    self.logger(f"Ball Tracker: Runtime {runtime:.0f}s | "
                              f"Max Height: {self.ball_height_record:.0f} | "
                              f"Max Speed: {self.ball_speed_record:.0f}")
                
        except Exception as e:
            self.logger(f"Ball Tracker: Error in background thread: {e}")
    
    def shutdown(self):
        """Called when the plugin system shuts down"""
        self.logger("Ball Tracker: Shutting down...")
        if hasattr(self, 'start_time'):
            total_runtime = time.time() - self.start_time
            self.logger(f"Ball Tracker: Total runtime: {total_runtime:.1f} seconds")
        self.logger("Ball Tracker: Goodbye!")
