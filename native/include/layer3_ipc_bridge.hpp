#ifndef LAYER3_IPC_BRIDGE_HPP
#define LAYER3_IPC_BRIDGE_HPP

// Camada 3 do digital_twin.md: IPC de Ultra Baixa Latência & Memória
// Compartilhada Zero-Copy. Portado da especificação (seção "CAMADA 3",
// subseção 5.1) para native/include/.
//
// O layout binário abaixo (TelemetryEntityData / SharedBufferFrame /
// SharedMemoryControlBlock) é espelhado byte a byte em
// utils/ipc_receiver.py (structs ctypes com _pack_ = 1 e o mesmo dtype
// NumPy) — qualquer mudança de campo aqui precisa ser refletida lá também,
// ou o handshake quebra silenciosamente (campos lidos com o offset errado).
//
// Caminho do socket: quando esta aplicação middleware roda dentro do
// Waydroid, o socket deve ser criado em DEFAULT_SOCKET_PATH abaixo, que é o
// lado "guest" do bind mount do LXC configurado para expor
// ~/.local/share/coc-digital-twin (host) como /data/media/0/coc-digital-twin
// (guest) — a raiz do container é somente leitura (montada a partir de
// system.img), então o bind mount precisa de um alvo dentro de uma partição
// gravável (/data). Ver utils/digital_twin_paths.py (lado Python/host) e
// mapeamento_arquivos.md, seção 5, para o mount entry completo do
// lxc.mount.entry.

#include <atomic>
#include <cstdint>
#include <cstring>
#include <fcntl.h>
#include <sys/eventfd.h>
#include <sys/mman.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <sys/un.h>
#include <unistd.h>

namespace Core::IPC {

    constexpr uint32_t SHM_MAGIC = 0x434F4354;
    constexpr size_t MAX_ENTITIES = 1024;

    // Lado "guest" (dentro do Waydroid) do diretório compartilhado com o
    // host via bind mount do LXC. Ver nota no topo do arquivo.
    constexpr const char* DEFAULT_SOCKET_PATH = "/data/media/0/coc-digital-twin/coc_dt.sock";

#pragma pack(push, 1)
    struct TelemetryEntityData {
        uint32_t entity_id;
        uint16_t type_id;
        uint8_t level;
        uint8_t state;
        float pos_x;
        float pos_y;
        float current_hp;
        float max_hp;
        uint64_t reserved;
    };

    struct SharedBufferFrame {
        uint64_t sequence;
        uint64_t timestamp_ns;
        uint32_t entity_count;
        uint32_t padding;
        TelemetryEntityData entities[MAX_ENTITIES];
    };

    struct SharedMemoryControlBlock {
        uint32_t magic;
        std::atomic<uint32_t> active_write_buffer{0};
        SharedBufferFrame buffers[2];
    };
#pragma pack(pop)

    class ZeroCopyIPCServer {
    private:
        int m_memfd{-1};
        int m_eventfd{-1};
        int m_socket_fd{-1};
        int m_client_fd{-1};
        SharedMemoryControlBlock* m_shm_region{nullptr};
        size_t m_shm_size{sizeof(SharedMemoryControlBlock)};
        uint64_t m_frame_counter{0};

    public:
        bool Initialize(const char* socket_path = DEFAULT_SOCKET_PATH) {
#if defined(__NR_memfd_create)
            m_memfd = static_cast<int>(syscall(__NR_memfd_create, "coc_dt_shm", 0 /* MFD_CLOEXEC opcional */));
#else
            m_memfd = static_cast<int>(syscall(SYS_memfd_create, "coc_dt_shm", 0));
#endif
            if (m_memfd < 0) return false;
            if (ftruncate(m_memfd, static_cast<off_t>(m_shm_size)) < 0) return false;

            void* addr = mmap(nullptr, m_shm_size, PROT_READ | PROT_WRITE, MAP_SHARED, m_memfd, 0);
            if (addr == MAP_FAILED) return false;

            m_shm_region = new (addr) SharedMemoryControlBlock();
            m_shm_region->magic = SHM_MAGIC;

            m_eventfd = eventfd(0, EFD_NONBLOCK | EFD_CLOEXEC);

            m_socket_fd = socket(AF_UNIX, SOCK_STREAM, 0);
            if (m_socket_fd < 0) return false;

            sockaddr_un sun{};
            sun.sun_family = AF_UNIX;
            std::strncpy(sun.sun_path, socket_path, sizeof(sun.sun_path) - 1);
            unlink(socket_path);

            if (bind(m_socket_fd, reinterpret_cast<sockaddr*>(&sun), sizeof(sun)) < 0) return false;
            if (listen(m_socket_fd, 1) < 0) return false;

            return true;
        }

        // Bloqueia até um cliente (o receptor Python, ZeroCopyIPCReceiver)
        // conectar, e então transfere o FD da memória compartilhada via
        // SCM_RIGHTS. Deve ser chamado uma vez por cliente antes de WriteFrame.
        bool AcceptClientAndSendFd() {
            sockaddr_un client_addr{};
            socklen_t addr_len = sizeof(client_addr);
            m_client_fd = accept(m_socket_fd, reinterpret_cast<sockaddr*>(&client_addr), &addr_len);
            if (m_client_fd < 0) return false;

            char dummy = 'x';
            iovec io{.iov_base = &dummy, .iov_len = 1};

            union {
                char buf[CMSG_SPACE(sizeof(int))];
                struct cmsghdr align;
            } cmsg_buf{};

            msghdr msg{};
            msg.msg_iov = &io;
            msg.msg_iovlen = 1;
            msg.msg_control = cmsg_buf.buf;
            msg.msg_controllen = sizeof(cmsg_buf.buf);

            cmsghdr* cmsg = CMSG_FIRSTHDR(&msg);
            cmsg->cmsg_level = SOL_SOCKET;
            cmsg->cmsg_type = SCM_RIGHTS;
            cmsg->cmsg_len = CMSG_LEN(sizeof(int));
            std::memcpy(CMSG_DATA(cmsg), &m_memfd, sizeof(int));

            return sendmsg(m_client_fd, &msg, 0) >= 0;
        }

        void WriteFrame(const TelemetryEntityData* entities, size_t count) {
            if (!m_shm_region) return;

            uint32_t write_idx = 1 - m_shm_region->active_write_buffer.load(std::memory_order_relaxed);
            SharedBufferFrame& frame = m_shm_region->buffers[write_idx];

            frame.sequence = ++m_frame_counter;
            frame.entity_count = (count > MAX_ENTITIES) ? MAX_ENTITIES : static_cast<uint32_t>(count);

            std::memcpy(frame.entities, entities, frame.entity_count * sizeof(TelemetryEntityData));

            m_shm_region->active_write_buffer.store(write_idx, std::memory_order_release);

            if (m_eventfd >= 0) {
                uint64_t signal = 1;
                [[maybe_unused]] ssize_t written = write(m_eventfd, &signal, sizeof(signal));
            }
        }

        ~ZeroCopyIPCServer() {
            if (m_shm_region) munmap(m_shm_region, m_shm_size);
            if (m_memfd >= 0) close(m_memfd);
            if (m_eventfd >= 0) close(m_eventfd);
            if (m_client_fd >= 0) close(m_client_fd);
            if (m_socket_fd >= 0) close(m_socket_fd);
        }
    };

}  // namespace Core::IPC

#endif  // LAYER3_IPC_BRIDGE_HPP
