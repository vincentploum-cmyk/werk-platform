import os
import stat
from datetime import datetime, timedelta

# Generate self-signed SSL certs using Python's ssl module via OpenSSL CLI
import subprocess
import sys

key_dir = "/home/team/shared/code/werk/infrastructure/nginx/ssl"
os.makedirs(key_dir, exist_ok=True)

key_file = os.path.join(key_dir, "werk.key")
crt_file = os.path.join(key_dir, "werk.crt")

# Generate using openssl subprocess
result = subprocess.run(
    ["openssl", "req", "-x509", "-nodes", "-days", "365",
     "-newkey", "rsa:2048",
     "-keyout", key_file,
     "-out", crt_file,
     "-subj", "/C=US/ST=Dev/L=Local/O=Werk/CN=localhost"],
    capture_output=True, text=True, timeout=30
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)

if os.path.exists(key_file) and os.path.exists(crt_file):
    os.chmod(key_file, stat.S_IRUSR | stat.S_IWUSR)
    print(f"SSL certs generated successfully!")
    print(f"  Key:  {key_file} ({os.path.getsize(key_file)} bytes)")
    print(f"  Cert: {crt_file} ({os.path.getsize(crt_file)} bytes)")
else:
    print("ERROR: Cert generation failed")
    sys.exit(1)