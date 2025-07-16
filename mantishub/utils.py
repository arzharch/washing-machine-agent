# mantishub/exceptions.py

class MantisHubAPIError(Exception):
    pass

class MantisHubNotFound(MantisHubAPIError):
    pass

class MantisHubUnauthorized(MantisHubAPIError):
    pass
