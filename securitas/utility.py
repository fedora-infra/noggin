import hashlib

def gravatar(email, size):
    return "https://www.gravatar.com/avatar/" + hashlib.md5(
        email.lower().encode('utf8')).hexdigest() + "?s=" + str(size) # nosec
