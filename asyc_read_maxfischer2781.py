import time
import select
import socket


class AsyncSleep:
    """Event and action to sleep ``until`` a point in time"""
    def __init__(self, until):
        self.until = until

    def __await__(self):
        yield self

    def __repr__(self):
        return '%s(until=%.1f)' % (self.__class__.__name__, self.until)


async def sleep(duration):
    """Cooperatively sleep for ``duration`` seconds"""
    await AsyncSleep(time.time() + duration / 2)
    await AsyncSleep(time.time() + duration / 2)


class AsyncRead:
    """Event and action to read ``amount`` bytes from ``file``"""
    def __init__(self, file, amount=1):
        self.file = file
        self.amount = amount
        self._buffer = b''

    def __await__(self):
        while len(self._buffer) < self.amount:
            yield self
            # we only get here if ``read`` will not block (this is a lie...)
            self._buffer += self.file.read(1)
        return self._buffer

    def __repr__(self):
        return '%s(file=%s, amount=%d, progress=%d)' % (
            self.__class__.__name__, self.file, self.amount, len(self._buffer)
        )


async def read(path, amount):
    """read ``amount`` bytes from ``path``"""
    with open(path, 'rb') as file:
        return await AsyncRead(file, amount)


class AsyncRecv:
    """Event and action to read ``amount`` bytes from ``connection``"""
    def __init__(self, connection, amount=1, read_buffer=1024):
        assert connection.gettimeout() == 0.0, 'connection must be non-blocking for async recv'
        self.connection = connection
        self.amount = amount
        self.read_buffer = read_buffer
        self._buffer = b''

    def __await__(self):
        while len(self._buffer) < self.amount:
            try:
                # read if we do not block
                self._buffer += self.connection.recv(self.read_buffer)
                # yield control to not starve other coroutines indefinitely
                yield self
            except BlockingIOError:
                # suspend if we would block
                yield self
        return self._buffer

    def __repr__(self):
        return '%s(file=%s, amount=%d, progress=%d)' % (
            self.__class__.__name__, self.connection, self.amount, len(self._buffer)
        )


async def recv(url, port, amount):
    """receive ``amount`` bytes from ``port`` at ``url``"""
    connection = socket.socket()
    connection.setblocking(False)
    # open without blocking - retry on failure
    try:
        connection.connect((url, port))
    except BlockingIOError:
        pass
    # await I/O
    try:
        return await AsyncRecv(connection, amount)
    finally:
        connection.close()


def run(*coroutines):
    """Cooperatively run all ``coroutines`` until completion"""
    waiting_read = {}  # type: Dict[file, coroutine]
    waiting = [(0, coroutine) for coroutine in coroutines]
    while waiting or waiting_read:
        # 2. wait until the next coroutine may run or read ...
        try:
            until, coroutine = waiting.pop(0)
        except IndexError:
            until, coroutine = float('inf'), None
            readable, _, _ = select.select(list(waiting_read), [], [])
        else:
            readable, _, _ = select.select(list(waiting_read), [], [], max(0.0, until - time.time()))
        # ... and select the appropriate one
        if readable and time.time() < until:
            if until and coroutine:
                waiting.append((until, coroutine))
                waiting.sort()
            coroutine = waiting_read.pop(readable[0])
        # 3. run this coroutine
        try:
            command = coroutine.send(None)
        except StopIteration:
            continue
        # 1. sort coroutines by their desired suspension ...
        if isinstance(command, AsyncSleep):
            waiting.append((command.until, coroutine))
            waiting.sort(key=lambda item: item[0])
        # ... or register reads
        elif isinstance(command, AsyncRead):
            waiting_read[command.file] = coroutine
        elif isinstance(command, AsyncRecv):
            waiting_read[command.connection] = coroutine


# example coroutines with helpful prints
async def sleepy(identifier, count=5):
    for i in range(count):
        print('id', identifier, 'round', i + 1)
        await sleep(0.01)


async def ready(path, amount=1024*4):
    print('read', path, 'at', '%d' % time.time())
    result = await read(path, amount)
    print('done', path, 'at', '%d' % time.time(), 'got', len(result), 'B')


async def recvy(url, port, amount=1024*32):
    print('read', '%s:%d' % (url, port), 'at', '%d' % time.time())
    try:
        result = await recv(url, port, amount)
    except ConnectionRefusedError:
        result = ''
    print('done', '%s:%d' % (url, port), 'at', '%d' % time.time(), 'got', len(result) or '----', 'B')


# must prepare server for recvy via
# $ cat /dev/urandom | nc -l 25000
run(sleepy('background', 5), recvy('localhost', 25000), ready('/dev/urandom'))