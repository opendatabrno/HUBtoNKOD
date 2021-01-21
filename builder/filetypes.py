class TypeMatcher():

    def __init__(self, mapping):
        self.mapping = mapping

    def make_url(self, code):
        return 'http://publications.europa.eu/resource/authority/file-type/{}'.format(code)

    def find_match(self, name, mimetype):
        # first search by name, then by mimetype
        xpaths = [
            ('.//lg.version[@lg="eng"][normalize-space()=$param]/ancestor::record', name),
            ('.//internet-media-type[normalize-space()=$param]/ancestor::record', mimetype),
        ]

        for xpath in xpaths:
            search = self.mapping.xpath(xpath[0], param=xpath[1])
            if search:
                authority = search[0].find('authority-code').text
                is_compressed = search[0].find('is-compressedFormat')
                compressed = is_compressed is not None and is_compressed.text == "true"
                return self.make_url(authority), compressed

        return self.make_url('OCTET'), False

