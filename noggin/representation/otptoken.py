from .base import Representation


class OTPToken(Representation):

    attr_names = {
        "uniqueid": "ipatokenuniqueid",
        "description": "description",
        "disabled": "ipatokendisabled",
    }
    attr_types = {
        "disabled": "bool",
    }
    pkey = "uniqueid"
    ipa_object = "otptoken"

    @property
    def uri(self):
        return self.raw.get('uri')
