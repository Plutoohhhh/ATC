import re

response = """Key  | Type | Data
SrNm | STR  | H2FJ1HX9WF
BMac | HEX  | A4 FC 14 13 11 66 00 00 00 00 00 00 00 00 00 00 
              
WSKU | HEX  | 01 00 00 00 00 00 00 00 58 30 00 00 00 00 00 00 
              
Mod# | STR  | 994-21265
BCAL | HEX  | 42 4C 4F 42 18 01 00 00 A6 A5 76 7C 01 00 00 00 """


# lines = response.split('\n')
# for line in lines:
#     if 'SrNm | STR  |' in line:
#         sn = line.split('|')[2].strip()
#         print(sn)
response = """sw-team@coreosMac-mini ~ % ifconfig | grep 'inet ' | grep -v 127.0.0.1 | head -1 | awk '{print $2}'
10.141.186.200"""

# 提取 IP 地址
lines = response.split('\n')
for line in lines:
    ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
    ip = ip_match.group(1)
    print(ip)