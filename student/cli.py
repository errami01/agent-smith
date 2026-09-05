import sys
import json
import argparse
from typing import List
from student.sandbox import Sandbox
from student.schema import SandboxConfig


def main_sandbox() -> None:
    """Entry point for the interactive sandbox CLI."""
    parser = argparse.ArgumentParser(description="Agent Smith Sandbox CLI")
    parser.add_argument("config_file", nargs="?", help="Path to config JSON")
    args = parser.parse_args()

    # Load config if provided, else use defaults
    config = SandboxConfig()
    if args.config_file:
        try:
            with open(args.config_file, "r") as f:
                config_data = json.load(f)
                config = SandboxConfig(**config_data)
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)

    sandbox = Sandbox(config)
    print(f"Interactive Sandbox (Python {sys.version.split()[0]})")
    print("Type 'exit' or Ctrl+D to quit.")

    while True:
        try:
            user_input = input(">>> ")
            if user_input.lower() in ("exit", "exit()", "quit()"):
                break
            
            # Execute and print results
            output = sandbox.run_code(user_input)
            if output:
                print(output, end="" if output.endswith("\n") else "\n")

        except EOFError:
            print("\nExiting...")
            break
        except KeyboardInterrupt:
            # Chapter V.2: KeyboardInterrupt must reach the loop for shutdown
            print("\nKeyboardInterrupt")
            break
        except Exception as e:
            print(f"CLI Error: {e}")


if __name__ == "__main__":
    main_sandbox()