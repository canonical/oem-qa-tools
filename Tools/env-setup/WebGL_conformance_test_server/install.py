import subprocess
import os

REPO_URL = "https://github.com/KhronosGroup/WebGL.git"
REPO_NAME = "WebGL"

WEBGL_TESTS_PATH = "/var/www/webgl_tests"
CLONE_PATH = os.path.join(WEBGL_TESTS_PATH, "sdk", "tests")

NGINX_CONFIG_FILE = "webgl_tests.conf"
NGINX_SITES_AVAILABLE = "/etc/nginx/sites-available/"
NGINX_SITES_ENABLED = "/etc/nginx/sites-enabled/"


def run_command(command, message):
    """
    Executes a shell command and provides feedback.
    """
    print(f"\n[INFO] {message}")
    try:
        subprocess.run(command, check=True, shell=True)
        print("[SUCCESS] Command executed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed with exit code {e.returncode}.")
        print(f"       Command: {command}")
        if e.output:
            print(f"       Output: {e.output}")
        exit(1)


def configure_firewall():
    """
    Checks and configures the UFW firewall to allow Nginx.
    """
    print("\n[INFO] Checking firewall status...")
    try:
        ufw_status = subprocess.run(
            "ufw status | grep 'Status: active'",
            shell=True,
            check=False,
            capture_output=True,
            text=True,
        )
        if ufw_status.returncode == 0:
            print(
                "[INFO] UFW is active. Configuring firewall"
                " to allow Nginx Full profile."
            )
            run_command(
                "ufw allow 'Nginx Full'",
                "Allowing Nginx traffic through the firewall...",
            )
        else:
            print(
                "[INFO] UFW is not active or is not installed."
                "Skipping firewall configuration."
            )
    except Exception as e:
        print(f"[ERROR] An error occurred while checking firewall status: {e}")


def main():
    """
    Main function to execute the setup steps.
    """
    print("Starting WebGL Nginx Server Setup...")

    # Step 1: Clone the WebGL repository
    if not os.path.exists(WEBGL_TESTS_PATH):
        # Create the directory if it doesn't exist
        run_command(
            f"mkdir -p {WEBGL_TESTS_PATH}",
            "Creating web server root directory...",
        )
        run_command(
            f"git clone {REPO_URL} {WEBGL_TESTS_PATH}",
            "Cloning WebGL repository to fixed location...",
        )
        # copy and patch for local testing
        run_command(
            "cp {}{}webgl-conformance-tests.html {}{}local-tests.html".format(
                WEBGL_TESTS_PATH,
                "/sdk/tests/",
                WEBGL_TESTS_PATH,
                "/sdk/tests/",
            ),
            "Copy webgl-conformance-tests.html to local-tests.html...",
        )
        run_command(
            f"patch {WEBGL_TESTS_PATH}/sdk/tests/local-tests.html local.patch",
            "Patch local-tests.html to download result automatically...",
        )
        # Ensure the user has ownership of the directory for future permissions
        run_command(
            f"chown -R $USER:$USER {WEBGL_TESTS_PATH}",
            "Setting correct file permissions...",
        )
    else:
        print(
            "\n[INFO] Directory '{}' already exists. Skipping clone.".format(
                WEBGL_TESTS_PATH
            )
        )

    # Step 2: Install and configure Nginx
    # Update package lists
    run_command("apt-get update", "Updating package lists...")

    # Install Nginx
    run_command("apt-get install -y nginx", "Installing Nginx...")

    # Step 3: Create Nginx configuration file for WebGL tests
    nginx_conf_content = f"""
server {{
    listen 80;
    server_name localhost;

    root {CLONE_PATH};
    index index.html;

    location / {{
        # First attempt to serve request as file, then as directory
        try_files $uri $uri/ =404;
    }}
}}
"""
    local_conf_path = NGINX_CONFIG_FILE
    with open(local_conf_path, "w") as f:
        f.write(nginx_conf_content)

    print(f"\n[INFO] Created Nginx configuration file: {local_conf_path}")

    # Step 4: Move configuration to sites-available and link to sites-enabled
    run_command(
        f"mv {local_conf_path} {NGINX_SITES_AVAILABLE}",
        "Moving configuration file to Nginx's sites-available directory...",
    )

    # Remove default site configuration
    run_command(
        f"rm -f {NGINX_SITES_ENABLED}default",
        "Removing default Nginx configuration link...",
    )

    # Create symbolic link to enable the new site
    run_command(
        "ln -s {}{} {}".format(
            NGINX_SITES_AVAILABLE, NGINX_CONFIG_FILE, NGINX_SITES_ENABLED
        ),
        "Creating symbolic link to enable the new site...",
    )

    # Step 5: Configure firewall
    configure_firewall()

    # Step 6: Restart Nginx to apply changes
    run_command("systemctl restart nginx", "Restarting Nginx service...")

    print("\n[SUCCESS] WebGL server setup complete!")


if __name__ == "__main__":
    main()
