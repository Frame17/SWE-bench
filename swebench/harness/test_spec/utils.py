from swebench.harness.constants import (
    END_TEST_OUTPUT,
    MAP_REPO_VERSION_TO_SPECS,
    START_TEST_OUTPUT,
)
from swebench.harness.utils import get_modified_files


# MARK: Test Command Creation Functions


def get_test_cmds(instance) -> list:
    test_cmd = MAP_REPO_VERSION_TO_SPECS[instance["repo"]][instance["version"]][
        "test_cmd"
    ]
    return [test_cmd] if isinstance(test_cmd, str) else test_cmd


# MARK: Script Creation Functions


def make_repo_script_list_common(
    specs, repo, repo_directory, base_commit, env_name
) -> list:
    """
    Create a list of bash commands to set up the repository for testing.
    This is the setup script for the instance image.
    """
    setup_commands = [
        f"git clone -o origin https://github.com/{repo} {repo_directory}",
        f"chmod -R 777 {repo_directory}",  # So nonroot user can run tests
        f"cd {repo_directory}",
        f"git reset --hard {base_commit}",
        "git remote remove origin",  # Remove the remote so the agent won't see newer commits
        # After the repository is set up, convert any Gradle wrapper distribution URLs that
        # reference "-all.zip" to the smaller "-bin.zip" distribution. Doing this here
        # (in the generated setup_repo.sh) avoids a Dockerfile-specific RUN step and
        # prevents downloading larger 'all' distributions during builds inside the image.
        f"find {repo_directory} -type f -path '*/gradle/wrapper/gradle-wrapper.properties' -exec sed -i -E \"s#(distributionUrl=.*)-all(\\.zip)#\\1-bin\\2#g\" {{}} + || true",
    ]
    if "pre_install" in specs:
        setup_commands.extend(specs["pre_install"])
    if "install" in specs:
        setup_commands.extend(specs["install"])
    if "build" in specs:
        setup_commands.extend(specs["build"])
    return setup_commands


def make_env_script_list_common(instance, specs, env_name) -> list:
    """
    Creates the list of commands to set up the environment for testing.
    This is the setup script for the environment image.
    """
    reqs_commands = []
    if "apt-pkgs" in specs:
        reqs_commands += [
            "apt-get update",
            f"apt-get install -y {' '.join(specs['apt-pkgs'])}",
        ]
    return reqs_commands


def make_eval_script_list_common(
    instance, specs, env_name, repo_directory, base_commit, test_patch
) -> list:
    """
    Applies the test patch and runs the tests.
    """
    HEREDOC_DELIMITER = "EOF_114329324912"
    test_files = get_modified_files(test_patch)
    # Reset test files to the state they should be in before the patch.
    if test_files:
        reset_tests_command = f"git checkout {base_commit} {' '.join(test_files)}"
    else:
        reset_tests_command = 'echo "No test files to reset"'

    build_commands = []
    if "build" in specs:
        build_commands.extend(specs["build"])

    apply_test_patch_command = f"git apply --verbose --reject - <<'{HEREDOC_DELIMITER}'\n{test_patch}\n{HEREDOC_DELIMITER}"
    test_commands = get_test_cmds(instance)
    eval_commands = [
        f"cd {repo_directory}",
        f"git config --global --add safe.directory {repo_directory}",  # for nonroot user
        f"cd {repo_directory}",
        # This is just informational, so we have a record
        # f"git status",
        # f"git show",
        # f"git -c core.fileMode=false diff {base_commit}",
        reset_tests_command,
        apply_test_patch_command,
        *build_commands,
        f": '{START_TEST_OUTPUT}'",
        *test_commands,
        f": '{END_TEST_OUTPUT}'",
        reset_tests_command,
    ]
    return eval_commands
