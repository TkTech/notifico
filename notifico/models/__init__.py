# -*- coding: utf8 -*-
from sqlalchemy import func
from sqlalchemy.ext.hybrid import Comparator


class CaseInsensitiveComparator(Comparator):
    def __eq__(self, other):
        return func.lower(self.__clause_element__()) == func.lower(other)


from notifico.models.user import *
from notifico.models.bot import *
from notifico.models.channel import *
from notifico.models.hook import *
from notifico.models.project import *
