import os
import psutil


def get_pem_port(process_name='LeagueClientUx.exe'):

    # Find the process
    process = None
    for p in psutil.process_iter(['name']):
        if p.info['name'] == process_name:
            process = p
            break

    if process is None:
        raise ValueError(f"No Process called '{process_name}' found!")
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
                    raise ValueError("Lockfile data is invalid")
        else:
            raise ValueError("Lockfile not found")

if __name__ == "__main__":
    print(get_pem_port())
