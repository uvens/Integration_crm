from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.serialization import load_pem_private_key
import csv
import os




def get_key():
    global private_key
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
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
    public_key, private_key = get_key()

    with open(file, 'r') as f:
        data = f.read().encode('utf-8')

    encrypted_data = public_key.encrypt(data, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                                                           algorithm=hashes.SHA256(), label=None))

    with open(file.split('.')[0] + '_encrypt' + '.bin', 'wb') as f:
        f.write(encrypted_data)

    os.remove(file)


def decrypt_user(file_name):
    with open("private_key.pem", "rb") as f:
        private_key = load_pem_private_key(f.read(), password=None)

    with open(file_name.split('.')[0] + '_encrypt' + '.bin', 'rb') as f:
        encrypted_data = f.read()

    decrypted_data = private_key.decrypt(encrypted_data, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                                                                      algorithm=hashes.SHA256(), label=None))
    csv_data = csv.reader(decrypted_data.decode('utf-8').splitlines())
    return csv_data
