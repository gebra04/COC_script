#ifndef LAYER1_NATIVE_HOOK_HPP
#define LAYER1_NATIVE_HOOK_HPP

#include <cstdint>
#include <cstddef>
#include <cstring>

#if defined(_WIN32) || defined(_WIN64)
    #define ENV_WINDOWS
    #include <windows.h>
#elif defined(__linux__) || defined(__ANDROID__)
    #define ENV_LINUX
    #include <sys/syscall.h>
    #include <unistd.h>
    #include <sys/mman.h>
#endif

namespace Core::Memory {

    /**
     * @class SyscallEngine
     * @brief Motor de Chamadas de Sistema Diretas para contornar libc e garantir isolamento.
     */
    class SyscallEngine {
    public:
        /**
         * @brief Executa syscall raw para alterar proteção de memória (mprotect/VirtualProtect).
         * @param addr Endereço de memória
         * @param len Tamanho do bloco
         * @param prot Flags de proteção (ex: PROT_READ | PROT_WRITE)
         * @return 0 em caso de sucesso, não-zero em caso de falha.
         */
        static uintptr_t RawMProtect(void* addr, size_t len, int prot);
    };

    /**
     * @class TrampolineARM64
     * @brief Utilitário para instalação de hooks inline e relocalização (ADRP) em ARM64.
     */
    class TrampolineARM64 {
    public:
        struct InlineHookContext {
            uintptr_t target_address;
            uintptr_t hook_destination;
            uintptr_t trampoline_stub;
            uint8_t original_bytes[16];
        };

        /**
         * @brief Instala um inline hook em uma função.
         * @param ctx Contexto do hook a ser populado/utilizado.
         * @return true se o hook foi instalado com sucesso.
         */
        static bool InstallHook(InlineHookContext& ctx);

        /**
         * @brief Corrige instruções dependentes do PC (Program Counter) como ADRP após a realocação.
         * @param instruction_ptr Ponteiro para a instrução a ser corrigida.
         * @param current_pc Valor atualizado do Program Counter no trampoline.
         * @param target_page Endereço absoluto da página de destino.
         */
        static void PatchADRP(uint32_t* instruction_ptr, uintptr_t current_pc, uintptr_t target_page);
        
        /**
         * @brief Restaura/Sanitiza o registrador de retorno (LR/X30) para evitar detecção no stack trace.
         */
        static void SanitizeLinkRegister();
    };

}

#endif // LAYER1_NATIVE_HOOK_HPP
