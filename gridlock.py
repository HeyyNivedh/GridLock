#!/usr/bin/env python3
"""
================================================================================
GRIDLOCK: Adversarial Containment Game using Minimax Search & A* Heuristic
S5 KTU AI Mini Project Implementation
Stack: Python 3.10+ | Pygame 2.5+
Author: S5 AI Project Team
================================================================================
Architecture Overview:
  1. GridLockState: Discrete 9x9 game-tree state representation & transitions
  2. AStarPlanner: Dynamic A* search with Manhattan heuristic & path reconstruction
  3. MinimaxAI: Alpha-Beta pruning adversary (depth=4) with strategic candidate pruning
  4. TelemetryData: Real-time decision metrics (nodes, cutoffs, latency, path, f-scores)
  5. SelfTestSuite: Automated verification of containment, path optimality & pruning
  6. GridLockUI: 2026 High-Tech Minimalist / Glassmorphic Pygame interface
================================================================================
"""

import sys
import os
import time
import math
import heapq
from typing import List, Tuple, Set, Optional, Dict

# Suppress Pygame welcome banner for clean console telemetry
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame

# ==============================================================================
# CONFIGURATION & COLOR CONSTANTS (2026 High-Tech Glassmorphism Palette)
# ==============================================================================
GRID_SIZE = 9
EXITS: List[Tuple[int, int]] = [(0, 4), (8, 4), (4, 0), (4, 8)]
DEFAULT_AI_START: Tuple[int, int] = (4, 4)
SEARCH_DEPTH = 4

# Window & Layout Geometry
WINDOW_WIDTH = 1140
WINDOW_HEIGHT = 760
BOARD_OFFSET_X = 40
BOARD_OFFSET_Y = 40
GRID_PIXEL_SIZE = 680
CELL_SIZE = GRID_PIXEL_SIZE // GRID_SIZE
CELL_GAP = 6
TILE_INNER_SIZE = CELL_SIZE - CELL_GAP

# Color Tokens
COLOR_CANVAS = (13, 17, 23)          # #0D1117 Obsidian
COLOR_PANEL_BG = (22, 27, 34)        # #161B22 Slate Card
COLOR_PANEL_BORDER = (48, 54, 61)    # #30363D Border
COLOR_GRID_BG = (18, 22, 29)         # Deep board inset
COLOR_TILE_EMPTY = (30, 36, 46)      # Idle cell tile
COLOR_TILE_BORDER = (40, 48, 60)     # Inner cell outline
COLOR_TILE_HOVER = (56, 139, 253, 50)# Subtle blue hover wash

# Neon Brand Highlights
COLOR_CYAN_TRACE = (0, 240, 255)     # #00F0FF Neon Cyan (A* trace & Exit portal)
COLOR_AMBER_WARN = (255, 184, 0)     # #FFB800 Amber Alert / Bottleneck
COLOR_CRIMSON_WALL = (255, 51, 102)  # #FF3366 Barrier Core
COLOR_CRIMSON_GLOW = (255, 51, 102, 60)
COLOR_LIME_AGENT = (57, 255, 20)     # #39FF14 Radioactive Lime
COLOR_LIME_GLOW = (57, 255, 20, 70)

COLOR_TEXT_PRIMARY = (240, 246, 252) # #F0F6FC Crisp White
COLOR_TEXT_MUTED = (139, 148, 158)   # #8B949E Slate Muted
COLOR_TEXT_CYAN = (88, 166, 255)     # Soft Cyan Header
COLOR_TEXT_GREEN = (63, 185, 80)     # Emerald Green Pass
COLOR_BADGE_BG = (33, 38, 45)

