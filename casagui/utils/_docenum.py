from enum import Enum

class DocEnum(Enum):
    '''Allows for documenting individual enum values::

           In [6]: class MaskMode(DocEnum):
           ...:     'Different masking modes available in addition to a user supplied mask'
           ...:     PB = 1, 'primary beam mask'
           ...:     AUTOMT = 2, 'multi-threshold auto masking'
           ...:

           In [7]: MaskMode.PB?
           Type:            MaskMode
           String form:     MaskMode.PB
           Docstring:       primary beam mask
           Class docstring: Different masking modes available in addition to a user supplied mask

           In [8]:
    '''
    def __new__(cls, value, doc=None):
        self = object.__new__(cls)  # calling super().__new__(value) here would fail
        self._value_ = value
        if doc is not None:
            self.__doc__ = doc
        return self
