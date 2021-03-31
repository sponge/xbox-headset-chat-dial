# Chat Dial Support for the Xbox Wireless Headset

Enables use of the chat volume dial of the Xbox Wireless Headset on Windows 10 PCs. When connected through the Xbox Wireless Adapter, turning the left ear cup will adjust the volume of a program separately from overall volume. This code is pretty hacky and experimental, but hopefully it works for you!

## Setup
1. Download and install Python 3. Python 3.8 is available from the Microsoft Store, and will work just fine.

2. Install [USBPcap](https://desowin.org/usbpcap/) to the default `c:\Program Files\USBPcap` location.

3. From the command line, run `pip install pywin32`

4. Install `pip install pycaw`

5. Double click `main.pyw` and hope for the best! You may need to accept a UAC prompt for USBPcap to launch successfully.

6. For best results, set Discord's output volume to 200%, and turn down the chat volume dial to a comfortable level.

## About

![Screenshot](screenshot.png?raw=true "Screenshot")

The Xbox Wireless Headset is a great little headset for the price, but on Windows 10 it is missing one feature I was most excited for. On the Xbox, adjusting the dial on the left ear cup will change the volume split of game audio, and chat audio. On a PC, however, nothing happens. There's no secondary output device to assign voice chat to, and if the feature is supported in Xbox parties, I'm never going to use Xbox party chat anyway.

When using the Xbox Wireless Adapter, I suspected that the headset was still sending the status to the device, and was just left unhandled by the `xboxgip.sys` driver in Windows. I found [USBPcap](https://desowin.org/usbpcap/), and loaded up Wireshark, hoping to sniff out the USB message.

Knowing very little about reverse engineering (and since the feature is unused, looking at the driver may not have even mattered) I started capturing packets from the headset, hoping to find a message that only appears when the knobs were turned. I assumed that the status messages would be pretty small. There were many packets that were ~1.4kb in size, these looked like they'd carry the audio to me. Filtering out large packets left me with still a decent flood of packets. This did reduce the amount enough to notice that turning the knob would cause a bunch of ~80 byte packets to be sent from the headset. This seemed promising!

Once I found the packet containing the message, the simplest way forward was to quickly turn the volume from minimum to maximum, hoping that I could catch a single byte value moving to and from 0. I got lucky and was able to find the two bytes, adjacent to each other, with a range from 0x00 to 0x60, or 0 to 100. This was definitely the dial status, however now I needed to be able to capture this value and do something with it programmatically.

I wasn't about to write my own USB filter driver to grab these packets on my own, and the USBPcap API is pretty gnarly for someone who doesn't work with USB. Thankfully, Wireshark has the ability to use external programs as a source of packets by invoking the program multiple times for configuration purposes, and then starting to capture packets from the program through a named pipe. USBPcap supports this protocol, since this is how I was using it in Wireshark in the first place.

Once I figured out the magic command line incantation, I was able to use Python to open and read the named pipe. I wasn't quite able to figure out the Wireshark packet protocol, but it didn't matter in the end as I could brute force search for the beginning of the packet I fished out earlier. When that header is found, the dial values are a fixed offset from there. I now had access to the dial value from within Python!

The last step was using the value to actually do something. I couldn't quite lower the system volume while raising the volume of a specific app, so instead the dial will set the Windows Mixer volume for a given process. I configured Discord to 200% output volume, and was able to lower the headset volume to get the balance right.

To my disbelief, all of this seemed to work, and seemed stable. I've been able to leave the program running, power cycle the headset, and come back the next day and it still works. I threw in a barebones UI, added the most barebones of error catching, and hope that it will now be useful for someone besides me.