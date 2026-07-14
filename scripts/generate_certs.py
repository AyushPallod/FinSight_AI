import os
import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# Script to dynamically generate a self-signed SSL certificate for FinSight local deployment


def generate_self_signed_cert():
    # Target directory is project_root/nginx/certs
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    certs_dir = os.path.join(project_root, "nginx", "certs")
    os.makedirs(certs_dir, exist_ok=True)

    key_path = os.path.join(certs_dir, "nginx.key")
    cert_path = os.path.join(certs_dir, "nginx.crt")

    # If certificates already exist, don't overwrite them
    if os.path.exists(key_path) and os.path.exists(cert_path):
        print("[*] SSL Certificates already exist. Skipping generation.")
        return

    print("[*] Generating self-signed SSL certificate for localhost...")

    # 1. Generate RSA private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # 2. Build x509 certificate subject/issuer properties
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "FinSight AI"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ]
    )

    # 3. Build certificate configuration
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
        )  # 1 year validity
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )

    # 4. Write private key PEM bytes to nginx.key
    with open(key_path, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    # 5. Write certificate PEM bytes to nginx.crt
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"[*] SSL Certificates successfully generated and saved to: {certs_dir}")



if __name__ == "__main__":
    generate_self_signed_cert()
