====
hpio
====

Heat pump IO client


Features
--------

* TODO

Requirements
--------

Install Python serial libry.
- Run: sudo apt-get install python-serial

Setup Serial GPIO porta. 
- Edit: /boot/cmdline.txt. Remove text: console=serial0,115200b. 
- Edit: /boot/config.txt. Add enable_uart=1
- Edit: /boot/config.txt. Add dtoverlay=pi3-disable-bt (if rasberry pi 3)
