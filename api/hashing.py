import base64
import hashlib

from django.contrib.auth import hashers

class SHA1WithBase64SaltHasher(hashers.SHA1PasswordHasher):
    algorithm='sha1-b64-salt'
    def encode(self, password, salt):
        raw_salt = base64.b64decode(salt)
        hash = hashlib.sha1(raw_salt+password).hexdigest()
        return "%s$%s$%s" % (self.algorithm, salt, hash)
    def salt(self):
        raw_result = super(SHA1WithBase64SaltHasher, self).salt()
        return base64.b64encode(raw_result)
