from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.hybrid import Comparator


class CaseInsensitiveComparator(Comparator):
    def __eq__(self, other):
        return func.lower(self.__clause_element__()) == func.lower(other)


def get_or_create(session, model, query, defaults):
    m = session.query(model).filter_by(**query).first()

    if m is None:
        m = model(**defaults)
        try:
            session.add(m)
            session.flush()
        except IntegrityError:
            session.rollback()
            return session.query(model).filter_by(**query).first()

    return m
