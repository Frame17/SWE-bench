import os
import re
import json


def analyze_build_logs(instances_dir):
    results = []

    if not os.path.exists(instances_dir):
        print(f"Directory {instances_dir} does not exist.")
        return results

    for instance_name in sorted(os.listdir(instances_dir)):
        instance_path = os.path.join(instances_dir, instance_name)
        if not os.path.isdir(instance_path):
            continue

        log_path = os.path.join(instance_path, "build_image.log")
        if not os.path.exists(log_path):
            results.append({
                "instance": instance_name,
                "status": "missing_log",
                "error": "build_image.log not found"
            })
            continue

        with open(log_path, 'r', errors='ignore') as f:
            lines = f.readlines()

        content = "".join(lines)

        if any(kw in content for kw in ["Image built successfully!", "Successfully built", "BUILD SUCCESSFUL"]):
            results.append({
                "instance": instance_name,
                "status": "success"
            })
        else:
            # Try to find the error
            error_msg = "Unknown error"

            # Look for common failure indicators
            # Sophisticated OOM detection: avoid matching it in command line arguments
            oom_match = re.search(r"(?<!\+HeapDumpOn)(OutOfMemoryError.*)", content)
            if oom_match:
                error_msg = oom_match.group(1).strip()
            else:
                # Find the line that caused the non-zero code
                # Usually it's a few lines before the final ERROR
                docker_error_match = re.search(r"ERROR - docker\.errors\.BuildError during (.*?): (.*)", content)
                if docker_error_match:
                    instance_tag = docker_error_match.group(1)
                    generic_error = docker_error_match.group(2)

                    # Try to find a more specific error before this one
                    # Look for 'fatal:', 'ERROR:', 'FAILURE:', or just the last few lines of INFO before the error
                    specific_error = None
                    for i in range(len(lines) - 1, -1, -1):
                        if "ERROR - docker.errors.BuildError" in lines[i]:
                            # Start looking backwards from here
                            for j in range(i - 1, max(-1, i - 20), -1):
                                line = lines[j]
                                if any(kw in line for kw in
                                       ["fatal:", "ERROR:", "FAILURE:", "BUILD FAILED",
                                        "Permission denied", "not found", "No such file"]):
                                    specific_error = line.strip()
                                    break
                                if "OutOfMemoryError" in line and "+HeapDumpOn" not in line:
                                    specific_error = line.strip()
                                    break
                                if "/root/setup_repo.sh: line" in line:
                                    specific_error = line.strip()
                                    break
                            if specific_error:
                                break

                    if specific_error:
                        error_msg = f"{specific_error} | {generic_error}"
                    else:
                        error_msg = generic_error
                else:
                    # Last ditch effort: last 5 lines that aren't empty or generic "Removed intermediate container"
                    relevant_lines = [l for l in lines if l.strip() and "---> Removed intermediate container" not in l]
                    if relevant_lines:
                        error_msg = " | ".join([l.strip() for l in relevant_lines[-2:]])

            results.append({
                "instance": instance_name,
                "status": "failure",
                "error": error_msg
            })

    return results


if __name__ == "__main__":
    logs_dir = "logs/build_images/instances"
    analysis = analyze_build_logs(logs_dir)

    success_count = sum(1 for r in analysis if r['status'] == 'success')
    failure_count = sum(1 for r in analysis if r['status'] == 'failure')
    missing_count = sum(1 for r in analysis if r['status'] == 'missing_log')

    print(f"Total instances: {len(analysis)}")
    print(f"Success: {success_count}")
    print(f"Failure: {failure_count}")
    if missing_count:
        print(f"Missing logs: {missing_count}")
    print("-" * 40)

    for r in analysis:
        if r['status'] != 'success':
            print(f"Instance: {r['instance']}")
            print(f"Status:   {r['status']}")
            print(f"Error:    {r.get('error', 'N/A')}")
            print("-" * 20)

    # Also save to a JSON file for further use
    with open("build_analysis.json", "w") as f:
        json.dump(analysis, f, indent=4)
    print(f"Analysis saved to build_analysis.json")
