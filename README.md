MAIN  -doc and navod
PY -code

https://github.com/hailo-ai/tappas/tree/4341aa360b7f8b9eac9b2d3b26f79fca562b34e4/docs/write_your_own_application
docs/write_your_own_application

![image](https://github.com/user-attachments/assets/043bb26f-5244-4c0d-b257-0f60c9b807a2)

------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Cannot Allocate Memory in Static TLS Block
In some scenarios (especially aarch64), you might experience the following error causing some GStreamer plugins to not load correctly. The error message is:


bash
(gst-plugin-scanner:67): GStreamer-WARNING **: 12:20:39.178: Failed to load plugin '/usr/lib/aarch64-linux-gnu/gstreamer-1.0/libgstlibav.so': /lib/aarch64-linux-gnu/libgomp.so.1: cannot allocate memory in static TLS block
This issue should be fixed by adding this to your .bashrc file:

echo 'export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libgomp.so.1' >> ~/.bashrc
If you already encountered this error, you can fix it by running the following commands:

export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libgomp.so.1
rm ~/.cache/gstreamer-1.0/registry.aarch64.bin
