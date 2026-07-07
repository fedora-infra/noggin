from .base import Representation


class OTPToken(Representation):
    attr_names = {
        "uniqueid": "ipatokenuniqueid",
        "description": "description",
        "disabled": "ipatokendisabled",
        "counter": "ipatokenhotpcounter",
    }
    attr_types = {
        "disabled": "bool",
        "counter": "int",
    }
    pkey = "uniqueid"
    ipa_object = "otptoken"

    @property
    def uri(self):
        return self.raw.get('uri')

    def is_recovery(self, recovery_description):
        token_type = self.raw.get('type') or ''
        if isinstance(token_type, list):
            token_type = token_type[0] if token_type else ''
        return (
            token_type.lower() == 'hotp'
            and self.description == recovery_description
        )
