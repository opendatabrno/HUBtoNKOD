class TypeMatcher():

    def __init__(self, mapping):
        self.mapping = mapping

    def make_url(self, code):
        return 'http://publications.europa.eu/resource/authority/file-type/{}'.format(code)

    def find_match(self, name, mimetype):
        by_name = self.mapping.xpath('.//lg.version[@lg="eng"][normalize-space()=$name]/ancestor::record', name=name)
        if by_name:
            authority = by_name[0].find('authority-code').text
            return self.make_url(authority)

        by_mime = self.mapping.xpath('.//internet-media-type[normalize-space()=$mime]/ancestor::record', mime=mimetype)
        if by_mime:
            authority = by_mime[0].find('authority-code').text
            return self.make_url(authority)

        return make_url('OCTET')

