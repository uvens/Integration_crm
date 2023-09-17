from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.serialization import load_pem_private_key
import csv
import os


def get_key():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    public_key = private_key.public_key()
    public_key_pem = public_key.public_bytes(encoding=serialization.Encoding.PEM,
                                             format=serialization.PublicFormat.SubjectPublicKeyInfo)

    with open('public_key.pem', 'wb') as f:
        f.write(public_key_pem)

    with open("private_key.pem", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    return public_key, private_key


def encrypt_user(file):
    public_key, _ = get_key()

    block_size = 446

    with open(file, 'rb') as f:
        data = f.read()

    encrypted_blocks = []
    for i in range(0, len(data), block_size):
        block = data[i:i + block_size]
        encrypted_block = public_key.encrypt(block, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                                                                 algorithm=hashes.SHA256(), label=None))
        encrypted_blocks.append(encrypted_block)

    with open(file.split('.')[0] + '_encrypt' + '.bin', 'wb') as f:
        for encrypted_block in encrypted_blocks:
            f.write(encrypted_block)

    os.remove(file)


def decrypt_user(file_name):
    with open("private_key.pem", "rb") as f:
        private_key = load_pem_private_key(f.read(), password=None)

    with open(file_name.split('.')[0] + '_encrypt' + '.bin', 'rb') as f:
        encrypted_data = f.read()

    decrypted_blocks = []
    block_size = 512

    for i in range(0, len(encrypted_data), block_size):
        encrypted_block = encrypted_data[i:i + block_size]
        decrypted_block = private_key.decrypt(encrypted_block, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                                                                            algorithm=hashes.SHA256(), label=None))
        decrypted_blocks.append(decrypted_block)

    decrypted_data = b''.join(decrypted_blocks)

    csv_data = csv.reader(decrypted_data.decode('utf-8').splitlines())
    return csv_data