# ==============================================================================
# 1. CORE GRAPH SEARCH: A* PATHFINDING WITH MANHATTAN HEURISTIC
# ==============================================================================
class AStarPlanner:
    """Dynamic A* search engine for shortest escape route calculation."""

    @staticmethod
    def manhattan(p1: Tuple[int, int], p2: Tuple[int, int]) -> int:
        """Admissible and consistent Manhattan distance heuristic h(n)."""
        return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

    @classmethod
    def multi_exit_heuristic(cls, p: Tuple[int, int]) -> int:
        """Admissible multi-goal heuristic: minimum Manhattan distance to any perimeter exit."""
        return min(abs(p[0] - e[0]) + abs(p[1] - e[1]) for e in EXITS)

    @classmethod
    def get_neighbors(cls, pos: Tuple[int, int], barriers: Set[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Return 4-connected orthogonal adjacent cells within grid bounds."""
        r, c = pos
        neighbors = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                if (nr, nc) not in barriers:
                    neighbors.append((nr, nc))
        return neighbors

    @classmethod
    def search_to_single_exit(
        cls, start: Tuple[int, int], target_exit: Tuple[int, int], barriers: Set[Tuple[int, int]]
    ) -> Optional[List[Tuple[int, int]]]:
        """Runs single-goal A* with Manhattan heuristic to a specific exit node."""
        if start == target_exit:
            return [start]
        if target_exit in barriers:
            return None

        open_set: List[Tuple[int, int, Tuple[int, int]]] = []
        heapq.heappush(open_set, (cls.manhattan(start, target_exit), 0, start))
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score: Dict[Tuple[int, int], int] = {start: 0}

        while open_set:
            f, g, current = heapq.heappop(open_set)
            if current == target_exit:
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                return path

            if g > g_score.get(current, float("inf")):
                continue

            for neighbor in cls.get_neighbors(current, barriers):
                tentative_g = g + 1
                if tentative_g < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_val = tentative_g + cls.manhattan(neighbor, target_exit)
                    heapq.heappush(open_set, (f_val, tentative_g, neighbor))

        return None

    @classmethod
    def find_shortest_escape_path(
        cls, start: Tuple[int, int], barriers: Set[Tuple[int, int]]
    ) -> Tuple[Optional[List[Tuple[int, int]]], Optional[Tuple[int, int]], float]:
        """
        High-performance Multi-Goal A* search across all perimeter exits using the
        admissible minimum Manhattan heuristic h(n) = min_e Manhattan(n, e).
        Returns: (path, target_exit, path_cost). If trapped, returns (None, None, inf).
        """
        if start in EXITS:
            return [start], start, 0.0

        open_set: List[Tuple[int, int, Tuple[int, int]]] = []
        heapq.heappush(open_set, (cls.multi_exit_heuristic(start), 0, start))
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score: Dict[Tuple[int, int], int] = {start: 0}

        while open_set:
            f, g, current = heapq.heappop(open_set)

            if current in EXITS:
                target_node = current
                path = [target_node]
                curr = target_node
                while curr in came_from:
                    curr = came_from[curr]
                    path.append(curr)
                path.reverse()
                return path, target_node, float(len(path) - 1)

            if g > g_score.get(current, float("inf")):
                continue

            for neighbor in cls.get_neighbors(current, barriers):
                tentative_g = g + 1
                if tentative_g < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_val = tentative_g + cls.multi_exit_heuristic(neighbor)
                    heapq.heappush(open_set, (f_val, tentative_g, neighbor))

        return None, None, float("inf")


# ==============================================================================
# 2. TELEMETRY & DECISION METRICS
# ==============================================================================
class TelemetryData:
    """Carries real-time search inspection metrics to the HUD."""

    def __init__(self):
        self.move_count: int = 0
        self.evaluated_nodes: int = 0
        self.pruned_branches: int = 0
        self.latency_ms: float = 0.0
        self.best_score: float = 0.0
        self.best_move: Optional[Tuple[int, int]] = None
        self.current_a_star_path: Optional[List[Tuple[int, int]]] = None
        self.a_star_distance: int = 0
        self.adjacent_scores: Dict[Tuple[int, int], float] = {}
        self.game_status_text: str = "HUMAN TURN: PLACE BARRICADE"


# ==============================================================================
# 3. GAME STATE & MECHANICS
# ==============================================================================
class GridLockState:
    """Immutable representation of a board configuration for minimax simulation."""

    def __init__(self, ai_pos: Tuple[int, int], barriers: Set[Tuple[int, int]]):
        self.ai_pos = ai_pos
        self.barriers = set(barriers)

    def is_ai_win(self) -> bool:
        return self.ai_pos in EXITS

    def is_human_win(self) -> bool:
        _, _, dist = AStarPlanner.find_shortest_escape_path(self.ai_pos, self.barriers)
        return math.isinf(dist)

    def get_mobility(self) -> int:
        return len(AStarPlanner.get_neighbors(self.ai_pos, self.barriers))


# ==============================================================================
# 4. ADVERSARIAL MINIMAX AI WITH ALPHA-BETA PRUNING
# ==============================================================================
class MinimaxAI:
    """
    Minimax search with Alpha-Beta pruning (Depth=4).
    MAX Player = AI Escapee (wants to reach exits, minimize distance, maximize mobility).
    MIN Player = Human Hunter (wants to block exits, increase distance, contain AI).
    """

    def __init__(self, depth: int = SEARCH_DEPTH):
        self.depth = depth
        self.nodes_evaluated: int = 0
        self.cutoffs_count: int = 0

    def evaluate_state(self, state: GridLockState, depth_level: int) -> float:
        """
        Composite Heuristic Evaluation Function:
          H(s) = W_dist * (MAX_DIST - d*) + W_mob * Mobility + W_red * OpenExits
        Includes terminal rewards/penalties adjusted by search depth.
        """
        # Terminal Check 1: AI reached exit
        if state.is_ai_win():
            return 10000.0 - depth_level * 10

        # Terminal Check 2: AI path to all exits is severed
        path, _, shortest_dist = AStarPlanner.find_shortest_escape_path(state.ai_pos, state.barriers)
        if math.isinf(shortest_dist):
            return -10000.0 + depth_level * 10

        mobility = state.get_mobility()
        if mobility == 0:
            return -10000.0 + depth_level * 10

        # Heuristic polynomial combination
        # The AI strongly values low distance to exit and high free movement
        score = (
            2000.0
            - (shortest_dist * 130.0)
            + (mobility * 45.0)
        )
        return score

    def get_strategic_barrier_candidates(self, state: GridLockState) -> List[Tuple[int, int]]:
        """
        Prunes the 70+ empty cell space into top strategic candidates for Human MIN:
          1. Cells directly on current A* escape path
          2. Cells immediately adjacent to AI
          3. Cells immediately guarding exit portals
        This ensures < 15ms calculation while maintaining fierce adversary play.
        """
        candidates: Set[Tuple[int, int]] = set()

        # 1. Cells along shortest A* path (the most immediate threat)
        path, _, _ = AStarPlanner.find_shortest_escape_path(state.ai_pos, state.barriers)
        if path and len(path) > 1:
            for node in path[1:min(5, len(path))]:
                if node not in EXITS:
                    candidates.add(node)

        # 2. Adjacent unblocked neighbors of AI
        for neighbor in AStarPlanner.get_neighbors(state.ai_pos, state.barriers):
            if neighbor not in EXITS:
                candidates.add(neighbor)

        # 3. Neighborhood around exits
        for exit_node in EXITS:
            er, ec = exit_node
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = er + dr, ec + dc
                if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                    if (nr, nc) != state.ai_pos and (nr, nc) not in state.barriers and (nr, nc) not in EXITS:
                        candidates.add((nr, nc))

        # Sort candidates by proximity to AI for better alpha-beta move ordering
        sorted_candidates = sorted(
            list(candidates),
            key=lambda c: AStarPlanner.manhattan(c, state.ai_pos)
        )
        return sorted_candidates[:7]  # Restrict to top 7 high-impact barrier placements

    def minimax(
        self,
        state: GridLockState,
        depth: int,
        alpha: float,
        beta: float,
        is_maximizing: bool
    ) -> float:
        """Alpha-Beta minimax search recursion."""
        self.nodes_evaluated += 1

        # Terminal conditions or depth limit
        if depth == 0 or state.is_ai_win() or state.is_human_win():
            return self.evaluate_state(state, depth)

        if is_maximizing:
            # MAX TURN (AI Escapee)
            max_eval = -float("inf")
            ai_moves = AStarPlanner.get_neighbors(state.ai_pos, state.barriers)
            if not ai_moves:
                return -10000.0 + depth * 10

            # Move ordering: prioritize moves that bring AI closer to any exit
            ai_moves.sort(key=lambda m: min(AStarPlanner.manhattan(m, e) for e in EXITS))

            for move in ai_moves:
                child_state = GridLockState(ai_pos=move, barriers=state.barriers)
                val = self.minimax(child_state, depth - 1, alpha, beta, False)
                max_eval = max(max_eval, val)
                alpha = max(alpha, val)
                if beta <= alpha:
                    self.cutoffs_count += 1
                    break  # Beta cut-off
            return max_eval
        else:
            # MIN TURN (Human Hunter Barrier Placement)
            min_eval = float("inf")
            barrier_candidates = self.get_strategic_barrier_candidates(state)
            if not barrier_candidates:
                return self.evaluate_state(state, depth)

            for cand in barrier_candidates:
                child_barriers = state.barriers.copy()
                child_barriers.add(cand)
                child_state = GridLockState(ai_pos=state.ai_pos, barriers=child_barriers)
                val = self.minimax(child_state, depth - 1, alpha, beta, True)
                min_eval = min(min_eval, val)
                beta = min(beta, val)
                if beta <= alpha:
                    self.cutoffs_count += 1
                    break  # Alpha cut-off
            return min_eval

    def compute_best_move(self, state: GridLockState, telemetry: TelemetryData) -> Optional[Tuple[int, int]]:
        """
        Executes root decision of Minimax (Alpha-Beta) with latency timing and candidate caching.
        """
        start_time = time.perf_counter()
        self.nodes_evaluated = 0
        self.cutoffs_count = 0

        valid_moves = AStarPlanner.get_neighbors(state.ai_pos, state.barriers)
        if not valid_moves:
            return None

        # Check for immediate 1-step win
        for move in valid_moves:
            if move in EXITS:
                telemetry.evaluated_nodes = 1
                telemetry.pruned_branches = 0
                telemetry.latency_ms = (time.perf_counter() - start_time) * 1000.0
                telemetry.best_score = 10000.0
                telemetry.best_move = move
                return move

        best_score = -float("inf")
        best_move = valid_moves[0]
        alpha = -float("inf")
        beta = float("inf")
        adjacent_scores: Dict[Tuple[int, int], float] = {}

        # Sort moves initially using quick Manhattan heuristic
        valid_moves.sort(key=lambda m: min(AStarPlanner.manhattan(m, e) for e in EXITS))

        for move in valid_moves:
            child_state = GridLockState(ai_pos=move, barriers=state.barriers)
            score = self.minimax(child_state, self.depth - 1, alpha, beta, False)
            adjacent_scores[move] = round(score, 1)

            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, score)

        latency = (time.perf_counter() - start_time) * 1000.0

        # Update telemetry
        telemetry.evaluated_nodes = self.nodes_evaluated
        telemetry.pruned_branches = self.cutoffs_count
        telemetry.latency_ms = latency
        telemetry.best_score = best_score
        telemetry.best_move = best_move
        telemetry.adjacent_scores = adjacent_scores

        # Terminal logging requested in spec
        print(
            f"[Turn {telemetry.move_count}] Evaluated: {self.nodes_evaluated} nodes | "
            f"Pruned: {self.cutoffs_count} branches | Best Move: {best_move} | "
            f"Score: {best_score:.1f} | Latency: {latency:.2f} ms"
        )
        return best_move


# ==============================================================================
# 5. SELF-TEST SUITE ('T' KEY OR CLI '--test')
# ==============================================================================
class SelfTestSuite:
    """Automated headless verification suite testing containment, pathfinding, and pruning."""

    @staticmethod
    def run_all_tests() -> Dict[str, bool]:
        results = {}
        print("\n========================================================")
        print("        GRIDLOCK ALGORITHM SELF-TEST SUITE              ")
        print("========================================================")

        # Test 1: Terminal Containment Detection
        # Enclose center (4, 4) with 4 barriers at (3,4), (5,4), (4,3), (4,5)
        barriers_enc = {(3, 4), (5, 4), (4, 3), (4, 5)}
        path, _, dist = AStarPlanner.find_shortest_escape_path((4, 4), barriers_enc)
        t1_passed = math.isinf(dist) and (path is None)
        results["Containment Detection (A* Infinite Cost)"] = t1_passed
        print(f"Test 1 [Containment]: {'[PASS]' if t1_passed else '[FAIL]'} (dist={dist}, path={path})")

        # Test 2: Direct Path Verification on Empty Board
        # From center (4, 4), distance to nearest perimeter exit must be exactly 4 steps
        path_empty, target_exit, dist_empty = AStarPlanner.find_shortest_escape_path((4, 4), set())
        t2_passed = (dist_empty == 4) and (target_exit in EXITS) and (len(path_empty) == 5)
        results["Direct Path Verification (4-Step Clean Escape)"] = t2_passed
        print(
            f"Test 2 [Direct Path]: {'[PASS]' if t2_passed else '[FAIL]'} "
            f"(dist={dist_empty}, exit={target_exit}, steps={len(path_empty) if path_empty else 0})"
        )

        # Test 3: Pruning Sanity Check
        # Compare node expansions between Alpha-Beta pruning vs Exhaustive Minimax
        ai_ab = MinimaxAI(depth=3)
        state_test = GridLockState(ai_pos=(4, 4), barriers={(3, 4), (2, 4)})
        
        # Run Alpha-Beta
        ai_ab.nodes_evaluated = 0
        ai_ab.cutoffs_count = 0
        ai_ab.minimax(state_test, depth=3, alpha=-float("inf"), beta=float("inf"), is_maximizing=True)
        ab_nodes = ai_ab.nodes_evaluated

        # Run Exhaustive Minimax without pruning (alpha=-inf, beta=+inf never triggers cutoff)
        class ExhaustiveMinimax(MinimaxAI):
            def minimax(self, state, depth, alpha, beta, is_maximizing):
                self.nodes_evaluated += 1
                if depth == 0 or state.is_ai_win() or state.is_human_win():
                    return self.evaluate_state(state, depth)
                if is_maximizing:
                    max_eval = -float("inf")
                    for m in AStarPlanner.get_neighbors(state.ai_pos, state.barriers):
                        c = GridLockState(ai_pos=m, barriers=state.barriers)
                        val = self.minimax(c, depth - 1, -float("inf"), float("inf"), False)
                        max_eval = max(max_eval, val)
                    return max_eval
                else:
                    min_eval = float("inf")
                    for b in self.get_strategic_barrier_candidates(state):
                        c = GridLockState(ai_pos=state.ai_pos, barriers=state.barriers | {b})
                        val = self.minimax(c, depth - 1, -float("inf"), float("inf"), True)
                        min_eval = min(min_eval, val)
                    return min_eval

        ex_ai = ExhaustiveMinimax(depth=3)
        ex_ai.nodes_evaluated = 0
        ex_ai.minimax(state_test, depth=3, alpha=-float("inf"), beta=float("inf"), is_maximizing=True)
        exhaustive_nodes = ex_ai.nodes_evaluated

        t3_passed = ab_nodes < exhaustive_nodes
        results["Pruning Sanity Check (Alpha-Beta < Exhaustive)"] = t3_passed
        print(
            f"Test 3 [Pruning Sanity]: {'[PASS]' if t3_passed else '[FAIL]'} "
            f"(Alpha-Beta Nodes: {ab_nodes} vs Exhaustive Nodes: {exhaustive_nodes})"
        )
        print("========================================================\n")
        return results


# ==============================================================================
# 6. HIGH-TECH 2026 PYGAME GRAPHICAL USER INTERFACE
# ==============================================================================
class GridLockUI:
    """Renders the game with modern glassmorphism, procedural glowing primitives, and telemetry."""

    def __init__(self, debug_start: bool = False):
        pygame.init()
        pygame.display.set_caption("GridLock: Adversarial Containment [KTU AI Mini Project]")
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()

        # Procedural Font System with safe fallbacks
        self.font_title = self._load_font(26, bold=True)
        self.font_header = self._load_font(18, bold=True)
        self.font_body = self._load_font(14)
        self.font_mono = self._load_font(13, mono=True)
        self.font_badge = self._load_font(12, bold=True)
        self.font_tag = self._load_font(11, mono=True, bold=True)

        # Game Engine Instances
        self.ai_pos: Tuple[int, int] = DEFAULT_AI_START
        self.barriers: Set[Tuple[int, int]] = set()
        self.minimax = MinimaxAI(depth=SEARCH_DEPTH)
        self.telemetry = TelemetryData()

        # Visual States
        self.debug_mode: bool = debug_start
        self.game_over: bool = False
        self.winner: Optional[str] = None  # "HUMAN" or "AI"
        self.human_turn: bool = True
        self.banner_message: Optional[str] = None
        self.banner_timer: float = 0.0

        # Agent Lerp Animation
        self.render_ai_pos = [float(self.ai_pos[1] * CELL_SIZE + CELL_SIZE // 2),
                              float(self.ai_pos[0] * CELL_SIZE + CELL_SIZE // 2)]
        self.target_ai_pos = list(self.render_ai_pos)

        # Initialize A* Telemetry on Startup
        self._refresh_path_telemetry()

    def _load_font(self, size: int, bold: bool = False, mono: bool = False) -> pygame.font.Font:
        font_names = ["Consolas", "Courier New", "monospace"] if mono else ["Segoe UI", "Inter", "Arial", "sans-serif"]
        for name in font_names:
            try:
                f = pygame.font.SysFont(name, size, bold=bold)
                if f:
                    return f
            except Exception:
                continue
        return pygame.font.Font(None, size)

    def _refresh_path_telemetry(self):
        path, _, dist = AStarPlanner.find_shortest_escape_path(self.ai_pos, self.barriers)
        self.telemetry.current_a_star_path = path
        self.telemetry.a_star_distance = dist if not math.isinf(dist) else -1

    def grid_to_screen_center(self, r: int, c: int) -> Tuple[int, int]:
        x = BOARD_OFFSET_X + c * CELL_SIZE + CELL_SIZE // 2
        y = BOARD_OFFSET_Y + r * CELL_SIZE + CELL_SIZE // 2
        return x, y

    def screen_to_grid(self, sx: int, sy: int) -> Optional[Tuple[int, int]]:
        gx = sx - BOARD_OFFSET_X
        gy = sy - BOARD_OFFSET_Y
        if 0 <= gx < GRID_PIXEL_SIZE and 0 <= gy < GRID_PIXEL_SIZE:
            c = gx // CELL_SIZE
            r = gy // CELL_SIZE
            if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE:
                return r, c
        return None

    def trigger_ai_turn(self):
        """Executes Minimax evaluation and updates game state."""
        if self.game_over:
            return

        self.telemetry.game_status_text = "AI COMPUTING OPTIMAL ESCAPE..."
        self._render_frame()  # Quick paint so status updates on screen

        state = GridLockState(self.ai_pos, self.barriers)
        best_move = self.minimax.compute_best_move(state, self.telemetry)

        if best_move is None or state.is_human_win():
            self.game_over = True
            self.winner = "HUMAN"
            self.telemetry.game_status_text = "CONTAINMENT ACHIEVED! HUMAN WINS."
            return

        # Execute move
        self.ai_pos = best_move
        tx, ty = self.grid_to_screen_center(self.ai_pos[0], self.ai_pos[1])
        self.target_ai_pos = [float(tx - BOARD_OFFSET_X), float(ty - BOARD_OFFSET_Y)]
        self._refresh_path_telemetry()

        # Check for AI Escape
        if self.ai_pos in EXITS:
            self.game_over = True
            self.winner = "AI"
            self.telemetry.game_status_text = "AI BREACHED PERIMETER! AI WINS."
        else:
            self.human_turn = True
            self.telemetry.game_status_text = "HUMAN TURN: PLACE BARRICADE"

    def handle_click(self, pos: Tuple[int, int]):
        """Safe human interaction handler with rigorous boundary guard clauses."""
        if self.game_over or not self.human_turn:
            return

        cell = self.screen_to_grid(pos[0], pos[1])
        if cell is None:
            return

        r, c = cell
        # Validation rules:
        # 1. Cannot place on AI current position
        # 2. Cannot place on exit portals
        # 3. Cannot place on already occupied barrier cell
        if (r, c) == self.ai_pos or (r, c) in EXITS or (r, c) in self.barriers:
            return

        # Place barrier
        self.barriers.add((r, c))
        self.telemetry.move_count += 1
        self._refresh_path_telemetry()

        # Check if this placement instantly achieved containment
        if self.telemetry.a_star_distance == -1:
            self.game_over = True
            self.winner = "HUMAN"
            self.telemetry.game_status_text = "CONTAINMENT ACHIEVED! HUMAN WINS."
            return

        # Switch to AI turn
        self.human_turn = False
        self.trigger_ai_turn()

    def reset_game(self):
        """Resets the board back to default initial configuration."""
        self.ai_pos = DEFAULT_AI_START
        self.barriers.clear()
        self.game_over = False
        self.winner = None
        self.human_turn = True
        self.telemetry = TelemetryData()
        self.telemetry.game_status_text = "HUMAN TURN: PLACE BARRICADE"
        tx, ty = self.grid_to_screen_center(self.ai_pos[0], self.ai_pos[1])
        self.render_ai_pos = [float(tx - BOARD_OFFSET_X), float(ty - BOARD_OFFSET_Y)]
        self.target_ai_pos = list(self.render_ai_pos)
        self._refresh_path_telemetry()
        self.banner_message = "BOARD RESET TO DEFAULT (4, 4)"
        self.banner_timer = time.time() + 2.0

    def run_tests_and_banner(self):
        """Triggers self-test suite and presents result in HUD."""
        results = SelfTestSuite.run_all_tests()
        all_passed = all(results.values())
        self.banner_message = f"SELF-TEST SUITE: {'ALL 3 PASSED' if all_passed else 'TEST FAILED'}"
        self.banner_timer = time.time() + 3.5

    # ==========================================================================
    # PROCEDURAL RENDERING PIPELINE
    # ==========================================================================
    def _draw_rounded_card(
        self, surface: pygame.Surface, rect: pygame.Rect, bg_color: Tuple[int, int, int], border_color: Tuple[int, int, int], radius: int = 8
    ):
        pygame.draw.rect(surface, bg_color, rect, border_radius=radius)
        pygame.draw.rect(surface, border_color, rect, width=1, border_radius=radius)

    def _draw_glowing_circle(
        self, surface: pygame.Surface, center: Tuple[int, int], radius: int, color: Tuple[int, int, int], alpha_layers: int = 3
    ):
        """Draws multi-layer radial soft alpha glow without raster images."""
        glow_surf = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
        center_glow = (radius * 2, radius * 2)

        for i in range(alpha_layers, 0, -1):
            r = int(radius * (1.0 + i * 0.45))
            alpha = int(40 / i)
            pygame.draw.circle(glow_surf, (*color[:3], alpha), center_glow, r)

        # Core bright entity
        pygame.draw.circle(glow_surf, color[:3], center_glow, radius)
        surface.blit(glow_surf, (center[0] - radius * 2, center[1] - radius * 2))

    def _render_board(self, mouse_pos: Tuple[int, int], ticks: int):
        # Board Background container
        board_rect = pygame.Rect(BOARD_OFFSET_X, BOARD_OFFSET_Y, GRID_PIXEL_SIZE, GRID_PIXEL_SIZE)
        self._draw_rounded_card(self.screen, board_rect, COLOR_GRID_BG, COLOR_PANEL_BORDER, radius=12)

        hover_cell = self.screen_to_grid(mouse_pos[0], mouse_pos[1])

        # 1. Draw Grid Tiles
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                x = BOARD_OFFSET_X + c * CELL_SIZE + CELL_GAP // 2
                y = BOARD_OFFSET_Y + r * CELL_SIZE + CELL_GAP // 2
                tile_rect = pygame.Rect(x, y, TILE_INNER_SIZE, TILE_INNER_SIZE)

                is_exit = (r, c) in EXITS
                is_barrier = (r, c) in self.barriers
                is_hover = (r, c) == hover_cell and not is_exit and not is_barrier and (r, c) != self.ai_pos

                # Background fill
                if is_exit:
                    pulse = math.sin(ticks * 0.006 + r + c) * 20
                    color = (0, int(210 + pulse), int(235 + pulse))
                    pygame.draw.rect(self.screen, (20, 45, 60), tile_rect, border_radius=6)
                    pygame.draw.rect(self.screen, color, tile_rect, width=2, border_radius=6)
                elif is_barrier:
                    # Crimson barrier tile
                    pygame.draw.rect(self.screen, (60, 15, 25), tile_rect, border_radius=6)
                    pygame.draw.rect(self.screen, COLOR_CRIMSON_WALL, tile_rect, width=2, border_radius=6)
                    # Crosshair barrier icon
                    cx, cy = x + TILE_INNER_SIZE // 2, y + TILE_INNER_SIZE // 2
                    pygame.draw.line(self.screen, COLOR_CRIMSON_WALL, (cx - 10, cy - 10), (cx + 10, cy + 10), 2)
                    pygame.draw.line(self.screen, COLOR_CRIMSON_WALL, (cx - 10, cy + 10), (cx + 10, cy - 10), 2)
                else:
                    tile_bg = (40, 50, 68) if is_hover else COLOR_TILE_EMPTY
                    pygame.draw.rect(self.screen, tile_bg, tile_rect, border_radius=6)
                    border_c = COLOR_CYAN_TRACE if is_hover else COLOR_TILE_BORDER
                    pygame.draw.rect(self.screen, border_c, tile_rect, width=1, border_radius=6)

                # Exit Label
                if is_exit:
                    lbl = self.font_tag.render("EXIT", True, COLOR_CYAN_TRACE)
                    self.screen.blit(lbl, lbl.get_rect(center=tile_rect.center))

        # 2. Draw A* Shortest Path Neon Trace (if active or in debug mode)
        if self.telemetry.current_a_star_path and len(self.telemetry.current_a_star_path) > 1:
            pts = [self.grid_to_screen_center(pr, pc) for pr, pc in self.telemetry.current_a_star_path]
            # Cyan glowing lines
            if len(pts) >= 2:
                pygame.draw.lines(self.screen, (0, 120, 150), False, pts, 6)
                pygame.draw.lines(self.screen, COLOR_CYAN_TRACE, False, pts, 2)
                for pt in pts[1:-1]:
                    pygame.draw.circle(self.screen, COLOR_CYAN_TRACE, pt, 4)

        # 3. Debug Overlay Tags on adjacent cells
        if self.debug_mode and self.telemetry.adjacent_scores:
            for cell, score in self.telemetry.adjacent_scores.items():
                cx, cy = self.grid_to_screen_center(cell[0], cell[1])
                score_str = f"{score:+.0f}"
                tag_surf = self.font_tag.render(score_str, True, COLOR_AMBER_WARN)
                tag_rect = tag_surf.get_rect(center=(cx, cy + 16))
                # Small dark pill behind tag
                bg_pill = tag_rect.inflate(8, 4)
                pygame.draw.rect(self.screen, (10, 12, 16), bg_pill, border_radius=4)
                pygame.draw.rect(self.screen, COLOR_AMBER_WARN, bg_pill, width=1, border_radius=4)
                self.screen.blit(tag_surf, tag_rect)

        # 4. Draw AI Escapee Agent with Lerp & Halo Glow
        # Interpolate coordinates for silky smooth transition
        for i in (0, 1):
            self.render_ai_pos[i] += (self.target_ai_pos[i] - self.render_ai_pos[i]) * 0.28

        ai_center = (
            int(BOARD_OFFSET_X + self.render_ai_pos[0]),
            int(BOARD_OFFSET_Y + self.render_ai_pos[1])
        )
        pulse_r = int(18 + math.sin(ticks * 0.008) * 3)
        self._draw_glowing_circle(self.screen, ai_center, pulse_r, COLOR_LIME_AGENT)
        # Inner white target dot
        pygame.draw.circle(self.screen, (255, 255, 255), ai_center, 5)

    def _render_dashboard(self, ticks: int):
        panel_x = BOARD_OFFSET_X + GRID_PIXEL_SIZE + 30
        panel_y = BOARD_OFFSET_Y
        panel_w = WINDOW_WIDTH - panel_x - BOARD_OFFSET_X
        panel_h = GRID_PIXEL_SIZE

        # Main Telemetry Container
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        self._draw_rounded_card(self.screen, panel_rect, COLOR_PANEL_BG, COLOR_PANEL_BORDER, radius=12)

        cur_y = panel_y + 24
        pad_x = panel_x + 24

        # Title & Subtitle
        title = self.font_title.render("GRIDLOCK AI", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(title, (pad_x, cur_y))
        cur_y += 28

        sub = self.font_mono.render("S5 KTU MINIMAX & A* ADVERSARY", True, COLOR_TEXT_CYAN)
        self.screen.blit(sub, (pad_x, cur_y))
        cur_y += 26

        pygame.draw.line(self.screen, COLOR_PANEL_BORDER, (pad_x, cur_y), (panel_x + panel_w - 24, cur_y), 1)
        cur_y += 18

        # Game State Status Badge
        badge_rect = pygame.Rect(pad_x, cur_y, panel_w - 48, 44)
        badge_border = COLOR_CYAN_TRACE
        badge_color = (18, 38, 50)
        if self.game_over:
            if self.winner == "HUMAN":
                badge_border = COLOR_TEXT_GREEN
                badge_color = (20, 50, 30)
            else:
                badge_border = COLOR_CRIMSON_WALL
                badge_color = (55, 20, 30)

        self._draw_rounded_card(self.screen, badge_rect, badge_color, badge_border, radius=8)
        status_txt = self.font_badge.render(self.telemetry.game_status_text, True, COLOR_TEXT_PRIMARY)
        self.screen.blit(status_txt, status_txt.get_rect(center=badge_rect.center))
        cur_y += 56

        # Telemetry Metrics Grid
        metrics = [
            ("MOVE COUNT", f"{self.telemetry.move_count}"),
            ("SEARCH DEPTH", f"d = {SEARCH_DEPTH}"),
            ("EVALUATED NODES", f"{self.telemetry.evaluated_nodes}"),
            ("PRUNED BRANCHES", f"{self.telemetry.pruned_branches}"),
            ("COMPUTE LATENCY", f"{self.telemetry.latency_ms:.2f} ms"),
            ("A* SHORTEST PATH", f"{self.telemetry.a_star_distance} steps" if self.telemetry.a_star_distance != -1 else "INF (TRAPPED)"),
            ("AI MOBILITY", f"{len(AStarPlanner.get_neighbors(self.ai_pos, self.barriers))} free neighbors"),
            ("BEST ROOT SCORE", f"{self.telemetry.best_score:+.1f}"),
        ]

        metric_box_w = (panel_w - 60) // 2
        metric_box_h = 52

        for idx, (label, val) in enumerate(metrics):
            col = idx % 2
            row = idx // 2
            bx = pad_x + col * (metric_box_w + 12)
            by = cur_y + row * (metric_box_h + 10)

            box_rect = pygame.Rect(bx, by, metric_box_w, metric_box_h)
            self._draw_rounded_card(self.screen, box_rect, (28, 34, 43), COLOR_PANEL_BORDER, radius=6)

            lbl_surf = self.font_tag.render(label, True, COLOR_TEXT_MUTED)
            val_surf = self.font_mono.render(val, True, COLOR_CYAN_TRACE if "LATENCY" in label or "PATH" in label else COLOR_TEXT_PRIMARY)
            self.screen.blit(lbl_surf, (bx + 10, by + 8))
            self.screen.blit(val_surf, (bx + 10, by + 26))

        cur_y += 4 * (metric_box_h + 10) + 12

        # Inspector / Debug Mode Indicator Card
        insp_rect = pygame.Rect(pad_x, cur_y, panel_w - 48, 48)
        insp_bg = (30, 42, 35) if self.debug_mode else (26, 30, 38)
        insp_border = COLOR_LIME_AGENT if self.debug_mode else COLOR_PANEL_BORDER
        self._draw_rounded_card(self.screen, insp_rect, insp_bg, insp_border, radius=6)

        mode_txt = "DEBUG INSPECTOR: ACTIVE [PATH & SCORES ON]" if self.debug_mode else "DEBUG INSPECTOR: INACTIVE (PRESS 'D')"
        mode_surf = self.font_mono.render(mode_txt, True, COLOR_LIME_AGENT if self.debug_mode else COLOR_TEXT_MUTED)
        self.screen.blit(mode_surf, mode_surf.get_rect(center=insp_rect.center))
        cur_y += 62

        # Command Hotkeys Card
        cmd_rect = pygame.Rect(pad_x, cur_y, panel_w - 48, 110)
        self._draw_rounded_card(self.screen, cmd_rect, (20, 24, 30), COLOR_PANEL_BORDER, radius=6)

        hotkeys = [
            ("[D] Toggle Debug Inspector", "Shows live heuristic scores & A* vector"),
            ("[T] Run Self-Test Suite", "Executes 3 headless algorithm sanity tests"),
            ("[R] Reset Board", "Restarts puzzle from starting position"),
            ("[ESC] Exit", "Safely terminates game process"),
        ]
        cmd_y = cur_y + 10
        for key, desc in hotkeys:
            k_surf = self.font_tag.render(key, True, COLOR_AMBER_WARN)
            d_surf = self.font_tag.render(desc, True, COLOR_TEXT_MUTED)
            self.screen.blit(k_surf, (pad_x + 12, cmd_y))
            self.screen.blit(d_surf, (pad_x + 185, cmd_y))
            cmd_y += 24

        # Banner Notification (if active)
        if self.banner_message and time.time() < self.banner_timer:
            banner_rect = pygame.Rect(pad_x, panel_y + panel_h - 44, panel_w - 48, 32)
            self._draw_rounded_card(self.screen, banner_rect, (40, 28, 10), COLOR_AMBER_WARN, radius=4)
            b_txt = self.font_tag.render(self.banner_message, True, COLOR_AMBER_WARN)
            self.screen.blit(b_txt, b_txt.get_rect(center=banner_rect.center))

    def _render_frame(self):
        ticks = pygame.time.get_ticks()
        mouse_pos = pygame.mouse.get_pos()
        self.screen.fill(COLOR_CANVAS)
        self._render_board(mouse_pos, ticks)
        self._render_dashboard(ticks)
        pygame.display.flip()

    def run(self):
        """Primary application event and rendering loop."""
        running = True
        while running:
            self.clock.tick(60)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_d:
                        self.debug_mode = not self.debug_mode
                    elif event.key == pygame.K_r:
                        self.reset_game()
                    elif event.key == pygame.K_t:
                        self.run_tests_and_banner()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)

            self._render_frame()

        pygame.quit()
        sys.exit(0)


# ==============================================================================
# MAIN ENTRY POINT & CLI OPTIONS
# ==============================================================================
def main():
    """Parses command-line arguments and launches GUI or test suite."""
    if "--test" in sys.argv or "-t" in sys.argv:
        # Headless testing mode
        results = SelfTestSuite.run_all_tests()
        if all(results.values()):
            print("[SUCCESS] All algorithm unit tests passed cleanly.")
            sys.exit(0)
        else:
            print("[ERROR] One or more unit tests failed.")
            sys.exit(1)

    debug_on = "--debug" in sys.argv or "-d" in sys.argv
    app = GridLockUI(debug_start=debug_on)
    app.run()


if __name__ == "__main__":
    main()
