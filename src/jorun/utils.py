import platform
import subprocess
import sys
import os


def get_process_group_args():
    """
    This function will generate the right arguments for the `Popen` function to create a process in
    a new process group. This is needed because when we stop a task, we send a signal to the process.
    If the child process is in the same process group as the father, the father will receive the signal too.
    """
    kwargs = {}
    if platform.system() == "Windows":
        # subprocess.DETACHED_PROCESS should not be needed
        kwargs.update(creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    elif sys.version_info < (3, 2):
        kwargs.update(preexec_fn=os.setsid)
    else:
        kwargs.update(start_new_session=True)

    return kwargs
