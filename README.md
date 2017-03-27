## Notify_RT

Notify_RT is an icinga2 plugin which creates tickets in an external RT system when an icinga service/host goes critical.

### Installation
 - Create an icinga2 api user, a queue and user to create posts in RT
 - Copy `notify_rt.json` and `notify_rt.py` to `/etc/icinga2/scripts/`
 - Copy `notify-rt.conf` to `/etc/icinga2/zones.d/global-templates`
 - Modify the configuration files appropriately
 - Set `var.notify_rt = "enabled"` on the hosts you want checked

### Dependencies
 - requests library `pip install requests` or `pip3`

### TODO
 - Better error logging
 - Set prefered resolution status for RT tickets in `notify_rt.json`
