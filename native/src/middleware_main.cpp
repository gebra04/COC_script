// native/src/middleware_main.cpp
//
// Aplicação middleware do Gêmeo Digital — o "servidor nativo" que roda DENTRO
// do Waydroid e faz a ponte entre o motor gráfico do jogo (Camadas 1/2) e o
// receptor Python no host (Camada 3). É a peça que o plano (digital_twin.md)
// descreve como residindo no guest; junta as três camadas nativas num único
// executável de longa duração:
//
//   Camada 1 (layer1_native_hook.hpp): instrumentação/hooking — resolve os
//     limites do segmento .rodata da libg.so em /proc/self/maps para alimentar
//     o VTableResolver da Camada 2. (Neste esqueleto, a instalação de hooks em
//     si é deixada como TODO: depende dos offsets exatos da build da Supercell.)
//   Camada 2 (layer2_forensic_heap.hpp): varre a heap, identifica entidades
//     por vptr e desreferencia structs para preencher TelemetryEntityData.
//   Camada 3 (layer3_ipc_bridge.hpp): publica os frames via memória
//     compartilhada zero-copy + Unix Domain Socket (SCM_RIGHTS).
//
// Estado atual: o laço de coleta real da Camada 2 (CollectEntities) é um STUB
// — sem os offsets de V-Table da libg.so (que exigem engenharia reversa da
// build específica do jogo) não há como enumerar as entidades reais. O stub
// emite uma entidade sintética para que o pipeline ponta a ponta host↔guest
// (memfd/SCM_RIGHTS/double-buffering) possa ser validado de verdade contra o
// utils/ipc_receiver.py, exatamente como o fake_native_server.py fazia do lado
// Python — só que agora do lado C++ nativo e rodável dentro do Waydroid.
//
// Build: compila em qualquer host Linux (ver CMakeLists.txt, alvo
// coc_dt_middleware). Para rodar dentro do Waydroid é preciso um binário
// ARM64/x86_64 conforme a ABI do container e o bind mount de
// /data/media/0/coc-digital-twin (ver mapeamento_arquivos.md, seção 5).

#include "layer2_forensic_heap.hpp"
#include "layer3_ipc_bridge.hpp"

#include <cerrno>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <string>
#include <thread>
#include <vector>

#if defined(__linux__)
#include <csignal>
#endif

namespace {

    volatile std::sig_atomic_t g_running = 1;

    void HandleSignal(int) { g_running = 0; }

    // Camada 1 (parcial): lê /proc/self/maps e devolve [start, end) do
    // primeiro segmento executável/mapeado de libg.so, usado como aproximação
    // dos limites onde as V-Tables (.rodata) vivem. Retorna false se a lib
    // ainda não foi carregada no processo (ex.: rodando fora do jogo).
    bool ResolveLibgRodataBounds(uintptr_t& start, uintptr_t& end) {
        std::FILE* maps = std::fopen("/proc/self/maps", "re");
        if (!maps) return false;

        char line[512];
        bool found = false;
        while (std::fgets(line, sizeof(line), maps)) {
            if (std::strstr(line, "libg.so") == nullptr) continue;

            uintptr_t s = 0, e = 0;
            if (std::sscanf(line, "%zx-%zx", &s, &e) == 2) {
                if (!found) {
                    start = s;
                    end = e;
                    found = true;
                } else {
                    // Estende para cobrir todos os segmentos mapeados da lib.
                    if (s < start) start = s;
                    if (e > end) end = e;
                }
            }
        }
        std::fclose(maps);
        return found;
    }

    // STUB da Camada 2: numa build real, isto varreria os pools de objetos do
    // motor, usaria VTableResolver::IdentifyObject sobre cada vptr e leria os
    // campos (id, posição, HP) via os LibcxxVector/LibcxxSharedPtr. Aqui,
    // apenas emite uma entidade sintética para exercitar o transporte IPC.
    size_t CollectEntities(const Core::Memory::VTableResolver& /*resolver*/,
                           Core::IPC::TelemetryEntityData* out, size_t max_out) {
        if (max_out == 0) return 0;

        static float t = 0.0f;
        t += 1.0f;

        out[0].entity_id = 1;
        out[0].type_id = 1;  // defesa
        out[0].level = 10;
        out[0].state = 1;
        out[0].pos_x = 25.0f;
        out[0].pos_y = 25.0f;
        out[0].current_hp = 1000.0f - (t > 900.0f ? 900.0f : t);
        out[0].max_hp = 1000.0f;
        out[0].reserved = 0;

        return 1;
    }

}  // namespace

int main(int argc, char** argv) {
    const char* socket_path =
        (argc > 1) ? argv[1] : Core::IPC::DEFAULT_SOCKET_PATH;

#if defined(__linux__)
    std::signal(SIGINT, HandleSignal);
    std::signal(SIGTERM, HandleSignal);
#endif

    std::printf("[middleware] Gêmeo Digital — servidor nativo (Camadas 1-3)\n");
    std::printf("[middleware] socket: %s\n", socket_path);

    Core::Memory::VTableResolver resolver;
    uintptr_t rodata_start = 0, rodata_end = 0;
    if (ResolveLibgRodataBounds(rodata_start, rodata_end)) {
        resolver.InitializeRodataBounds(rodata_start, rodata_end);
        std::printf("[middleware] libg.so .rodata bounds: 0x%zx-0x%zx\n",
                    rodata_start, rodata_end);
        // TODO(Camada 2): resolver.RegisterClassVTable(base + offset, tipo)
        // para cada V-Table conhecida, uma vez levantados os offsets da
        // libg.so via engenharia reversa da build da Supercell.
    } else {
        std::printf("[middleware] libg.so não encontrada em /proc/self/maps "
                    "(rodando fora do jogo?) — seguindo com coleta STUB.\n");
    }

    Core::IPC::ZeroCopyIPCServer server;
    if (!server.Initialize(socket_path)) {
        std::fprintf(stderr, "[middleware] Falha ao inicializar IPC (%s): %s\n",
                     socket_path, std::strerror(errno));
        return 1;
    }

    std::printf("[middleware] aguardando cliente Python (ZeroCopyIPCReceiver)...\n");
    if (!server.AcceptClientAndSendFd()) {
        std::fprintf(stderr, "[middleware] Falha ao aceitar cliente / enviar FD: %s\n",
                     std::strerror(errno));
        return 1;
    }
    std::printf("[middleware] cliente conectado, FD da SHM enviado. Publicando frames.\n");

    std::vector<Core::IPC::TelemetryEntityData> entities(Core::IPC::MAX_ENTITIES);

    // ~60 FPS. Em produção este ritmo é ditado pelo hook da Camada 1 (a cada
    // frame renderizado do jogo); no stub usamos um sleep fixo.
    const auto frame_interval = std::chrono::microseconds(16667);

    while (g_running) {
        size_t count = CollectEntities(resolver, entities.data(), entities.size());
        server.WriteFrame(entities.data(), count);
        std::this_thread::sleep_for(frame_interval);
    }

    std::printf("\n[middleware] encerrando.\n");
    return 0;
}
