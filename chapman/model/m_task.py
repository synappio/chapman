from ming import Field
from ming.declarative import Document
from ming import schema as S

from .m_base import doc_session, dumps, pickle_property

class TaskState(Document):
    class __mongometa__:
        name='chapman.task'
        session = doc_session

    _id=Field(S.ObjectId)
    type=Field(str)
    parent_id=Field(S.ObjectId, if_missing=None)
    status=Field(str)
    _result=Field('result', S.Binary)
    data=Field({str:None})
    options=Field(dict(
            immutable=S.Bool(if_missing=False),
            ignore_result=S.Bool(if_missing=False),
            preserve_result=S.Bool(if_missing=False), # keep even if linked
            ))
    on_complete=Field(S.ObjectId, if_missing=None)
    mq=Field([S.ObjectId()])

    result = pickle_property('_result')

    @classmethod
    def set_result(cls, id, result):
        cls.m.update_partial(
            { '_id': id },
            { '$set': {
                    'result': dumps(result),
                    'status': 'complete' } } )
    