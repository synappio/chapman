from chapman.meta import RegistryMetaclass
from chapman.model import TaskState, Message
from chapman import exc

class Task(object):
    __metaclass__ = RegistryMetaclass
    _registry = {}

    def __init__(self, state):
        self._state = state

    @property
    def id(self):
        return self._state._id

    @classmethod
    def s(cls, **options):
        state = TaskState.make(dict(
                type=cls.name, status='active',
                options=options))
        state.m.insert()
        return cls(state)

    @classmethod
    def from_state(cls, state):
        Class = cls.by_name(state.type)
        return Class(state)

    def refresh(self):
        self._state = TaskState.m.get(_id=self.id)

    def run(self, msg):
        '''Do the work of the task'''
        raise NotImplementedError, 'run'

    def error(self, msg):
        self.complete(msg.args[0])

    def start(self, *args, **kwargs):
        '''Send a 'run' message & update state'''
        msg = Message.s(self, 'run', *args, **kwargs)
        msg.send()
        return msg

    def link(self, task, slot, *args, **kwargs):
        '''Add an on_complete message with the given args'''
        msg = Message.s(task, slot, *args, **kwargs)
        self._state.m.set(dict(on_complete=msg._id))
        return msg

    def complete(self, result):
        if self._state.on_complete:
            msg = Message.m.get(_id=self._state.on_complete)
            if result.status == 'success':
                msg.send(result.get())
            else:
                msg.m.set(dict(slot='error'))
                msg.send(result)
            self._state.m.delete()
        elif ( self._state.options.ignore_result
               and result.status == 'success'):
            self._state.m.delete()
        else:
            TaskState.set_result(self.id, result)
            self.refresh()

    def get(self):
        return self._state.result.get()

    def handle(self, msg):
        method = getattr(self, msg.slot)
        method(msg)
        msg.retire()

class Result(object):

    def __init__(self, task_id, status, data):
        self.task_id = task_id
        self.status = status
        self.data = data

    def __repr__(self):
        return '<Result %s for %s>' % (
            self.status, self.task_id)

    @classmethod
    def success(cls, task_id, value):
        return cls(task_id, 'success', value)

    @classmethod
    def failure(cls, task_id, message, ex_type, ex_value, tb):
        return cls(
            task_id, 'failure',
            exc.TaskError.from_exc_info(
                message, ex_type, ex_value, tb))

    def get(self):
        if self.status == 'success':
            return self.data
        elif self.status == 'failure':
            raise self.data
        else:
            assert False

