#include "layer1_native_hook.hpp"

namespace Core::Memory {

    uintptr_t SyscallEngine::RawMProtect(void* addr, size_t len, int prot) {
#if defined(ENV_LINUX) && defined(__aarch64__)
        register long x8 __asm__("x8") = __NR_mprotect;
        register long x0 __asm__("x0") = reinterpret_cast<long>(addr);
        register long x1 __asm__("x1") = static_cast<long>(len);
        register long x2 __asm__("x2") = static_cast<long>(prot);

        __asm__ __volatile__(
            "svc #0"
            : "+r"(x0)
            : "r"(x8), "r"(x1), "r"(x2)
            : "memory"
        );
        return static_cast<uintptr_t>(x0);

#elif defined(ENV_LINUX) && defined(__x86_64__)
        register long rax __asm__("rax") = __NR_mprotect;
        register long rdi __asm__("rdi") = reinterpret_cast<long>(addr);
        register long rsi __asm__("rsi") = static_cast<long>(len);
        register long rdx __asm__("rdx") = static_cast<long>(prot);

        __asm__ __volatile__(
            "syscall"
            : "+r"(rax)
            : "r"(rdi), "r"(rsi), "r"(rdx)
            : "rcx", "r11", "memory"
        );
        return static_cast<uintptr_t>(rax);

#elif defined(ENV_WINDOWS)
        DWORD oldProt;
        BOOL res = VirtualProtect(addr, len, static_cast<DWORD>(prot), &oldProt);
        return res ? 0 : 1;
#else
        return static_cast<uintptr_t>(-1);
#endif
    }

    bool TrampolineARM64::InstallHook(InlineHookContext& ctx) {
        // Save original prolog
        std::memcpy(ctx.original_bytes, reinterpret_cast<void*>(ctx.target_address), 16);

        uintptr_t page_size = 4096;
        void* page_align = reinterpret_cast<void*>(ctx.target_address & ~(page_size - 1));
        
        // 1. Change memory protection to Read/Write (RW-)
        // POSIX PROT_READ = 1, PROT_WRITE = 2 (1 | 2 = 3). Avoiding RWE (7) for security.
        SyscallEngine::RawMProtect(page_align, page_size * 2, 3);

        uint32_t trampoline_code[4];
        trampoline_code[0] = 0x58000050; // LDR X16, #8
        trampoline_code[1] = 0xd61f0200; // BR X16

        uint64_t* dest_ptr = reinterpret_cast<uint64_t*>(&trampoline_code[2]);
        *dest_ptr = static_cast<uint64_t>(ctx.hook_destination);

        // Inject the trampoline (if not ARM64, this will just write ARM64 payload regardless, logic is simplified for conceptual validation)
        std::memcpy(reinterpret_cast<void*>(ctx.target_address), trampoline_code, 16);

        // 2. Change memory protection back to Read/Execute (R-X)
        // POSIX PROT_READ = 1, PROT_EXEC = 4 (1 | 4 = 5).
        SyscallEngine::RawMProtect(page_align, page_size * 2, 5);

#if defined(__GNUC__) || defined(__clang__)
        // Clear instruction cache
        __builtin___clear_cache(
            reinterpret_cast<char*>(ctx.target_address),
            reinterpret_cast<char*>(ctx.target_address + 16)
        );
#endif
        return true;
    }

    void TrampolineARM64::PatchADRP(uint32_t* instruction_ptr, uintptr_t current_pc, uintptr_t target_page) {
        uint32_t instr = *instruction_ptr;
        int64_t offset = static_cast<int64_t>(target_page) - (current_pc & ~0xFFF);
        int64_t imm = offset >> 12;

        uint32_t immlo = (imm & 0x3) << 29;
        uint32_t immhi = ((imm >> 2) & 0x7FFFF) << 5;

        // Reconstruct instruction with updated immediate values
        *instruction_ptr = (instr & 0x9F00001F) | immlo | immhi;
    }

    void TrampolineARM64::SanitizeLinkRegister() {
        // Implementação simulada para neutralizar X30(LR) em hooks.
#if defined(__aarch64__)
        __asm__ __volatile__(
            "mov x30, xzr\n\t" // Exemplo: limpa/mascara X30 para sub-rotinas
        );
#endif
    }
}
