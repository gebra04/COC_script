#ifndef LAYER2_FORENSIC_HEAP_HPP
#define LAYER2_FORENSIC_HEAP_HPP

// Camada 2 do digital_twin.md: Forensic Heap Walk & Reconstrução de V-Tables.
// Portado da especificação (seção "CAMADA 2", subseção 5) para native/include/
// como parte da aplicação middleware que roda dentro do processo alvo
// (com.supercell.clashofclans) uma vez injetada pela Camada 1.
//
// Nota de escopo: a validação de checksum do Scudo Hardened Allocator
// (ScudoAuditor) só é significativa dentro de um processo Android/Bionic real
// — o cabeçalho de 8 bytes que ela lê só existe porque o alocador do sistema é
// o Scudo. Em builds de host (Linux glibc, usados para compilar e testar este
// middleware fora do Waydroid), chunks alocados com malloc() comum não têm
// esse cabeçalho, então ScudoAuditor::ValidateChunk() não deve ser chamado
// sobre eles — ver native/src/main_test_middleware.cpp, que testa apenas
// VTableResolver contra objetos sintéticos, sem tentar validar seus chunks.

#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <optional>
#include <unordered_map>

namespace Core::Memory {

    template <typename T>
    struct LibcxxVector {
        T* my_first;
        T* my_last;
        T* my_end;

        [[nodiscard]] size_t size() const {
            if (!my_first || !my_last || my_last < my_first) return 0;
            return static_cast<size_t>(my_last - my_first);
        }

        [[nodiscard]] size_t capacity() const {
            if (!my_first || !my_end || my_end < my_first) return 0;
            return static_cast<size_t>(my_end - my_first);
        }

        [[nodiscard]] bool is_valid() const {
            return my_first != nullptr && my_last >= my_first && my_end >= my_last;
        }

        std::optional<T> at(size_t index) const {
            if (index >= size()) return std::nullopt;
            return my_first[index];
        }
    };

    struct SharedPtrControlBlock {
        uintptr_t vtable;
        int32_t shared_owners;  // _Uses
        int32_t weak_owners;    // _Weaks
    };

    template <typename T>
    struct LibcxxSharedPtr {
        T* ptr;
        SharedPtrControlBlock* control_block;

        [[nodiscard]] bool is_alive() const {
            if (!ptr || !control_block) return false;
            return control_block->shared_owners > 0;
        }

        T* get() const { return is_alive() ? ptr : nullptr; }
    };

    // Classes de entidade conhecidas, mapeadas a partir das V-Tables da
    // libg.so. type_id (Camada 3/telemetria) usa uma família de valores
    // separada (defesa=1/tropa=2/recurso=3, ver TelemetryEntityData); este
    // enum é interno à Camada 2, usado para diferenciar edifícios específicos
    // antes de serem reduzidos ao type_id genérico publicado via IPC.
    enum class EntityType {
        Unknown = 0,
        TownHall,
        Cannon,
        ArcherTower,
        Barbarian,
        Wall
    };

    // Resolve o tipo estático de um objeto em O(1) a partir do seu vptr
    // (offset 0x0), sem depender de RTTI (desabilitado em builds -O3 de
    // produção do motor gráfico).
    class VTableResolver {
    private:
        std::unordered_map<uintptr_t, EntityType> m_vtable_map;
        uintptr_t m_rodata_start{0};
        uintptr_t m_rodata_end{0};

    public:
        void InitializeRodataBounds(uintptr_t start, uintptr_t end) {
            m_rodata_start = start;
            m_rodata_end = end;
        }

        void RegisterClassVTable(uintptr_t vtable_address, EntityType type) {
            m_vtable_map[vtable_address] = type;
        }

        [[nodiscard]] bool HasRodataBounds() const {
            return m_rodata_start != 0 && m_rodata_end != 0;
        }

        [[nodiscard]] EntityType IdentifyObject(const void* object_ptr) const {
            if (!object_ptr) return EntityType::Unknown;

            uintptr_t vptr = *reinterpret_cast<const uintptr_t*>(object_ptr);

            if (vptr < m_rodata_start || vptr >= m_rodata_end) {
                return EntityType::Unknown;
            }

            auto it = m_vtable_map.find(vptr);
            if (it != m_vtable_map.end()) {
                return it->second;
            }

            return EntityType::Unknown;
        }
    };

    // Auditoria do cabeçalho de chunk do Scudo Hardened Allocator (Android
    // 11+). Só é válida sobre ponteiros alocados pelo Scudo dentro de um
    // processo Android real — ver nota de escopo no topo do arquivo.
    class ScudoAuditor {
    private:
        uint32_t m_scudo_cookie{0};

    public:
        explicit ScudoAuditor(uint32_t cookie) : m_scudo_cookie(cookie) {}

#pragma pack(push, 1)
        struct ChunkHeader {
            uint32_t state : 2;
            uint32_t class_id : 6;
            uint32_t offset : 16;
            uint32_t size : 8;
            uint16_t checksum;
        };
#pragma pack(pop)

        [[nodiscard]] bool ValidateChunk(const void* chunk_ptr) const {
            if (!chunk_ptr) return false;
            const auto* header = reinterpret_cast<const ChunkHeader*>(
                reinterpret_cast<uintptr_t>(chunk_ptr) - sizeof(ChunkHeader));
            return header->state == 1;
        }
    };

}  // namespace Core::Memory

#endif  // LAYER2_FORENSIC_HEAP_HPP
