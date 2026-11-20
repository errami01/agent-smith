from dotenv import load_dotenv

import json
import os
import subprocess
import time

def main(tag="baseline"):
    load_dotenv()
    with open("student/benchmark/configs.json", "r") as file:
        config = json.load(file)
    os.makedirs("benchmark_results", exist_ok=True)
    if os.path.exists("benchmark_results/validations.json"):
        with open("benchmark_results/validations.json") as file:
            validations = json.load(file)
    else:
        validations = {}

    for task_path in config["tasks"]:
        with open(task_path) as f:
            task = json.load(f)
        image_tag = f"smith-{task['instance_id'].lower()}"
        subprocess.run(["docker", "build", "--build-arg",  f"BASE_IMAGE={task['docker_image']}", "-t", image_tag, "."], check=True)

        for model in config['model']:
            safe_id = model["id"].replace("/", "-")
            run_name = f"{tag}__{safe_id}__{task['instance_id']}"
            out_file = f"benchmark_results/{run_name}.json"

            if os.path.exists(out_file):
                print(f"SKIP {run_name}")
                continue

            api_key = os.getenv(model["api_key_env"], "")
            try:
                subprocess.run([
                    "docker", "run", "--rm", 
                    "-e", f"{model['api_key_env']}={api_key}",
                    "-v", f"{os.path.abspath(task_path)}:/task.json:ro",
                    "-v", f"{os.path.abspath('benchmark_results')}:/out",
                    image_tag,
                    "uv", "run", "python", "-m", "student.agent_swebench",
                    "--task-file", "/task.json",
                    "--output", f"/out/{run_name}.json",
                    "--model-name", model["model_name"],
                    "--provider-url", model["provider_url"],
                ], timeout=930)
            except subprocess.TimeoutExpired:
                    pass

            if os.path.exists(out_file):
                status = subprocess.run(
                    ["uv", "run", "moulinette_eval", "validate", "swebench",
                    os.path.abspath(task_path), os.path.abspath(out_file)],
                    cwd="moulinette/moulinette")
                validations[run_name] = (status.returncode == 0)
                with open("benchmark_results/validations.json", "w") as f:
                    json.dump(validations, f, indent=2)
                print(f"{run_name}: {validations}")
            else:
                validations[run_name] = False
                print(f"{run_name}: CRASHED/TIMEOUT" )

if __name__ == "__main__":
    main()