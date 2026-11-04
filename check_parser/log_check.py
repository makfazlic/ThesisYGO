import sys
import json
import os
from multiprocessing import Process, freeze_support

sys.path.append(os.path.abspath(".."))

from check_parser.db_capture_regular_browser import capture_replay_state
from parser.parser_fixed import parse_replay
from simulator.game_ui import run_replay_viewer


def main():
    replay_path = sys.argv[1]

    with open(replay_path, "r", encoding="utf-8") as file:
        game_log = json.load(file)

    game_id = game_log["id"]
    print(f"Game ID: {game_id}")

    # Parse replay
    parser_result = parse_replay(game_log)
    parsed_state = parser_result["final_state"]
    pairs = parser_result["pairs"]
    last_pair = [pairs[-1]]

    # Capture state ONLY ONCE
    extracted_state = capture_replay_state(game_id)
    extracted_state_action = [
        {"action": "Extracted State", "state": extracted_state}
    ]

    # Launch two independent viewer windows
    p1 = Process(target=run_replay_viewer, args=(last_pair,))
    p2 = Process(target=run_replay_viewer, args=(extracted_state_action,))

    p1.start()
    p2.start()

    p1.join()
    p2.join()


if __name__ == "__main__":
    freeze_support()
    main()