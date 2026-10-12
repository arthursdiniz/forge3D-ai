import os

class InstanceLock:
    """OS lock held for API lifetime; protects the single GPU worker/recovery."""
    def __init__(self,path,message='Forge3D já está rodando neste diretório. Abra http://127.0.0.1:8000.'):
        self.path=path
        self.stream=None
        self.message=message
    def acquire(self):
        self.stream=self.path.open('a+b')
        if self.path.stat().st_size==0:
            self.stream.write(b'0')
            self.stream.flush()
        self.stream.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.stream.close()
            self.stream=None
            raise RuntimeError(self.message)
    def release(self):
        if self.stream:
            self.stream.close()
            self.stream=None
