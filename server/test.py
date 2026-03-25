import ntplib

client = ntplib.NTPClient()
response = client.request('in.pool.ntp.org', timeout=5)

print(response.tx_time)