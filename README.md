Sync a Text file to uptime-kuma to create checks in bulk
It is possible to check for timeouts, keywords, and status codes

There is also a check_mk plugin that can be used to monitor the uptime-kuma checks
at https://github.com/styliteag/uptime-kuma-checkmk-plugin

```shell

# Prequisites:
apt install python-dotenv
apt install python3-pip
pip install uptime-kuma-api --break-system-packages



./sync_text2kuma.py -f example.txt -c example.ini -u

# Sync text to kuma 
./sync_text2kuma.py -f data/stylite_urls.txt -c data/stylite.ini -u -r
./sync_text2kuma.py -f data/sigma_urls.txt -c data/sigma.ini -u -r


```

hen