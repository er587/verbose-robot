from cifsdk.exceptions import CIFException


class StoreSubmissionFailed(CIFException):
    pass


class InvalidSearch(CIFException):
    pass


class CIFBusy(CIFException):
    pass
