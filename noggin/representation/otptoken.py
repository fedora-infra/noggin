from noggin.representation import Representation


class OTPToken(Representation):
    @property
    def uniqueid(self):
        return self._attr('ipatokenuniqueid')

    @property
    def description(self):
        return self._attr('description')

    @property
    def disabled(self):
        return self._attr('ipatokendisabled')

    @property
    def uri(self):
        return self.raw.get('uri')
