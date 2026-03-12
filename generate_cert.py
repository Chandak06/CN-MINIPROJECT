import os            # Used to build the output path relative to this script's location
import ipaddress     # Used to specify an IPv4 address in the SAN extension
import datetime      # Used to set the certificate's validity period
import argparse      # Used to accept custom SAN entries from command line
from cryptography import x509                                    # Core X.509 certificate building API
from cryptography.x509.oid import NameOID                        # Object Identifiers for certificate fields (CN, O, etc.)
from cryptography.hazmat.primitives import hashes, serialization # SHA-256 hashing and PEM serialization
from cryptography.hazmat.primitives.asymmetric import rsa        # RSA key pair generation

# Determine the security/ directory relative to this script regardless of where it is run from
SECURITY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "security")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate self-signed TLS cert for secure clock sync")
    parser.add_argument(
        "--ips",
        nargs="+",
        default=["127.0.0.1", "192.168.56.1"],
        help="IPv4 addresses to include in SAN (space-separated)",
    )
    parser.add_argument(
        "--dns",
        nargs="+",
        default=["localhost"],
        help="DNS names to include in SAN (space-separated)",
    )
    parser.add_argument(
        "--common-name",
        default="localhost",
        help="Certificate common name",
    )
    return parser.parse_args()


args = parse_args()

# Create the security/ directory if it does not already exist
os.makedirs(SECURITY_DIR, exist_ok=True)

# ── Step 1: Generate RSA Private Key ─────────────────────────────────────────
key = rsa.generate_private_key(
    public_exponent=65537,   # Standard RSA public exponent (widely used, cryptographically safe)
    key_size=2048             # 2048-bit key length — industry standard for good security
)

# ── Step 2: Define Certificate Subject and Issuer ────────────────────────────
# For a self-signed certificate, subject == issuer (the cert signs itself)
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME,             "IN"),               # 2-letter country code
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME,   "Karnataka"),        # State/province
    x509.NameAttribute(NameOID.LOCALITY_NAME,            "Bangalore"),        # City
    x509.NameAttribute(NameOID.ORGANIZATION_NAME,        "ClockSyncProject"), # Organisation name
    x509.NameAttribute(NameOID.COMMON_NAME,              args.common_name),    # Primary hostname the cert covers
])

san_entries = []
for dns_name in args.dns:
    san_entries.append(x509.DNSName(dns_name))

for ip_text in args.ips:
    try:
        san_entries.append(x509.IPAddress(ipaddress.IPv4Address(ip_text)))
    except ipaddress.AddressValueError as exc:
        raise ValueError(f"Invalid IPv4 address in --ips: {ip_text}") from exc

# ── Step 3: Get Current UTC Time ─────────────────────────────────────────────
# datetime.now(timezone.utc) is the modern replacement for the deprecated utcnow()
now = datetime.datetime.now(datetime.timezone.utc)

# ── Step 4: Build and Sign the Certificate ───────────────────────────────────
cert = (
    x509.CertificateBuilder()
    .subject_name(subject)                  # Who the certificate belongs to
    .issuer_name(issuer)                    # Who issued/signed the certificate (same entity = self-signed)
    .public_key(key.public_key())           # Embed the public key so clients can verify the server's identity
    .serial_number(x509.random_serial_number())  # Unique serial number for this certificate
    .not_valid_before(now)                  # Certificate is valid starting right now
    .not_valid_after(now + datetime.timedelta(days=365))  # Certificate expires in 1 year
    .add_extension(
        # Subject Alternative Name (SAN): specifies all hostnames/IPs this cert is valid for
        # Modern TLS libraries use SAN for hostname verification (CN alone is no longer sufficient)
        x509.SubjectAlternativeName(san_entries),
        critical=False,   # SAN is informational; not critical means clients won't reject the cert if they don't understand it
    )
    .sign(key, hashes.SHA256())   # Sign the certificate with our private key using SHA-256 — makes it self-signed
)

# ── Step 5: Write Private Key to Disk ────────────────────────────────────────
key_path  = os.path.join(SECURITY_DIR, "key.pem")
cert_path = os.path.join(SECURITY_DIR, "cert.pem")

with open(key_path, "wb") as f:
    f.write(key.private_bytes(
        encoding=serialization.Encoding.PEM,                         # PEM = Base64-encoded text format
        format=serialization.PrivateFormat.TraditionalOpenSSL,       # PKCS#1 format, compatible with OpenSSL
        encryption_algorithm=serialization.NoEncryption()           # Store key unencrypted (no passphrase)
    ))

# ── Step 6: Write Certificate to Disk ────────────────────────────────────────
with open(cert_path, "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))   # Write cert in PEM text format

print(f"Certificate : {cert_path}")
print(f"Private key : {key_path}")
print(f"Common Name : {args.common_name}")
print(f"SAN DNS     : {', '.join(args.dns)}")
print(f"SAN IPs     : {', '.join(args.ips)}")
print("Done.")
