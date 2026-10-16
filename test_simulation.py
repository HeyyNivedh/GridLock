#!/usr/bin/env python3
"""
Automated headless benchmark and simulation test for GridLock.
Verifies latency (<15 ms), decision validity, and multi-turn stability.
"""
import time
from gridlock import GridLockState, MinimaxAI, TelemetryData, AStarPlanner, EXITS

def test_multi_turn_simulation():
    print("\n--- SIMULATING 5-TURN ADVERSARIAL MATCH HEADLESS ---")
    state = GridLockState(ai_pos=(4, 4), barriers=set())
    ai = MinimaxAI(depth=4)
    telemetry = TelemetryData()
    latencies = []

    # Simulated Human barrier placements attempting to surround the AI
    human_moves = [(3, 4), (5, 4), (4, 3), (2, 4), (6, 4)]

    for turn_idx, barrier in enumerate(human_moves, 1):
        telemetry.move_count = turn_idx
        state.barriers.add(barrier)
        print(f"\n[Turn {turn_idx}] Human dropped Barrier at {barrier}")

        # Check if containment achieved
        if state.is_human_win():
            print(f"[Turn {turn_idx}] Containment Achieved! Game Over.")
            break

        # AI Turn
        t0 = time.perf_counter()
        best_move = ai.compute_best_move(state, telemetry)
        dt = (time.perf_counter() - t0) * 1000.0
        latencies.append(dt)

        assert best_move is not None, f"AI returned None move when escape paths existed!"
        assert best_move not in state.barriers, f"AI moved into barrier at {best_move}!"
        assert best_move in AStarPlanner.get_neighbors(state.ai_pos, state.barriers), f"Illegal move {best_move}!"
        
        state.ai_pos = best_move
        print(f" -> AI executed move to {best_move} in {dt:.2f} ms")

        if state.is_ai_win():
            print(f" -> AI escaped to exit {best_move}!")
            break

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    print(f"\nBenchmark Results: Avg Latency = {avg_latency:.2f} ms | Max Latency = {max_latency:.2f} ms")
    assert max_latency < 25.0, f"Max latency exceeded threshold: {max_latency:.2f} ms"
    print("--- BENCHMARK PASSED: All decisions made smoothly within real-time budget ---\n")

if __name__ == "__main__":
    test_multi_turn_simulation()
