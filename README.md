## Notify_RT

Notify_RT is an icinga2 plugin which creates tickets in an external RT system when an icinga service/host goes critical.

### Installation
 - Create an icinga2 api user, a queue and user to create posts in RT
 - Copy `notify_rt.json` and `notify_rt.py` to `/etc/icinga2/scripts/`
 - Copy `notify-rt.conf` to `/etc/icinga2/zones.d/global-templates`
 - Modify the configuration files with a icinga2 api user and RT who has permissions to read, comment and create tickets in the rt queues
 - Set `vars.notify_rt = <queue name>` on the hosts and services you want to be notified about, the queue to post new tickets to is set here

### Dependencies
 - requests library `pip install requests` or `pip3`
 - To make RT ticket ID's clickable install [Icinga/icingaweb2-module-generictts](https://github.com/Icinga/icingaweb2-module-generictts)

### TODO
 - Better error logging
 - Set prefered resolution status for RT tickets in `notify_rt.json`
