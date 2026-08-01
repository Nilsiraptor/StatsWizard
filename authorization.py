import os
import psutil


class ConnectionError(Exception):
    """Exception raised when a connection to the League of Legends client fails."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def get_pem_port(process_name='LeagueClientUx.exe'):
    """Retrieves the PEM port and password from the League client lockfile.

    Scans running processes for the League of Legends client, reads its
    lockfile, and returns the PEM authentication credentials.

    Args:
        process_name: The name of the League client process to search for.
            Defaults to 'LeagueClientUx.exe'.

    Returns:
        A tuple of (password, port) strings extracted from the lockfile.

    Raises:
        ConnectionError: If the League client process is not found, the
            lockfile does not exist, or the lockfile data is invalid.
    """

    # Find the process
    process = None
    for p in psutil.process_iter(['name']):
        if p.info['name'] == process_name:
            process = p
            break

    if process is None:
        raise ConnectionError(f"No Process called '{process_name}' found!")
    else:
        # Get the path of the process executable
        executable_path = process.exe()
        process_dir = os.path.dirname(executable_path)

        # Check if the lockfile exists
        lockfile_path = os.path.join(process_dir, 'lockfile')
        if os.path.exists(lockfile_path):
            with open(lockfile_path, 'r') as lockfile:
                lockfile_data = lockfile.read().strip().split(':')
                if len(lockfile_data) >= 4:
                    password = lockfile_data[3]
                    port = lockfile_data[2]
                    return password, port
                else:
                    raise ConnectionError("Lockfile data is invalid")
        else:
            raise ConnectionError("Lockfile not found")

if __name__ == "__main__":
    print(get_pem_port())
