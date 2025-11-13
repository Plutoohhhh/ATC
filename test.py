import re
from pathlib import Path

response = "09:53:53.1448|169.122.123.117"
lines = response.split('\n')
for line in lines:
    ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
    if ip_match:
        ip = ip_match.group(1)
        print(ip)
        print(Path.home())