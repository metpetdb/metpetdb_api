from getenv import env
import drest

class MetpetAPI():
    def __init__(self, user=None, api=None):
        self.username = user
        self.api_key = api
        self.api = drest.api.TastyPieAPI('{0}/api/v1/'.format(env('HOST_NAME')))
        if self.username:
            self.api.auth(user, api)
