from noggin.representation import Representation


class OTPToken(Representation):

    ATTR_MAP = {
        "uniqueid": "ipatokenuniqueid",
        "description": "description",
        "disabled": "ipatokendisabled",
    }

    pkey = "uniqueid"
    ipa_object = "otptoken"

    @property
    def uri(self):
        return self.raw.get('uri')
