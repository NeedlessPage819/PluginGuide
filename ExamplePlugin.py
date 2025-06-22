#Holy AI #100
# This is a ball tracking system for a soccer video game. It keeps track of:
# - How high and fast the ball goes
# - Which player has the ball (possession)
# - When goals are scored
# - The current score and winning team
# - Special events like kickoffs and high/fast balls

# First we import some tools we'll need:
import time  # For tracking time
import math  # For math calculations
import collections  # For keeping history of movements
import numpy as np  # For smoothing controls

# This sets up how we control the game (steering, jumping etc.)
try:
    from rlbot.agents.base_agent import SimpleControllerState
except ImportError:
    class SimpleControllerState:
        def __init__(self, steer=0.0, throttle=0.0, pitch=0.0, yaw=0.0, roll=0.0, jump=False, boost=False, handbrake=False, use_item=False):
            self.steer, self.throttle, self.pitch, self.yaw, self.roll = steer, throttle, pitch, yaw, roll
            self.jump, self.boost, self.handbrake, self.use_item = jump, boost, handbrake, use_item
        def __str__(self): return f"SCS(T:{self.throttle:.1f} S:{self.steer:.1f} P:{self.pitch:.1f} J:{self.jump})"

class BallTracker:
    def __init__(self, ConsoleLogger=None):
        """
        This starts up the ball tracker when the game begins.
        It sets up all the counters and trackers we'll use.
        """
        self.logger = ConsoleLogger or print  # How we show messages
        self.Name = lambda: "Ball Tracker Enhanced"  # Our name
        self.enabled = True  # Whether we're active

        # These track records about the ball
        self.ball_height_record = 0  # Highest the ball has gone
        self.ball_speed_record = 0  # Fastest the ball has moved
        self.last_ball_touch_time = 0  # When ball was last touched
        self.ball_possession_time = 0  # How long someone had the ball
        self.last_possession_player_index = None  # Who last had the ball

        # These track scores and goals
        self.last_scores = {}  # Each player's score
        self.goals_scored_this_match = []  # List of goals in this game
        self.current_team_scores = [0, 0]  # Blue and Orange team scores
        self.local_player_team = None  # Which team you're on

        # These remember last reports to avoid repeating info
        self.last_reported_team_scores = [0, 0]
        self.last_reported_ball_height = 0
        self.last_reported_ball_speed = 0
        self.last_reported_winning_status = ""

        # Settings for what counts as high/fast/possession
        self.possession_distance_threshold = 200  # How close to count as having ball
        self.high_ball_threshold = 300  # What counts as a high ball
        self.fast_ball_threshold = 2000  # What counts as a fast ball

        # These smooth out controller movements
        self.smoothing_window_size = int(1.1)  # How much to smooth movements
        self.steer_history = collections.deque(maxlen=self.smoothing_window_size)
        self.throttle_history = collections.deque(maxlen=self.smoothing_window_size)
        self.pitch_history = collections.deque(maxlen=self.smoothing_window_size)
        self.yaw_history = collections.deque(maxlen=self.smoothing_window_size)
        self.roll_history = collections.deque(maxlen=self.smoothing_window_size)

        self.logger(f"[{self.Name()}] Initialized!")  # Say we're ready

    def _reset_match_stats(self):
        """Resets all stats when a new match starts"""
        self.logger(f"[{self.Name()}] Resetting match stats.")
        # Clear all records
        self.ball_height_record = 0
        self.ball_speed_record = 0
        self.ball_possession_time = 0
        self.last_possession_player_index = None
        self.last_scores = {}
        self.goals_scored_this_match = []
        self.current_team_scores = [0, 0]
        
        # Reset last reports
        self.last_reported_team_scores = [0, 0]
        self.last_reported_ball_height = 0
        self.last_reported_ball_speed = 0
        self.last_reported_winning_status = ""

    def initialize(self):
        """Called when starting up the tracker"""
        self.logger(f"[{self.Name()}] Starting analysis...")
        self.start_time = time.time()  # Remember when we started
        self._reset_match_stats()  # Reset all stats

    def on_game_event_started(self, event):
        """Called when a new match begins"""
        if not self.enabled: return
        self.logger(f"[{self.Name()}] New match started.")
        self._reset_match_stats()
        self.start_time = time.time()  # Reset timer for new match

    def game_tick_packet_set(self, packet, local_player_index, playername, field_info):
        """
        Main function that runs every game frame.
        Does all the tracking and analysis.
        """
        if not self.enabled:
            return None

        try:
            ball = packet.game_ball  # Get current ball info

            # Remember which team you're on
            if local_player_index < packet.num_cars:
                self.local_player_team = packet.game_cars[local_player_index].team

            # Update all our trackers
            self._update_ball_records(ball)  # Height/speed
            self._track_possession(packet)  # Who has ball
            self._detect_goals(packet)  # Check for goals
            self._update_team_scores(packet)  # Update scores

            return None  # We don't control anything

        except Exception as e:
            self.logger(f"[{self.Name()}] Error: {e}")
            return None

    def _update_ball_records(self, ball):
        """Updates highest and fastest ball records"""
        ball_height = ball.physics.location.z
        if ball_height > self.ball_height_record:
            self.ball_height_record = ball_height  # New height record

        velocity = ball.physics.velocity
        ball_speed = math.sqrt(velocity.x**2 + velocity.y**2 + velocity.z**2)
        if ball_speed > self.ball_speed_record:
            self.ball_speed_record = ball_speed  # New speed record

    def _update_team_scores(self, packet):
        """Calculates team scores from player scores"""
        blue_score = 0
        orange_score = 0
        
        # Add up all player scores by team
        for i in range(packet.num_cars):
            car = packet.game_cars[i]
            try:
                player_score = car.score_info.score
                if car.team == 0:  # Blue team
                    blue_score += player_score
                elif car.team == 1:  # Orange team
                    orange_score += player_score
            except Exception as e:
                self.logger(f"[{self.Name()}] Error getting score for car {i}: {e}")
        
        self.current_team_scores[0] = blue_score
        self.current_team_scores[1] = orange_score
        
        # Figure out if we're winning/losing
        winning_status = ""
        if self.local_player_team is not None:
            if self.local_player_team == 0:  # On Blue team
                if blue_score > orange_score:
                    winning_status = "WE ARE WINNING!"
                elif orange_score > blue_score:
                    winning_status = "WE ARE LOSING!"
                else:
                    winning_status = "WE ARE TIED!"
            else:  # On Orange team
                if orange_score > blue_score:
                    winning_status = "WE ARE WINNING!"
                elif blue_score > orange_score:
                    winning_status = "WE ARE LOSING!"
                else:
                    winning_status = "WE ARE TIED!"
        else:
            winning_status = "Team unknown"

    def _track_possession(self, packet):
        """Tracks which player is closest to the ball"""
        if not self.enabled: return

        ball = packet.game_ball
        closest_player_idx = -1
        min_distance_to_ball = float('inf')

        # Find which player is closest to ball
        for i in range(packet.num_cars):
            car = packet.game_cars[i]
            dist_sq = ( (car.physics.location.x - ball.physics.location.x)**2 +
                        (car.physics.location.y - ball.physics.location.y)**2 +
                        (car.physics.location.z - ball.physics.location.z)**2 )
            
            if dist_sq < min_distance_to_ball:
                min_distance_to_ball = dist_sq
                closest_player_idx = i
        
        actual_distance = math.sqrt(min_distance_to_ball)

        if closest_player_idx != -1 and actual_distance < self.possession_distance_threshold:
            if self.last_possession_player_index != closest_player_idx:
                self.last_possession_player_index = closest_player_idx
                self.ball_possession_time = packet.game_info.seconds_elapsed # Use game time
                # Fix the decode error by handling both string and bytes types
                car_name = packet.game_cars[closest_player_idx].name
                if isinstance(car_name, bytes):
                    possessor_name = car_name.decode('utf-16', errors='ignore').rstrip('\x00')
                else:
                    possessor_name = str(car_name).rstrip('\x00')
                self.logger(f"[{self.Name()}] Possession changed to: {possessor_name} (Index {closest_player_idx}) at {actual_distance:.0f} units.")
        elif self.last_possession_player_index is not None and actual_distance >= self.possession_distance_threshold:
            # Ball is loose
            self.last_possession_player_index = None
            self.logger(f"[{self.Name()}] Ball is now loose.")

    def _detect_goals(self, packet):
        """Detects and logs goals scored by tracking individual player scores."""
        if not self.enabled: return
        
        # Loop through all cars to check for score changes
        for i in range(packet.num_cars):
            car = packet.game_cars[i]
            
            try:
                # Get the score directly from the packet's ScoreInfo struct
                current_score = car.score_info.score
                
                # Get the last known score for this player from our dictionary
                last_known_score = self.last_scores.get(car.name, 0)
                
                if last_known_score != current_score:
                    # Handle car name decoding
                    car_name = car.name
                    if isinstance(car_name, bytes):
                        player_name = car_name.decode('utf-16', errors='ignore').rstrip('\x00')
                    else:
                        player_name = str(car_name).rstrip('\x00')
                    
                    goal_description = f"Goal scored by {player_name}!"
                    self.goals_scored_this_match.append(goal_description)
                    self.logger(f"[{self.Name()}] *** {goal_description} Score: {last_known_score} → {current_score} ***")
                    
                    # Update the score in our dictionary for this specific player
                    self.last_scores[car.name] = current_score
                    
            except Exception as e:
                self.logger(f"[{self.Name()}] Error processing car {car.name}: {e}")

    @condition("packet.game_info.is_kickoff_pause")
    def on_kickoff_start(self, packet, local_player_index, playername):
        """Triggered when kickoff starts (including after a goal)."""
        if not self.enabled: return
        self.logger(f"[{self.Name()}] Kickoff detected - resetting possession and ensuring scores are synced.")
        self.last_possession_player_index = None
        self.ball_possession_time = packet.game_info.seconds_elapsed # Reset to current game time
        # Sync scores to prevent re-detecting goals
        for i in range(packet.num_cars):
            car = packet.game_cars[i]
            try:
                self.last_scores[car.name] = car.score_info.score
            except Exception as e:
                self.logger(f"[{self.Name()}] Error syncing score for car {car.name}: {e}")

    @condition("packet.game_ball.physics.location.z > 300")
    def on_high_ball(self, packet, local_player_index):
        """Triggered when ball is high in the air"""
        if not self.enabled: return
        ball_height = packet.game_ball.physics.location.z
        if ball_height > self.ball_height_record * 0.95 : # Only log if near record
            self.logger(f"[{self.Name()}] High ball detected! Height: {ball_height:.0f} (Record: {self.ball_height_record:.0f})")

    @condition("(packet.game_ball.physics.velocity.x**2 + packet.game_ball.physics.velocity.y**2 + packet.game_ball.physics.velocity.z**2)**0.5 > 2000")
    def on_fast_ball(self, packet):
        """Triggered when ball is moving very fast."""
        if not self.enabled: return
        velocity = packet.game_ball.physics.velocity
        speed = math.sqrt(velocity.x**2 + velocity.y**2 + velocity.z**2)
        if speed > self.ball_speed_record * 0.95: # Only log if near record
            self.logger(f"[{self.Name()}] Fast ball detected! Speed: {speed:.0f} (Record: {self.ball_speed_record:.0f})")

    @condition("packet.game_info.is_match_ended")
    def on_match_end_summary(self, packet):
        """Triggered when match ends - report statistics"""
        if not self.enabled: return
        self.logger(f"[{self.Name()}] === MATCH SUMMARY ===")
        self.logger(f"Final Score: Blue {self.current_team_scores[0]} - {self.current_team_scores[1]} Orange")
        if self.current_team_scores[0] > self.current_team_scores[1]:
            self.logger(f"Winner: Blue (Team 0)")
        elif self.current_team_scores[1] > self.current_team_scores[0]:
            self.logger(f"Winner: Orange (Team 1)")
        else:
            self.logger(f"Result: Draw")
        self.logger(f"Highest ball height this match: {self.ball_height_record:.0f}")
        self.logger(f"Fastest ball speed this match: {self.ball_speed_record:.0f}")
        self.logger(f"Goals Scored ({len(self.goals_scored_this_match)}):")
        for goal_desc in self.goals_scored_this_match:
            self.logger(f"  - {goal_desc}")
        self.logger(f"[{self.Name()}] ====================")

    def controller_filter(self, controller):
        """Apply movement smoothing to controller inputs."""
        if controller is None:
            return None
            
        # Store current analog controls in history
        self.steer_history.append(controller.steer)
        self.throttle_history.append(controller.throttle)
        self.pitch_history.append(controller.pitch)
        self.yaw_history.append(controller.yaw)
        self.roll_history.append(controller.roll)

        # Calculate smoothed controls using mean of history
        smoothed_steer = np.mean(list(self.steer_history)) if self.steer_history else controller.steer
        smoothed_throttle = np.mean(list(self.throttle_history)) if self.throttle_history else controller.throttle
        smoothed_pitch = np.mean(list(self.pitch_history)) if self.pitch_history else controller.pitch
        smoothed_yaw = np.mean(list(self.yaw_history)) if self.yaw_history else controller.yaw
        smoothed_roll = np.mean(list(self.roll_history)) if self.roll_history else controller.roll
        
        # For boolean controls, pass through directly for responsiveness
        smoothed_jump = controller.jump
        smoothed_boost = controller.boost
        smoothed_handbrake = controller.handbrake
        smoothed_use_item = getattr(controller, 'use_item', False)

        # Create new controller state with smoothed values
        smoothed_controller = SimpleControllerState(
            steer=float(smoothed_steer),
            throttle=float(smoothed_throttle),
            pitch=float(smoothed_pitch),
            yaw=float(smoothed_yaw),
            roll=float(smoothed_roll),
            jump=bool(smoothed_jump),
            boost=bool(smoothed_boost),
            handbrake=bool(smoothed_handbrake),
            use_item=bool(smoothed_use_item)
        )
        
        return smoothed_controller

    def main(self):
        """ Background thread for periodic reporting. """
        if not self.enabled: return # Exit if disabled from the start

        self.logger(f"[{self.Name()}] Background reporting thread started.")
        while self.enabled: # Loop relies on self.enabled to be shut down
            time.sleep(5)  # Report every 5 seconds instead of 0.2
            if not self.enabled: break # Check again before logging, in case it was disabled during sleep

            try:
                if hasattr(self, 'start_time') and hasattr(self, 'current_team_scores'):
                    runtime = time.time() - self.start_time
                    score_line = f"Score: B {self.current_team_scores[0]} - O {self.current_team_scores[1]}"
                    
                    # Determine winning status for background report
                    winning_status = ""
                    if self.local_player_team is not None:
                        if self.local_player_team == 0:  # Local player is on Blue team
                            if self.current_team_scores[0] > self.current_team_scores[1]:
                                winning_status = "WE ARE WINNING!"
                            elif self.current_team_scores[1] > self.current_team_scores[0]:
                                winning_status = "WE ARE LOSING!"
                            else:
                                winning_status = "WE ARE TIED!"
                        else:  # Local player is on Orange team
                            if self.current_team_scores[1] > self.current_team_scores[0]:
                                winning_status = "WE ARE WINNING!"
                            elif self.current_team_scores[0] > self.current_team_scores[1]:
                                winning_status = "WE ARE LOSING!"
                            else:
                                winning_status = "WE ARE TIED!"
                    else:
                        winning_status = "Team unknown"

                    # Check if anything has changed
                    scores_changed = (self.current_team_scores != self.last_reported_team_scores)
                    ball_height_changed = (self.ball_height_record != self.last_reported_ball_height)
                    ball_speed_changed = (self.ball_speed_record != self.last_reported_ball_speed)
                    winning_status_changed = (winning_status != self.last_reported_winning_status)
                    
                    if scores_changed or ball_height_changed or ball_speed_changed or winning_status_changed:
                        self.logger(f"[{self.Name()}] Tick Report: Runtime {runtime:.0f}s | {score_line} | {winning_status} | Max H: {self.ball_height_record:.0f} | Max S: {self.ball_speed_record:.0f}")
                        
                        # Update last reported values
                        self.last_reported_team_scores = self.current_team_scores.copy()
                        self.last_reported_ball_height = self.ball_height_record
                        self.last_reported_ball_speed = self.ball_speed_record
                        self.last_reported_winning_status = winning_status
                else:
                    # Always log score even if waiting for game data
                    self.logger(f"[{self.Name()}] Background Report: Waiting for game data...")
            except Exception as e:
                self.logger(f"[{self.Name()}] Error in background thread: {e}")
        
        self.logger(f"[{self.Name()}] Background reporting thread finished.")


    def on_game_event_destroyed(self, event):
        """Called when a game event (match) ends and is destroyed."""
        if not self.enabled: return # Check enabled status
        self.logger(f"[{self.Name()}] Game event destroyed. Finalizing and resetting stats for next game.")
        # Perform final summary if not already done by on_match_end_summary
        # (This provides a fallback if on_match_end_summary condition wasn't met for some reason)
        # self.on_match_end_summary(None) # packet would be None here, so it's better to rely on game_tick for final summary
        
        self._reset_match_stats()
        # self.enabled = False # If you want the plugin to stop its main thread after one game

    def shutdown(self):
        """Called when the plugin system shuts down"""
        self.enabled = False # Crucial for stopping the main() thread gracefully
        self.logger(f"[{self.Name()}] Shutting down...")
        if hasattr(self, 'start_time'): # Check if start_time was initialized
            total_runtime_since_init = time.time() - self.start_time # This is total plugin active time
            self.logger(f"[{self.Name()}] Total plugin active time: {total_runtime_since_init:.1f} seconds")
        self.logger(f"[{self.Name()}] Goodbye!")
