import win32pipe, win32file, pywintypes
import subprocess
import re
import threading
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
from tkinter import *
from tkinter.ttk import *

process_name = "Discord.exe"

volume_val = -1
split_val = -1
connected = False
received_packets = False
got_error = False
error_text = ""
usbpcap_process = None
do_xfade = True
xfade_shape = 1

split_label = None
split_progress = None
volume_label = None
volume_progress = None
status_label = None
abort_thread = False

def find_device():
    value_str = r"{value=(.*)}{"
    value_num = r"{value=(\d*)}{display=(.*)}{"

    ifaces = subprocess.check_output(['c:/Program Files/USBPcap/USBPcapCMD.exe', '--extcap-interfaces'])
    for match in re.finditer(value_str, ifaces.decode('utf-8')):
        iface = match.group(1)
        devices = subprocess.check_output(['c:/Program Files/USBPcap/USBPcapCMD.exe', '--extcap-interface', iface, '--extcap-config']).decode('utf-8').split('\r\n')
        for dev in devices:
            if 'Xbox Wireless Adapter for Windows' in dev:
                for dev_match in re.finditer(value_num, dev):
                    return (iface, dev_match.group(1), dev_match.group(2))

def convert_xfade(val):
    if xfade_shape == 1:
        if val <= 50:
            return val / 50
        else:
            return 1
    else:
        return val / 100
                
def pipe_reader():
    global volume_val
    global split_val
    global connected
    global process_name
    global received_packets
    global abort_thread
    global got_error
    global error_text

    try:
        pipe = win32pipe.CreateNamedPipe(
            r'\\.\pipe\Dog',
            win32pipe.PIPE_ACCESS_DUPLEX,
            win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
            1, 65536, 65536,
            0,
            None)
    except Exception as e:
        got_error = True
        error_text = str(e)
        return

    win32pipe.ConnectNamedPipe(pipe, None)
    connected = True

    while True:
        if abort_thread:
            return

        err, resp = win32file.ReadFile(pipe, 64*1024)

        if err != 0:
            got_error = True
            error_text = "Failed to read from pipe"
            return

        if len(resp):
            received_packets = True

        found = resp.find(b'\x48\x00\xc0\x4a')
        if found == -1:
            continue

        volume_offs = found + 70
        split_offs = found + 71
        if (split_offs > len(resp)):
            print(":(")
            continue

        volume_val = resp[volume_offs]
        split_val = resp[split_offs]

        # this seems to happen when the headphones turn on, so ignore it
        if volume_val == 0 and split_val == 1:
            continue

        sessions = AudioUtilities.GetAllSessions()
        for session in sessions:
            volume = session._ctl.QueryInterface(ISimpleAudioVolume)
            if session.Process and session.Process.name() == process_name:
                volume.SetMasterVolume(convert_xfade(split_val), None)
            elif do_xfade:
                volume.SetMasterVolume(convert_xfade(100 - split_val), None)

def tick():
    usbpcap_process.poll()
    if usbpcap_process.returncode is not None:
        status_label.configure(text = f"Error: USBPcap process exited unexpectedly.")
    elif got_error:
        status_label.configure(text = f"Error: {error_text}")
    elif received_packets:
        num_procs = len([s for s in AudioUtilities.GetAllSessions() if s.Process and s.Process.name() == process_name])
        text = f"Adjusting volume for {num_procs} {process_name} session"
        if num_procs > 1:
            text += "s"
        status_label.configure(text = text)

    if connected and volume_val == -1:
        split_label.configure(text = f'App Volume: Adjust dial to start...')
        split_progress['mode'] = 'indeterminate'
        split_progress['value'] += 1
        volume_label.configure(text = f'Volume: Adjust dial to start...')
        volume_progress['mode'] = 'indeterminate'
        volume_progress['value'] += 1
    elif connected or (volume_val == 0 and split_val == 1):
        split_label.configure(text = f'App Volume: {split_val}')
        split_progress['value'] = split_val
        split_progress['mode'] = 'determinate'
        volume_label.configure(text = f'Volume: {volume_val}')
        volume_progress['value'] = volume_val
        volume_progress['mode'] = 'determinate'
    else:
        split_label.configure(text = f'App Volume: Connecting...')
        split_progress['mode'] = 'indeterminate'
        split_progress['value'] += 1
        volume_label.configure(text = f'Volume: Connecting...')
        volume_progress['mode'] = 'indeterminate'
        volume_progress['value'] += 1

    window.after(20, tick)

if __name__ == "__main__":
    iface, dev, dev_name = find_device()
    
    window = Tk()
    window.title('Headset Dial Monitor')
    window.geometry("300x220")

    padding_x = 15
    padding_y = 5

    iface_label = Label(window, text=f'Interface: {iface}').pack(side=TOP, anchor=W, padx=padding_x, pady=padding_y)

    dev_label = Label(window, text=f'Device: {dev_name}').pack(side=TOP, anchor=W, padx=padding_x, pady=0)

    status_label = Label(window, text="No packets received yet...")
    status_label.pack(side=TOP, anchor=W, padx=padding_x, pady=padding_y)

    split_label = Label(window, text="")
    split_label.pack(side=TOP, anchor=W, padx=padding_x, pady=padding_y)

    split_progress = Progressbar(window, orient=HORIZONTAL, length=100)
    split_progress.pack(fill=X, padx=padding_x, pady=padding_y)

    volume_label = Label(window, text="")
    volume_label.pack(side=TOP, anchor=W, padx=padding_x, pady=padding_y)

    volume_progress = Progressbar(window, orient=HORIZONTAL, length=100)
    volume_progress.pack(fill=X, padx=padding_x, pady=padding_y)

    t = threading.Thread(target=pipe_reader)
    t.start()

    cmd = ['c:/Program Files/USBPcap/USBPcapCMD.exe',
    '--capture',
    '--extcap-interface', iface,
    '--fifo', r'\\.\pipe\Dog',
    '--snaplen', '65535', 
    '--bufferlen', '1048576',
    '--devices', dev]
    usbpcap_process = subprocess.Popen(cmd)

    window.after(20, tick)
    window.mainloop()
    abort_thread = True
    t.join()
