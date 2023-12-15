import os
import re


pattern = re.compile(r'([^\n:]+?):\s+(.+)')


def regex_extract(input):
    result = {}
    groups = pattern.findall(input)
    for group in groups:
        result[group[0]] = group[1]
    return result


def plugin(kernel, lifecycle):
    """
    Proof of concept for driver switching within MeerK40t.

    @param kernel:
    @param lifecycle:
    @return:
    """
    if lifecycle == "register":
        _ = kernel.translation

        @kernel.console_option("source_dir", "d", type=str, help="Directory where you have placed the drivers to install")
        @kernel.console_command(
            "driver_install",
            help=_("install driver"),
        )
        def driver_install(command, channel, _, source_dir=None, **kwgs):
            import subprocess
            import ctypes
            vid = "9588"
            pid = "9899"

            # Find existing drivers assigned to specified VID/PID
            # This doesn't require elevated privileges
            list_process = r'pnputil.exe /enum-devices /deviceid USB\VID_{0}&PID_{1}'.format(vid, pid)
            p = subprocess.Popen(list_process, shell=False, stdout=subprocess.PIPE, universal_newlines=True)
            output = p.stdout.read()
            result = regex_extract(output)
            if result == {}:
                channel("Could not find laser with the VID/PID: {0}/{1}".format(vid, pid))
                return
            channel(str(result))

            # Couldn't find existing device. Probably in future we can change this
            # so that it just doesn't do the delete when the previous device doesn't exist
            if 'args' not in kwgs: return

            # Existing driver found. Delete it using elevated privileges
            prev_driver = result['Driver Name']
            ctypes.windll.shell32.ShellExecuteW(None, "runas", "pnputil.exe",
                                                '/delete-driver {0} /force'.format(prev_driver), None, 1)

            # Massage source directory where the new drivers should be found
            if source_dir is None:
                source_dir = os.path.expanduser('~') + '\\Downloads\\balor-drivers\\'
            if not source_dir.endswith('\\'):
                source_dir += '\\'

            # Install the appropriately requested driver with elevated privileges.
            requested_driver = kwgs['args'][0]
            if requested_driver == "meerk40t":
                args = '/add-driver {0}{1} /install'.format(source_dir, "MeerK40t_Balor.inf")
            elif requested_driver == "ezcad":
                args = '/add-driver {0}{1} /install'.format(source_dir, "Lmcv2u.inf")
            ctypes.windll.shell32.ShellExecuteW(None, "runas", "pnputil.exe", args, None, 1)

