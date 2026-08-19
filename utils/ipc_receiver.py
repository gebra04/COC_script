"""Receptor IPC Zero-Copy (Camada 3 do Gêmeo Digital).

Conecta-se ao servidor nativo C++ (Core::IPC::ZeroCopyIPCServer) via
Unix Domain Socket, recebe o File Descriptor da memória compartilhada
(memfd_create) através de SCM_RIGHTS e mapeia o buffer double-buffered
diretamente para structs ctypes / arrays NumPy, sem cópias intermediárias.

Ver `digital_twin.md`, Camada 3, seções 2 a 5, para a especificação
completa do protocolo e do layout binário.
"""

import socket
import struct
import mmap
import ctypes
import numpy as np

from utils.digital_twin_paths import DEFAULT_SOCKET_PATH

MAX_ENTITIES = 1024


class TelemetryEntityData(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("entity_id", ctypes.c_uint32),
        ("type_id", ctypes.c_uint16),
        ("level", ctypes.c_uint8),
        ("state", ctypes.c_uint8),
        ("pos_x", ctypes.c_float),
        ("pos_y", ctypes.c_float),
        ("current_hp", ctypes.c_float),
        ("max_hp", ctypes.c_float),
        ("reserved", ctypes.c_uint64),
    ]


class SharedBufferFrame(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("sequence", ctypes.c_uint64),
        ("timestamp_ns", ctypes.c_uint64),
        ("entity_count", ctypes.c_uint32),
        ("padding", ctypes.c_uint32),
        ("entities", TelemetryEntityData * MAX_ENTITIES),
    ]


class SharedMemoryControlBlock(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("magic", ctypes.c_uint32),
        ("active_write_buffer", ctypes.c_uint32),
        ("buffers", SharedBufferFrame * 2),
    ]


# dtype NumPy equivalente ao TelemetryEntityData empacotado (36 bytes).
TELEMETRY_DTYPE = np.dtype(
    [
        ("entity_id", "u4"),
        ("type_id", "u2"),
        ("level", "u1"),
        ("state", "u1"),
        ("pos_x", "f4"),
        ("pos_y", "f4"),
        ("current_hp", "f4"),
        ("max_hp", "f4"),
        ("reserved", "u8"),
    ]
)

_ENTITIES_HEADER_SIZE = ctypes.sizeof(ctypes.c_uint64) * 2 + ctypes.sizeof(ctypes.c_uint32) * 2


# Formato struct do cabeçalho do SharedMemoryControlBlock, empacotado (sem
# padding, espelhando #pragma pack(push, 1) do lado C++): magic (u32) +
# active_write_buffer (u32).
_CONTROL_HEADER_FORMAT = "=II"
_CONTROL_HEADER_SIZE = struct.calcsize(_CONTROL_HEADER_FORMAT)

# Formato struct do cabeçalho de cada SharedBufferFrame: sequence (u64) +
# timestamp_ns (u64) + entity_count (u32) + padding (u32).
_FRAME_HEADER_FORMAT = "=QQII"


class ZeroCopyIPCReceiver:
    """Cliente Python da ponte IPC Zero-Copy descrita em digital_twin.md (Camada 3)."""

    def __init__(self, socket_path: str = DEFAULT_SOCKET_PATH):
        self.socket_path = socket_path
        self._client: socket.socket | None = None
        self.shm_buf: mmap.mmap | None = None

    def connect_and_map(self) -> None:
        """Conecta ao socket UDS, recebe o FD da SHM via SCM_RIGHTS e mapeia o buffer."""
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(self.socket_path)
        self._client = client

        fd_size = struct.calcsize("i")
        msg, ancdata, flags, addr = client.recvmsg(1024, socket.CMSG_LEN(fd_size))

        shm_fd = -1
        for cmsg_level, cmsg_type, cmsg_data in ancdata:
            if cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SCM_RIGHTS:
                shm_fd = struct.unpack("i", cmsg_data[:fd_size])[0]
                break

        if shm_fd < 0:
            raise RuntimeError("Falha ao receber o File Descriptor da SHM via SCM_RIGHTS")

        shm_size = ctypes.sizeof(SharedMemoryControlBlock)
        # Mapeamento somente leitura (PROT_READ): o cliente Python nunca escreve
        # na região compartilhada. Por isso os campos do cabeçalho são lidos
        # via struct.unpack_from diretamente sobre o mmap a cada chamada, em vez
        # de vincular uma ctypes.Structure com from_buffer() — esse método exige
        # um buffer gravável e levantaria TypeError sobre um mmap PROT_READ.
        self.shm_buf = mmap.mmap(shm_fd, shm_size, mmap.MAP_SHARED, mmap.PROT_READ)

    def read_latest_telemetry(self):
        """Retorna (sequence, entities_ndarray) do frame ativo, ou None se vazio."""
        if self.shm_buf is None:
            return None

        _magic, active_idx = struct.unpack_from(_CONTROL_HEADER_FORMAT, self.shm_buf, 0)

        frame_offset = _CONTROL_HEADER_SIZE + active_idx * ctypes.sizeof(SharedBufferFrame)
        sequence, _timestamp_ns, count, _padding = struct.unpack_from(
            _FRAME_HEADER_FORMAT, self.shm_buf, frame_offset
        )

        if count == 0:
            return None

        entities_offset = frame_offset + _ENTITIES_HEADER_SIZE

        entities_array = np.frombuffer(
            self.shm_buf,
            dtype=TELEMETRY_DTYPE,
            count=count,
            offset=entities_offset,
        )

        return sequence, entities_array

    def close(self) -> None:
        """Libera o mmap e o socket.

        Cuidado: o `ndarray` devolvido por `read_latest_telemetry()` é uma view
        zero-copy sobre `shm_buf` (via `np.frombuffer`). Se essa view ainda
        estiver referenciada em algum lugar (variável local, thread, etc.) no
        momento deste `close()`, `mmap.close()` levanta `BufferError`. Quem
        consome a telemetria em uma thread separada (ex.: `gui.py`) deve
        garantir que a thread de leitura tenha terminado antes de chamar
        `close()`.
        """
        if self.shm_buf is not None:
            self.shm_buf.close()
            self.shm_buf = None
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "ZeroCopyIPCReceiver":
        self.connect_and_map()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
