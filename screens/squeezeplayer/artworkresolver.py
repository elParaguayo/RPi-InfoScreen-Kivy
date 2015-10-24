from urllib import urlencode

class ArtworkResolver(object):
    """Class object to help provide an easy way of obtaining a URL to a
       playlist item.

       The class is capable of working out the appropriate path depending on
       whether the file is remote or local.

       A default image path can also be provided. If none is provided, this
       will fall back to the LMS default image.
    """
    def __init__(self, host="localhost", port=9000, default=None):
        self.host = host
        self.port = port

        # Custom plugins may use a different image format
        # Set up some methods to handle them
        self.methods = {"spotifyimage": self.__spotify_url}

        # Set up the template for local artwork
        self.localart = "http://{host}:{port}/music/{coverid}/cover.jpg"

        # Set the default path for missing artwork
        if default is not None:
            self.default = default
        else:
            self.default = self.localart.format(host=self.host,
                                                port=self.port,
                                                coverid=0)

        # Prefix for remote artwork
        self.prefix = "http://www.mysqueezebox.com/public/imageproxy?{data}"

    def __getRemoteURL(self, track, size):
        # Check whether there's a URL for remote artworl
        art = track.get("artwork_url", False)

        # If there is, build the link.
        if art:
            for k in self.methods:
                if art.startswith(k):
                    return self.methods[k](art)

            h, w = size
            data= {"h": h,
                   "w": w,
                   "u": art}
            return self.prefix.format(data=urlencode(data))

        # If not, return the fallback image
        else:
            return self.default

    def __getLocalURL(self, track):
        # Check if local cover art is available
        coverart = track.get("coverart", False)

        # If so, build the link
        if coverart:

            return self.localart.format(host=self.host,
                                        port=self.port,
                                        coverid=track["coverid"])

        # If not, return the fallback image
        else:
            return self.default

    def __spotify_url(self, art):
        """Spotify images (using Triode's plugin) are provided on the local
           server.
        """
        return "http://{host}:{port}/{art}".format(host=self.host,
                                                   port=self.port,
                                                   art=art)

    def getURL(self, track, size=(50, 50)):
        """Method for generating link to artwork for the selected track.

          'track' is a dict object which must contain the "remote", "coverid"
          and "coverart" tags as returned by the server.

          'size' is an optional parameter which can be used when creting links
          for remotely hosted images.
        """

        # List of required keys
        required = ["remote", "coverid", "coverart"]

        # Check that we've received the right type of data
        if type(track) != dict:
            raise TypeError("track should be a dict")

        # Check if all the keys are present
        if not set(required) < set(track.keys()):
            raise KeyError("track should have 'remote', 'coverid' and"
                           " 'coverart' keys")

        # Check the flags for local and remote art
        track["coverart"] = int(track["coverart"])
        remote = int(track["remote"])

        # If it's a remotely hosted file, let's get the link
        if remote:
            return self.__getRemoteURL(track, size)

        # or it's a local file, so let's get the link
        else:
            return self.__getLocalURL(track)
