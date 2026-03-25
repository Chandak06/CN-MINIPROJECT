import ntplib

client = ntplib.NTPClient()
response = client.request('time.google.com', timeout=5)

print(response.tx_time)