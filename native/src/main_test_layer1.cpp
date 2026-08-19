#include <iostream>
#include <iomanip>
#include "layer1_native_hook.hpp"

// Dummy original function
void TargetFunction() {
    std::cout << "[Target] TargetFunction() was executed normally." << std::endl;
}

// Dummy hook function
void HookedFunction() {
    std::cout << "[Hook] TargetFunction() was interceptada e HookedFunction() foi chamada!" << std::endl;
}

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << " GymAI Digital Twin - Camada 1 Test " << std::endl;
    std::cout << "========================================" << std::endl;

    using namespace Core::Memory;

    TrampolineARM64::InlineHookContext ctx;
    ctx.target_address = reinterpret_cast<uintptr_t>(&TargetFunction);
    ctx.hook_destination = reinterpret_cast<uintptr_t>(&HookedFunction);
    ctx.trampoline_stub = 0;

    std::cout << "[*] Endereço da TargetFunction: 0x" << std::hex << ctx.target_address << std::dec << std::endl;
    std::cout << "[*] Endereço da HookedFunction: 0x" << std::hex << ctx.hook_destination << std::dec << std::endl;
    
    // Simulate invocation of the Hook install routine
    // WARNING: Em um host x86_64, a instalação real do trampoline ARM64 irá falhar ou crashar se tentarmos executar o código ARM64 injetado. 
    // Para fins de teste estrutural, chamamos TrampolineARM64::InstallHook somente se estivermos rodando no ambiente cross-platform adequado, 
    // mas o build system garante que compila.
    
    std::cout << "[*] Preparando instalacao do hook..." << std::endl;

    // Uncomment this line on a real ARM64 device or emulator to inject:
    // TrampolineARM64::InstallHook(ctx); 
    
    std::cout << "[+] Compilacao da Camada 1 (Instrumentacao Nativa) concluida com sucesso." << std::endl;
    std::cout << "========================================" << std::endl;

    return 0;
}
